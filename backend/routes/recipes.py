import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from database import get_db
from models import Recipe, Ingredient, RecipeIngredient
from services.scraper import scrape_recipe
from services.claude import normalize_ingredients, search_recipes_by_mood

router = APIRouter(prefix="/api/recipe", tags=["recipes"])


class ScrapeRequest(BaseModel):
    url: str


class RecipeOut(BaseModel):
    id: int
    url: str
    title: str
    source_site: Optional[str]
    image_url: Optional[str]
    servings: Optional[int]
    total_time_minutes: Optional[int]
    description: Optional[str]
    is_ai_suggested: bool
    ingredients: list[dict]

    class Config:
        from_attributes = True


def _get_or_create_ingredient(db: Session, canonical_name: str, category: str, is_pantry_staple: bool) -> Ingredient:
    ing = db.query(Ingredient).filter(Ingredient.canonical_name == canonical_name).first()
    if not ing:
        ing = Ingredient(
            name=canonical_name,
            canonical_name=canonical_name,
            category=category,
            is_pantry_staple=is_pantry_staple,
        )
        db.add(ing)
        db.flush()
    return ing


def _recipe_to_out(recipe: Recipe) -> dict:
    ingredients = [
        {
            "id": ri.ingredient_id,
            "name": ri.ingredient.canonical_name,
            "quantity": ri.quantity,
            "unit": ri.unit,
            "notes": ri.notes,
            "category": ri.ingredient.category,
            "is_pantry_staple": ri.ingredient.is_pantry_staple,
            "raw_text": ri.raw_text,
        }
        for ri in recipe.recipe_ingredients
    ]
    return {
        "id": recipe.id,
        "url": recipe.url,
        "title": recipe.title,
        "source_site": recipe.source_site,
        "image_url": recipe.image_url,
        "servings": recipe.servings,
        "total_time_minutes": recipe.total_time_minutes,
        "description": recipe.description,
        "is_ai_suggested": recipe.is_ai_suggested,
        "ingredients": ingredients,
    }


@router.post("/scrape")
async def scrape_recipe_url(body: ScrapeRequest, db: Session = Depends(get_db)):
    """Scrape a recipe URL and store it."""
    # Check if already scraped
    existing = db.query(Recipe).filter(Recipe.url == body.url).first()
    if existing:
        return _recipe_to_out(existing)

    # Scrape
    try:
        data = scrape_recipe(body.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not data["ingredients_raw"]:
        raise HTTPException(status_code=422, detail="No ingredients found at that URL")

    # Normalize via Claude
    try:
        normalized = normalize_ingredients(data["ingredients_raw"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingredient normalization failed: {e}")

    # Store recipe
    recipe = Recipe(
        url=data["url"],
        title=data["title"] or "Untitled Recipe",
        source_site=data["source_site"],
        image_url=data["image_url"],
        servings=data["servings"],
        total_time_minutes=data["total_time_minutes"],
        ingredients_raw=json.dumps(data["ingredients_raw"]),
        description=data["description"],
        is_ai_suggested=False,
    )
    db.add(recipe)
    db.flush()

    # Store normalized ingredients
    for item in normalized:
        canonical = (item.get("canonical_name") or item.get("name", "")).strip().lower()
        if not canonical:
            continue
        ing = _get_or_create_ingredient(
            db, canonical,
            item.get("category", "other"),
            item.get("is_pantry_staple", False),
        )
        # Avoid duplicate recipe<->ingredient links
        existing_ri = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe.id,
            RecipeIngredient.ingredient_id == ing.id,
        ).first()
        if not existing_ri:
            ri = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ing.id,
                quantity=item.get("quantity"),
                unit=item.get("unit"),
                notes=item.get("notes"),
                raw_text=item.get("name"),
            )
            db.add(ri)

    db.commit()
    db.refresh(recipe)
    return _recipe_to_out(recipe)


@router.get("/search")
async def search_recipes(
    mood: str = Query(..., description="Mood or craving, e.g. 'cozy Korean weeknight'"),
    db: Session = Depends(get_db),
):
    """Search for recipes based on mood/craving using Claude."""
    try:
        suggestions = search_recipes_by_mood(mood)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    for s in suggestions:
        url = s.get("url", "")
        # Try to scrape high-confidence suggestions to verify
        if s.get("confidence") == "high" and url:
            try:
                existing = db.query(Recipe).filter(Recipe.url == url).first()
                if existing:
                    r = _recipe_to_out(existing)
                    r["confidence"] = "high"
                    results.append(r)
                    continue
                data = scrape_recipe(url)
                if data["ingredients_raw"]:
                    # Store it
                    recipe = Recipe(
                        url=url,
                        title=data["title"] or s.get("title", ""),
                        source_site=data["source_site"] or s.get("source_site"),
                        image_url=data["image_url"],
                        servings=data["servings"],
                        total_time_minutes=data["total_time_minutes"],
                        ingredients_raw=json.dumps(data["ingredients_raw"]),
                        description=data["description"] or s.get("description"),
                        is_ai_suggested=True,
                    )
                    db.add(recipe)
                    db.flush()
                    try:
                        normalized = normalize_ingredients(data["ingredients_raw"])
                        for item in normalized:
                            canonical = (item.get("canonical_name") or item.get("name", "")).strip().lower()
                            if not canonical:
                                continue
                            ing = _get_or_create_ingredient(db, canonical, item.get("category", "other"), item.get("is_pantry_staple", False))
                            existing_ri = db.query(RecipeIngredient).filter(
                                RecipeIngredient.recipe_id == recipe.id,
                                RecipeIngredient.ingredient_id == ing.id,
                            ).first()
                            if not existing_ri:
                                ri = RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id, quantity=item.get("quantity"), unit=item.get("unit"), notes=item.get("notes"), raw_text=item.get("name"))
                                db.add(ri)
                    except Exception:
                        pass
                    db.commit()
                    r = _recipe_to_out(recipe)
                    r["confidence"] = "high"
                    results.append(r)
                    continue
            except Exception:
                pass

        # Low confidence or scrape failed — return as suggestion only (no DB store)
        results.append({
            "id": None,
            "url": url,
            "title": s.get("title", ""),
            "source_site": s.get("source_site"),
            "image_url": None,
            "servings": None,
            "total_time_minutes": None,
            "description": s.get("description"),
            "is_ai_suggested": True,
            "ingredients": [],
            "confidence": s.get("confidence", "low"),
        })

    return results


@router.get("")
async def list_recipes(db: Session = Depends(get_db)):
    """List all scraped recipes."""
    recipes = db.query(Recipe).order_by(Recipe.scraped_at.desc()).all()
    return [_recipe_to_out(r) for r in recipes]


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _recipe_to_out(recipe)


@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.delete(recipe)
    db.commit()
    return {"ok": True}
