from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import WeeklyPlan, PantryItem, Ingredient
from services.claude import generate_grocery_list

router = APIRouter(prefix="/api/grocery-list", tags=["grocery"])


@router.get("/{plan_id}")
async def get_grocery_list(plan_id: int, db: Session = Depends(get_db)):
    """Generate a consolidated grocery list for a weekly plan, minus pantry items."""
    plan = db.query(WeeklyPlan).filter(WeeklyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not plan.planned_recipes:
        return []

    # Build ingredient list from all planned recipes
    recipe_ingredients = []
    for pr in plan.planned_recipes:
        servings_scale = 1.0
        if pr.servings_override and pr.recipe.servings:
            servings_scale = pr.servings_override / pr.recipe.servings

        for ri in pr.recipe.recipe_ingredients:
            qty = ri.quantity
            if qty and servings_scale != 1.0:
                qty = round(qty * servings_scale, 2)

            recipe_ingredients.append({
                "canonical_name": ri.ingredient.canonical_name,
                "quantity": qty,
                "unit": ri.unit,
                "category": ri.ingredient.category,
                "is_pantry_staple": ri.ingredient.is_pantry_staple,
                "recipe_title": pr.recipe.title,
            })

    # Get pantry
    pantry_items = db.query(PantryItem).join(Ingredient).all()
    pantry_data = [
        {
            "canonical_name": p.ingredient.canonical_name,
            "quantity": p.quantity,
            "unit": p.unit,
        }
        for p in pantry_items
    ]

    try:
        grocery_list = generate_grocery_list(recipe_ingredients, pantry_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return grocery_list
