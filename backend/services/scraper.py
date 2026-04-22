"""
Recipe scraper service.

Uses recipe-scrapers 9.x for natively supported sites, then falls back to
manual JSON-LD / schema.org parsing for everything else.
"""
import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_me, WebsiteNotImplementedError

TARGET_BLOGS = [
    "okonomikitchen.com",
    "tiffycooks.com",
    "halfbakedharvest.com",
    "omnivorescookbook.com",
    "madewithlau.com",
    "thewoksoflife.com",
    "maangchi.com",
    "loveandlemons.com",
]

# Sites confirmed to block server-side requests (403/500)
BLOCKED_SITES = {
    "tiffycooks.com",
    "maangchi.com",
    "omnivorescookbook.com",
    "madewithlau.com",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
}


def _domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def _fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def scrape_recipe(url: str) -> dict:
    """
    Scrape a recipe from a URL. Returns a dict with:
    title, url, source_site, image_url, servings, total_time_minutes,
    ingredients_raw (list[str]), description.
    Raises ValueError if no recipe data could be extracted.
    """
    domain = _domain(url)

    if domain in BLOCKED_SITES:
        raise ValueError(
            f"{domain} blocks automated access. "
            f"Sites that work for URL import: thewoksoflife.com, halfbakedharvest.com, "
            f"okonomikitchen.com, loveandlemons.com. "
            f"For {domain}, try browsing their site and copying the recipe ingredients manually."
        )

    # Try recipe-scrapers native support first
    try:
        scraper = scrape_me(url)
        result = _build_from_scraper(scraper, url, domain)
        if result["ingredients_raw"]:
            return result
    except WebsiteNotImplementedError:
        pass  # Site not in registry — fall through to JSON-LD
    except Exception:
        pass  # Network or parse error — fall through

    # Fallback: fetch HTML and parse JSON-LD schema.org/Recipe manually
    try:
        html = _fetch_html(url)
    except Exception as e:
        raise ValueError(f"Could not fetch {url}: {e}")

    return _jsonld_fallback(html, url, domain)


def _build_from_scraper(scraper, url: str, domain: str) -> dict:
    try:
        ingredients = scraper.ingredients()
    except Exception:
        ingredients = []

    try:
        title = scraper.title()
    except Exception:
        title = ""

    try:
        image = scraper.image()
    except Exception:
        image = None

    try:
        servings_str = str(scraper.yields() or "")
        m = re.search(r"\d+", servings_str)
        servings = int(m.group()) if m else None
    except Exception:
        servings = None

    try:
        total_time = scraper.total_time()
        total_time = int(total_time) if total_time else None
    except Exception:
        total_time = None

    try:
        description = scraper.description()
    except Exception:
        description = None

    return {
        "title": title,
        "url": url,
        "source_site": domain,
        "image_url": image,
        "servings": servings,
        "total_time_minutes": total_time,
        "ingredients_raw": ingredients,
        "description": description,
    }


def _jsonld_fallback(html: str, url: str, domain: str) -> dict:
    """Parse schema.org/Recipe from JSON-LD <script> tags."""
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Handle @graph arrays and plain lists
        if isinstance(data, dict) and "@graph" in data:
            items = data["@graph"]
        elif isinstance(data, list):
            items = data
        else:
            items = [data]

        for item in items:
            if not isinstance(item, dict):
                continue
            schema_type = item.get("@type", "")
            if isinstance(schema_type, list):
                schema_type = " ".join(schema_type)
            if "Recipe" not in schema_type:
                continue

            raw_ingredients = item.get("recipeIngredient", [])
            if not raw_ingredients:
                continue

            # Parse servings
            servings = None
            yield_data = item.get("recipeYield")
            if yield_data:
                m = re.search(r"\d+", str(yield_data))
                servings = int(m.group()) if m else None

            # Parse total time (ISO 8601 duration)
            total_time = None
            for time_field in ("totalTime", "cookTime", "prepTime"):
                val = item.get(time_field, "")
                if val:
                    m = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?", val)
                    if m:
                        hours = int(m.group(1) or 0)
                        minutes = int(m.group(2) or 0)
                        total_time = hours * 60 + minutes
                        break

            # Parse image
            image = item.get("image")
            if isinstance(image, list):
                image = image[0]
            if isinstance(image, dict):
                image = image.get("url")

            return {
                "title": item.get("name", ""),
                "url": url,
                "source_site": domain,
                "image_url": image,
                "servings": servings,
                "total_time_minutes": total_time,
                "ingredients_raw": list(raw_ingredients),
                "description": item.get("description"),
            }

    raise ValueError(f"No recipe data found at {url}. The site may not use schema.org/Recipe markup.")
