from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import WeeklyPlan, PlannedRecipe, Recipe, PantryItem, Ingredient, RecipeIngredient
from services.claude import suggest_recipe_combos

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])


class PlanIn(BaseModel):
    week_of: date
    name: Optional[str] = None


class AddRecipeIn(BaseModel):
    recipe_id: int
    servings_override: Optional[int] = None


def _plan_to_out(plan: WeeklyPlan) -> dict:
    return {
        "id": plan.id,
        "week_of": plan.week_of.isoformat(),
        "name": plan.name,
        "created_at": plan.created_at.isoformat(),
        "recipes": [_planned_recipe_to_out(pr) for pr in plan.planned_recipes],
    }


def _planned_recipe_to_out(pr: PlannedRecipe) -> dict:
    return {
        "id": pr.id,
        "recipe_id": pr.recipe_id,
        "title": pr.recipe.title,
        "url": pr.recipe.url,
        "source_site": pr.recipe.source_site,
        "image_url": pr.recipe.image_url,
        "servings": pr.servings_override or pr.recipe.servings,
        "cooked": pr.cooked,
        "cooked_at": pr.cooked_at.isoformat() if pr.cooked_at else None,
    }


@router.post("")
async def create_plan(body: PlanIn, db: Session = Depends(get_db)):
    plan = WeeklyPlan(week_of=body.week_of, name=body.name)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_to_out(plan)


@router.get("")
async def list_plans(db: Session = Depends(get_db)):
    plans = db.query(WeeklyPlan).order_by(WeeklyPlan.week_of.desc()).all()
    return [_plan_to_out(p) for p in plans]


@router.get("/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_out(plan)


@router.post("/{plan_id}/recipes")
async def add_recipe_to_plan(plan_id: int, body: AddRecipeIn, db: Session = Depends(get_db)):
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    recipe = db.query(Recipe).filter(Recipe.id == body.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    existing = db.query(PlannedRecipe).filter(
        PlannedRecipe.plan_id == plan_id,
        PlannedRecipe.recipe_id == body.recipe_id,
    ).first()
    if existing:
        return _plan_to_out(plan)

    pr = PlannedRecipe(
        plan_id=plan_id,
        recipe_id=body.recipe_id,
        servings_override=body.servings_override,
    )
    db.add(pr)
    db.commit()
    db.refresh(plan)
    return _plan_to_out(plan)


@router.delete("/{plan_id}/recipes/{recipe_id}")
async def remove_recipe_from_plan(plan_id: int, recipe_id: int, db: Session = Depends(get_db)):
    pr = db.query(PlannedRecipe).filter(
        PlannedRecipe.plan_id == plan_id,
        PlannedRecipe.recipe_id == recipe_id,
    ).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Recipe not in plan")
    db.delete(pr)
    db.commit()
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == plan_id).first()
    return _plan_to_out(plan)


@router.post("/{plan_id}/cooked/{recipe_id}")
async def mark_as_cooked(plan_id: int, recipe_id: int, db: Session = Depends(get_db)):
    """Mark a recipe as cooked and auto-deplete perishable pantry items."""
    pr = db.query(PlannedRecipe).filter(
        PlannedRecipe.plan_id == plan_id,
        PlannedRecipe.recipe_id == recipe_id,
    ).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Recipe not in plan")

    pr.cooked = True
    pr.cooked_at = datetime.utcnow()

    # Auto-deplete non-staple pantry items used in this recipe
    recipe_ingredients = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe_id
    ).all()

    depleted = []
    for ri in recipe_ingredients:
        if ri.ingredient.is_pantry_staple:
            continue  # Don't deplete condiments/spices
        pantry_item = db.query(PantryItem).filter(
            PantryItem.ingredient_id == ri.ingredient_id
        ).first()
        if pantry_item:
            db.delete(pantry_item)
            depleted.append(ri.ingredient.canonical_name)

    db.commit()
    return {"ok": True, "depleted_from_pantry": depleted}


@router.get("/{plan_id}/suggest-combos")
async def suggest_combos(plan_id: int, db: Session = Depends(get_db)):
    """Suggest recipe combinations that minimize food waste."""
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if len(plan.planned_recipes) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 recipes to suggest combos")

    recipes_data = []
    for pr in plan.planned_recipes:
        recipe = pr.recipe
        ingredients = [
            {
                "canonical_name": ri.ingredient.canonical_name,
                "is_pantry_staple": ri.ingredient.is_pantry_staple,
                "category": ri.ingredient.category,
            }
            for ri in recipe.recipe_ingredients
        ]
        recipes_data.append({
            "id": recipe.id,
            "title": recipe.title,
            "url": recipe.url,
            "ingredients": ingredients,
        })

    try:
        combos = suggest_recipe_combos(recipes_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return combos
