from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import PantryItem, Ingredient

router = APIRouter(prefix="/api/pantry", tags=["pantry"])


class PantryItemIn(BaseModel):
    ingredient_name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class PantryItemOut(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    canonical_name: str
    quantity: Optional[float]
    unit: Optional[str]
    notes: Optional[str]
    category: Optional[str]
    is_pantry_staple: bool


def _item_to_out(item: PantryItem) -> dict:
    return {
        "id": item.id,
        "ingredient_id": item.ingredient_id,
        "ingredient_name": item.ingredient.name,
        "canonical_name": item.ingredient.canonical_name,
        "quantity": item.quantity,
        "unit": item.unit,
        "notes": item.notes,
        "category": item.ingredient.category,
        "is_pantry_staple": item.ingredient.is_pantry_staple,
    }


@router.get("")
async def list_pantry(db: Session = Depends(get_db)):
    items = db.query(PantryItem).join(Ingredient).order_by(Ingredient.category, Ingredient.canonical_name).all()
    return [_item_to_out(i) for i in items]


@router.post("")
async def add_pantry_item(body: PantryItemIn, db: Session = Depends(get_db)):
    canonical = body.ingredient_name.strip().lower()

    # Find or create ingredient
    ing = db.query(Ingredient).filter(Ingredient.canonical_name == canonical).first()
    if not ing:
        # Make a basic ingredient entry — category/staple will be unknown until a recipe uses it
        ing = Ingredient(
            name=body.ingredient_name,
            canonical_name=canonical,
            category="other",
            is_pantry_staple=False,
        )
        db.add(ing)
        db.flush()

    # Check if already in pantry
    existing = db.query(PantryItem).filter(PantryItem.ingredient_id == ing.id).first()
    if existing:
        existing.quantity = body.quantity
        existing.unit = body.unit
        existing.notes = body.notes
        db.commit()
        db.refresh(existing)
        return _item_to_out(existing)

    item = PantryItem(
        ingredient_id=ing.id,
        quantity=body.quantity,
        unit=body.unit,
        notes=body.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _item_to_out(item)


@router.delete("/{item_id}")
async def remove_pantry_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(PantryItem).filter(PantryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Pantry item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/ingredients/autocomplete")
async def autocomplete_ingredients(q: str, db: Session = Depends(get_db)):
    """Autocomplete ingredient names from known ingredients in DB."""
    results = (
        db.query(Ingredient)
        .filter(Ingredient.canonical_name.contains(q.lower()))
        .limit(10)
        .all()
    )
    return [{"name": i.canonical_name, "category": i.category} for i in results]
