const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Ingredient {
  id: number;
  name: string;
  quantity: number | null;
  unit: string | null;
  notes: string | null;
  category: string;
  is_pantry_staple: boolean;
  raw_text: string | null;
}

export interface Recipe {
  id: number | null;
  url: string;
  title: string;
  source_site: string | null;
  image_url: string | null;
  servings: number | null;
  total_time_minutes: number | null;
  description: string | null;
  is_ai_suggested: boolean;
  ingredients: Ingredient[];
  confidence?: "high" | "low";
}

export interface PantryItem {
  id: number;
  ingredient_id: number;
  ingredient_name: string;
  canonical_name: string;
  quantity: number | null;
  unit: string | null;
  notes: string | null;
  category: string | null;
  is_pantry_staple: boolean;
}

export interface PlannedRecipe {
  id: number;
  recipe_id: number;
  title: string;
  url: string;
  source_site: string | null;
  image_url: string | null;
  servings: number | null;
  cooked: boolean;
  cooked_at: string | null;
}

export interface WeeklyPlan {
  id: number;
  week_of: string;
  name: string | null;
  created_at: string;
  recipes: PlannedRecipe[];
}

export interface RecipeCombo {
  recipe_ids: number[];
  recipe_titles: string[];
  shared_ingredients: string[];
  shared_count: number;
  explanation: string;
}

export interface GroceryCategory {
  category: string;
  items: {
    name: string;
    quantity: number | null;
    unit: string | null;
    recipes: string[];
  }[];
}

// ─── Recipe API ───────────────────────────────────────────────────────────────

export const api = {
  recipes: {
    scrape: (url: string) =>
      req<Recipe>("/api/recipe/scrape", { method: "POST", body: JSON.stringify({ url }) }),
    search: (mood: string) =>
      req<Recipe[]>(`/api/recipe/search?mood=${encodeURIComponent(mood)}`),
    list: () => req<Recipe[]>("/api/recipe"),
    get: (id: number) => req<Recipe>(`/api/recipe/${id}`),
    delete: (id: number) => req<{ ok: boolean }>(`/api/recipe/${id}`, { method: "DELETE" }),
  },

  pantry: {
    list: () => req<PantryItem[]>("/api/pantry"),
    add: (ingredient_name: string, quantity?: number, unit?: string, notes?: string) =>
      req<PantryItem>("/api/pantry", {
        method: "POST",
        body: JSON.stringify({ ingredient_name, quantity, unit, notes }),
      }),
    remove: (id: number) => req<{ ok: boolean }>(`/api/pantry/${id}`, { method: "DELETE" }),
    autocomplete: (q: string) =>
      req<{ name: string; category: string }[]>(`/api/pantry/ingredients/autocomplete?q=${encodeURIComponent(q)}`),
  },

  mealPlan: {
    create: (week_of: string, name?: string) =>
      req<WeeklyPlan>("/api/meal-plan", { method: "POST", body: JSON.stringify({ week_of, name }) }),
    list: () => req<WeeklyPlan[]>("/api/meal-plan"),
    get: (id: number) => req<WeeklyPlan>(`/api/meal-plan/${id}`),
    addRecipe: (plan_id: number, recipe_id: number, servings_override?: number) =>
      req<WeeklyPlan>(`/api/meal-plan/${plan_id}/recipes`, {
        method: "POST",
        body: JSON.stringify({ recipe_id, servings_override }),
      }),
    removeRecipe: (plan_id: number, recipe_id: number) =>
      req<WeeklyPlan>(`/api/meal-plan/${plan_id}/recipes/${recipe_id}`, { method: "DELETE" }),
    markCooked: (plan_id: number, recipe_id: number) =>
      req<{ ok: boolean; depleted_from_pantry: string[] }>(
        `/api/meal-plan/${plan_id}/cooked/${recipe_id}`,
        { method: "POST" }
      ),
    suggestCombos: (plan_id: number) =>
      req<RecipeCombo[]>(`/api/meal-plan/${plan_id}/suggest-combos`),
  },

  grocery: {
    get: (plan_id: number) => req<GroceryCategory[]>(`/api/grocery-list/${plan_id}`),
  },
};
