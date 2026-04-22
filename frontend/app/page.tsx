"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { api, WeeklyPlan, RecipeCombo } from "@/lib/api";

function getMondayOf(d: Date): string {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  date.setDate(diff);
  return date.toISOString().split("T")[0];
}

function formatDate(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export default function HomePage() {
  const [plans, setPlans] = useState<WeeklyPlan[]>([]);
  const [activePlan, setActivePlan] = useState<WeeklyPlan | null>(null);
  const [combos, setCombos] = useState<RecipeCombo[]>([]);
  const [loadingCombos, setLoadingCombos] = useState(false);
  const [loadingCooked, setLoadingCooked] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const loadPlans = useCallback(async () => {
    const data = await api.mealPlan.list();
    setPlans(data);
    if (data.length > 0 && !activePlan) {
      setActivePlan(data[0]);
    } else if (activePlan) {
      const fresh = data.find((p) => p.id === activePlan.id);
      if (fresh) setActivePlan(fresh);
    }
  }, [activePlan]);

  useEffect(() => {
    loadPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createThisWeekPlan = async () => {
    setCreating(true);
    try {
      const monday = getMondayOf(new Date());
      const plan = await api.mealPlan.create(monday, "This Week");
      await loadPlans();
      setActivePlan(plan);
    } finally {
      setCreating(false);
    }
  };

  const removeRecipe = async (recipeId: number) => {
    if (!activePlan) return;
    const updated = await api.mealPlan.removeRecipe(activePlan.id, recipeId);
    setActivePlan(updated);
    setCombos([]);
  };

  const markCooked = async (recipeId: number) => {
    if (!activePlan) return;
    setLoadingCooked(recipeId);
    try {
      const result = await api.mealPlan.markCooked(activePlan.id, recipeId);
      if (result.depleted_from_pantry.length > 0) {
        showToast(`Removed from pantry: ${result.depleted_from_pantry.join(", ")}`);
      }
      await loadPlans();
    } finally {
      setLoadingCooked(null);
    }
  };

  const getSuggestions = async () => {
    if (!activePlan) return;
    setLoadingCombos(true);
    setCombos([]);
    try {
      const data = await api.mealPlan.suggestCombos(activePlan.id);
      setCombos(data);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : "Failed to get suggestions");
    } finally {
      setLoadingCombos(false);
    }
  };

  return (
    <div className="space-y-6">
      {toast && (
        <div className="fixed bottom-4 right-4 bg-green-700 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Weekly Meal Planner</h1>
        <button
          onClick={createThisWeekPlan}
          disabled={creating}
          className="px-4 py-2 bg-green-700 text-white rounded-lg text-sm font-medium hover:bg-green-800 disabled:opacity-50"
        >
          {creating ? "Creating…" : "+ New Plan"}
        </button>
      </div>

      {plans.length === 0 ? (
        <div className="text-center py-16 text-stone-400">
          <p className="text-lg mb-4">No meal plans yet.</p>
          <button
            onClick={createThisWeekPlan}
            className="px-6 py-3 bg-green-700 text-white rounded-xl font-medium hover:bg-green-800"
          >
            Create this week&apos;s plan
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Plan selector sidebar */}
          <div className="lg:col-span-1 space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-400 mb-3">
              Your Plans
            </p>
            {plans.map((plan) => (
              <button
                key={plan.id}
                onClick={() => { setActivePlan(plan); setCombos([]); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                  activePlan?.id === plan.id
                    ? "bg-green-100 text-green-800 font-medium"
                    : "hover:bg-stone-100 text-stone-700"
                }`}
              >
                <div className="font-medium">{plan.name || "Unnamed"}</div>
                <div className="text-xs text-stone-400">
                  Week of {formatDate(plan.week_of)}
                </div>
              </button>
            ))}
          </div>

          {/* Active plan */}
          {activePlan && (
            <div className="lg:col-span-3 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">{activePlan.name || "Meal Plan"}</h2>
                  <p className="text-sm text-stone-400">
                    Week of {formatDate(activePlan.week_of)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Link
                    href={`/grocery/${activePlan.id}`}
                    className="px-3 py-1.5 bg-stone-800 text-white rounded-lg text-sm hover:bg-stone-900"
                  >
                    Grocery List →
                  </Link>
                  <Link
                    href="/search"
                    className="px-3 py-1.5 border border-stone-300 rounded-lg text-sm hover:bg-stone-100"
                  >
                    + Add Recipes
                  </Link>
                </div>
              </div>

              {activePlan.recipes.length === 0 ? (
                <div className="border-2 border-dashed border-stone-200 rounded-xl p-10 text-center text-stone-400">
                  <p className="mb-3">No recipes yet.</p>
                  <Link href="/search" className="text-green-700 font-medium hover:underline">
                    Find recipes to add →
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {activePlan.recipes.map((pr) => (
                    <div
                      key={pr.id}
                      className={`flex items-center gap-3 bg-white rounded-xl p-3 border transition-opacity ${
                        pr.cooked ? "opacity-60 border-stone-100" : "border-stone-200"
                      }`}
                    >
                      {pr.image_url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={pr.image_url}
                          alt=""
                          className="w-14 h-14 rounded-lg object-cover flex-shrink-0"
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <a
                          href={pr.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-stone-900 hover:text-green-700 truncate block"
                        >
                          {pr.title}
                        </a>
                        <p className="text-xs text-stone-400">
                          {pr.source_site}
                          {pr.servings ? ` · ${pr.servings} servings` : ""}
                          {pr.cooked && " · ✓ Cooked"}
                        </p>
                      </div>
                      <div className="flex gap-1.5 flex-shrink-0">
                        {!pr.cooked && (
                          <button
                            onClick={() => markCooked(pr.recipe_id)}
                            disabled={loadingCooked === pr.recipe_id}
                            className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded hover:bg-green-200 disabled:opacity-50"
                          >
                            {loadingCooked === pr.recipe_id ? "…" : "Mark cooked"}
                          </button>
                        )}
                        <button
                          onClick={() => removeRecipe(pr.recipe_id)}
                          className="text-xs px-2 py-1 text-red-600 hover:bg-red-50 rounded"
                        >
                          Remove
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Combo suggestions */}
              {activePlan.recipes.length >= 2 && (
                <div className="mt-4">
                  <button
                    onClick={getSuggestions}
                    disabled={loadingCombos}
                    className="text-sm text-green-700 font-medium hover:underline disabled:opacity-50"
                  >
                    {loadingCombos ? "Finding best combos…" : "✨ Suggest ingredient-saving combos"}
                  </button>

                  {combos.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {combos.map((combo, i) => (
                        <div key={i} className="bg-green-50 border border-green-200 rounded-xl p-3">
                          <p className="text-sm font-medium text-green-900">
                            {combo.recipe_titles.join(" + ")}
                          </p>
                          <p className="text-xs text-green-700 mt-1">{combo.explanation}</p>
                          {combo.shared_ingredients.length > 0 && (
                            <p className="text-xs text-stone-500 mt-1">
                              Shared: {combo.shared_ingredients.join(", ")}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
