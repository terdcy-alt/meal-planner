"""
All Claude API interactions.
"""
import json
import os
from typing import Optional

import anthropic

from services.scraper import TARGET_BLOGS

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def normalize_ingredients(raw_ingredients: list[str]) -> list[dict]:
    """
    Parse raw ingredient strings into structured dicts.
    Returns list of: {quantity, unit, name, canonical_name, notes, category, is_pantry_staple}
    """
    prompt = f"""Parse these raw recipe ingredient strings into structured JSON.

Raw ingredients:
{json.dumps(raw_ingredients, indent=2)}

Return a JSON array where each item has:
- "quantity": number or null (e.g. 2, 0.5, null)
- "unit": string or null (e.g. "tbsp", "cup", "g", null for items like "1 egg")
- "name": the ingredient name as written
- "canonical_name": normalized/canonical form (lowercase, singular)
  - normalize synonyms: "scallions" → "green onion", "cilantro" → "cilantro", "spring onion" → "green onion"
  - remove descriptors: "fresh ginger" → "ginger", "large eggs" → "egg"
- "notes": preparation notes if any (e.g. "thinly sliced", "room temperature") or null
- "category": one of: "produce", "protein", "dairy", "grain", "pantry", "condiment", "spice", "oil", "other"
- "is_pantry_staple": true for condiments/spices/oils that last a long time (soy sauce, sesame oil, fish sauce, rice vinegar, garlic, ginger, etc.)

Return ONLY valid JSON array, no explanation."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # Strip markdown code fences if present
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def suggest_recipe_combos(recipes: list[dict]) -> list[dict]:
    """
    Given a list of recipes (with their normalized ingredients), suggest the best
    2-3 recipe combinations that minimize food waste (maximize shared ingredients).

    recipes: list of {id, title, url, ingredients: [{canonical_name, is_pantry_staple}]}
    Returns: list of {recipe_ids, shared_ingredients, explanation}
    """
    prompt = f"""You are helping minimize food waste in weekly meal planning.

Here are the available recipes and their ingredients:
{json.dumps(recipes, indent=2)}

Identify the best 2-3 recipe combinations that share the most perishable ingredients
(fresh produce, proteins, dairy — NOT pantry staples like soy sauce, oil, spices).

Return a JSON array of up to 3 combo suggestions, each with:
- "recipe_ids": list of recipe IDs in this combo
- "recipe_titles": list of recipe titles
- "shared_ingredients": list of canonical ingredient names shared between the recipes (perishables only)
- "shared_count": number of shared perishable ingredients
- "explanation": one sentence explaining why this combo is good

Sort by shared_count descending. Return ONLY valid JSON array."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def generate_grocery_list(
    recipe_ingredients: list[dict],
    pantry_items: list[dict],
) -> list[dict]:
    """
    Consolidate recipe ingredients, subtract pantry items, group by category.

    recipe_ingredients: [{canonical_name, quantity, unit, category, is_pantry_staple, recipe_title}]
    pantry_items: [{canonical_name, quantity, unit}]
    Returns: [{category, items: [{name, quantity, unit, recipes}]}]
    """
    prompt = f"""Generate a consolidated grocery list.

Recipe ingredients needed:
{json.dumps(recipe_ingredients, indent=2)}

Items already in pantry (DO NOT include these in the grocery list):
{json.dumps(pantry_items, indent=2)}

Instructions:
1. Combine duplicate ingredients across recipes (sum quantities where units match)
2. Remove any ingredient that is already in the pantry (use fuzzy matching — "low-sodium soy sauce" matches "soy sauce")
3. If pantry has partial quantity, only add the remaining needed amount
4. Group results by category: "Produce", "Protein", "Dairy", "Grains & Bread", "Pantry & Condiments", "Other"
5. Within each category, list items alphabetically

Return a JSON array of category groups:
[
  {{
    "category": "Produce",
    "items": [
      {{
        "name": "green onion",
        "quantity": 1,
        "unit": "bunch",
        "recipes": ["Recipe A", "Recipe B"]
      }}
    ]
  }}
]

Only include categories that have items. Return ONLY valid JSON array."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def search_recipes_by_mood(mood: str, existing_recipe_ids: list[int] = None) -> list[dict]:
    """
    Two-step search:
    1. Claude suggests search queries per blog (2 queries per blog = more coverage).
    2. Scrape each blog's search page and pull top 3 results per query.
    Returns up to ~10 deduplicated results.
    """
    import requests
    from bs4 import BeautifulSoup

    SCRAPABLE_BLOGS = [
        "thewoksoflife.com",
        "halfbakedharvest.com",
        "okonomikitchen.com",
        "loveandlemons.com",
        "tiffycooks.com",
    ]

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    # Step 1: Claude generates 2 search queries per blog (broader coverage)
    blogs_list = "\n".join(f"- {b}" for b in SCRAPABLE_BLOGS)
    prompt = f"""The user wants recipes matching this mood/craving: "{mood}"

For each of these food blogs, suggest 2 different search queries that would find relevant recipes:
{blogs_list}

Return a JSON array — one entry per (blog, query) pair, so 10 entries total:
[
  {{
    "blog": "thewoksoflife.com",
    "search_query": "mapo tofu",
    "description": "Silken tofu in a spicy Sichuan sauce"
  }},
  {{
    "blog": "thewoksoflife.com",
    "search_query": "braised pork",
    "description": "Tender pork belly in a rich soy-braised sauce"
  }}
]

- "search_query": 2-3 words maximum, no special characters
- Vary the 2 queries per blog (different dishes, not the same recipe twice)
- Only use blogs from the list above
- Return ONLY valid JSON array, no explanation."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    suggestions = json.loads(text)

    # Step 2: Scrape each blog's search page, pull top 3 links per query
    seen_urls = set()
    results = []

    for s in suggestions:
        blog = s.get("blog", "").replace("www.", "")
        if blog not in SCRAPABLE_BLOGS:
            continue

        query = s.get("search_query", "")
        if not query:
            continue

        base = "https://thewoksoflife.com" if blog == "thewoksoflife.com" else f"https://www.{blog}"
        search_url = f"{base}/?s={requests.utils.quote(query)}"

        try:
            resp = requests.get(search_url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")

            # Pull up to 3 recipe links from headings on the search results page
            found = 0
            for a in soup.select("h2 a, h3 a, h4 a"):
                href = a.get("href", "")
                title = a.get_text(strip=True)
                if (
                    blog.replace("www.", "") in href
                    and href.startswith("http")
                    and href not in seen_urls
                    and title
                ):
                    seen_urls.add(href)
                    results.append({
                        "title": title,
                        "url": href,
                        "source_site": blog,
                        "description": s["description"],
                        "confidence": "high",
                    })
                    found += 1
                    if found >= 3:
                        break
        except Exception:
            continue

    return results


def fuzzy_match_pantry(ingredient_name: str, pantry_names: list[str]) -> Optional[str]:
    """Check if an ingredient is covered by any pantry item (handles synonyms/variants)."""
    if not pantry_names:
        return None

    prompt = f"""Does "{ingredient_name}" match any of these pantry items (accounting for synonyms, brand variants, and near-equivalents)?

Pantry items: {json.dumps(pantry_names)}

Reply with just the matching pantry item name, or "none" if no match."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}],
    )

    result = message.content[0].text.strip().strip('"')
    return None if result.lower() == "none" else result
