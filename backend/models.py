from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, Date,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100))  # produce, dairy, protein, pantry, etc.
    is_pantry_staple: Mapped[bool] = mapped_column(Boolean, default=False)  # condiments, spices — don't auto-deplete

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(back_populates="ingredient")
    pantry_items: Mapped[list["PantryItem"]] = relationship(back_populates="ingredient")


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    source_site: Mapped[Optional[str]] = mapped_column(String(200))
    image_url: Mapped[Optional[str]] = mapped_column(String(1000))
    servings: Mapped[Optional[int]] = mapped_column(Integer)
    total_time_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    ingredients_raw: Mapped[Optional[str]] = mapped_column(Text)  # JSON array of raw strings
    description: Mapped[Optional[str]] = mapped_column(Text)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False)

    recipe_ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )
    planned_recipes: Mapped[list["PlannedRecipe"]] = relationship(back_populates="recipe")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), index=True)
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(String(300))  # "thinly sliced", "optional", etc.
    raw_text: Mapped[Optional[str]] = mapped_column(String(500))

    recipe: Mapped["Recipe"] = relationship(back_populates="recipe_ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="recipe_ingredients")

    __table_args__ = (UniqueConstraint("recipe_id", "ingredient_id"),)


class PantryItem(Base):
    __tablename__ = "pantry_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), index=True)
    quantity: Mapped[Optional[float]] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(String(300))

    ingredient: Mapped["Ingredient"] = relationship(back_populates="pantry_items")


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    week_of: Mapped[date] = mapped_column(Date, index=True)  # Monday of the week
    name: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    planned_recipes: Mapped[list["PlannedRecipe"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class PlannedRecipe(Base):
    __tablename__ = "planned_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("weekly_plans.id"), index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    servings_override: Mapped[Optional[int]] = mapped_column(Integer)
    cooked: Mapped[bool] = mapped_column(Boolean, default=False)
    cooked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    plan: Mapped["WeeklyPlan"] = relationship(back_populates="planned_recipes")
    recipe: Mapped["Recipe"] = relationship(back_populates="planned_recipes")

    __table_args__ = (UniqueConstraint("plan_id", "recipe_id"),)
