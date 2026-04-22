"use client";

import { useState, useEffect } from "react";
import { api, Recipe, WeeklyPlan } from "@/lib/api";

export default function SearchPage() {
  const [tab, setTab] = useState<"url" | "mood">("url");
  const [url, setUrl] = useState("");
  const [mood, setMood] = useState("");
  const [results, setResults] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plans, setPlans] = useState<WeeklyPlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<number | "">("");
  const [adding, setAdding] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    api.mealPlan.list().then((data) => {
      setPlans(data);
      if (data.length > 0) setSelectedPlan(data[0].id);
    });
  }, []);

  const scrapeUrl = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const recipe = await api.recipes.scrape(url.trim());
      setResults([recipe]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to scrape recipe");
    } finally {
      setLoading(false);
    }
  };

  const searchMood = async () => {
    if (!mood.trim()) return;
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const recipes = await api.recipes.search(mood.trim());
      setResults(recipes);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const addToPlan = async (recipe: Recipe) => {
    if (!selectedPlan || !recipe.id) return;
    const key = String(recipe.id);
    setAdding(key);
    try {
      await api.mealPlan.addRecipe(selectedPlan as number, recipe.id);
      showToast(`Added "${recipe.title}" to plan`);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : "Failed to add recipe");
    } finally {
      setAdding(null);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {toast && (
        <div className="fixed bottom-4 right-4 bg-green-700 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm">
          {toast}
        </div>
      )}

      <h1 className="text-2xl font-bold">Find Recipes</h1>

      {/* Tab switcher */}
      <div className="flex rounded-lg border border-stone-200 overflow-hidden bg-white w-fit">
        <button
          onClick={() => setTab("url")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            tab === "url" ? "bg-green-700 text-white" : "text-stone-600 hover:bg-stone-50"
          }`}
        >
          Paste URL
        </button>
        <button
          onClick={() => setTab("mood")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            tab === "mood" ? "bg-green-700 text-white" : "text-stone-600 hover:bg-stone-50"
          }`}
        >
          Search by Mood
        </button>
      </div>

      {tab === "url" ? (
        <div className="space-y-3">
          <label className="block text-sm font-medium text-stone-700">
            Recipe URL
          </label>
          <div className="flex gap-2">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && scrapeUrl()}
              placeholder="https://thewoksoflife.com/mapo-tofu/"
              className="flex-1 px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <button
              onClick={scrapeUrl}
              disabled={loading || !url.trim()}
              className="px-4 py-2 bg-green-700 text-white rounded-lg text-sm font-medium hover:bg-green-800 disabled:opacity-50"
            >
              {loading ? "Scraping…" : "Import"}
            </button>
          </div>
          <p className="text-xs text-stone-400">
            Works with: <span className="text-stone-500">The Woks of Life, Half Baked Harvest, Okonomi Kitchen, Love and Lemons</span>, and most other recipe sites.
            Tiffy Cooks, Maangchi, Omnivore&apos;s Cookbook, and Made With Lau block automated access — use the Search by Mood tab to find their recipes.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <label className="block text-sm font-medium text-stone-700">
            What are you feeling this week?
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={mood}
              onChange={(e) => setMood(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchMood()}
              placeholder="e.g. cozy Korean weeknight, quick stir fry, something with tofu…"
              className="flex-1 px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            />
            <button
              onClick={searchMood}
              disabled={loading || !mood.trim()}
              className="px-4 py-2 bg-green-700 text-white rounded-lg text-sm font-medium hover:bg-green-800 disabled:opacity-50"
            >
              {loading ? "Searching…" : "Search"}
            </button>
          </div>
          <p className="text-xs text-stone-400">
            Claude will suggest recipes from your favorite blogs. High-confidence results are auto-scraped.
          </p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-stone-800">{results.length} recipe{results.length !== 1 ? "s" : ""} found</h2>
            {plans.length > 0 && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-stone-500">Add to:</span>
                <select
                  value={selectedPlan}
                  onChange={(e) => setSelectedPlan(Number(e.target.value))}
                  className="border border-stone-300 rounded px-2 py-1 text-sm focus:outline-none"
                >
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name || `Plan ${p.id}`}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {results.map((recipe, i) => (
            <div key={recipe.id ?? i} className="bg-white border border-stone-200 rounded-xl p-4 flex gap-4">
              {recipe.image_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={recipe.image_url}
                  alt=""
                  className="w-20 h-20 rounded-lg object-cover flex-shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <a
                    href={recipe.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-stone-900 hover:text-green-700 leading-snug"
                  >
                    {recipe.title}
                  </a>
                  {recipe.confidence === "low" && (
                    <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded flex-shrink-0">
                      Unverified
                    </span>
                  )}
                </div>
                <p className="text-xs text-stone-400 mt-0.5">
                  {recipe.source_site}
                  {recipe.total_time_minutes ? ` · ${recipe.total_time_minutes} min` : ""}
                  {recipe.servings ? ` · ${recipe.servings} servings` : ""}
                  {recipe.is_ai_suggested ? " · AI suggested" : ""}
                </p>
                {recipe.description && (
                  <p className="text-sm text-stone-600 mt-1 line-clamp-2">{recipe.description}</p>
                )}
                {recipe.ingredients.length > 0 && (
                  <p className="text-xs text-stone-400 mt-1">
                    {recipe.ingredients.length} ingredients
                  </p>
                )}
              </div>
              <div className="flex-shrink-0">
                {recipe.id ? (
                  <button
                    onClick={() => addToPlan(recipe)}
                    disabled={adding === String(recipe.id) || !selectedPlan}
                    className="px-3 py-1.5 bg-green-700 text-white rounded-lg text-sm hover:bg-green-800 disabled:opacity-50"
                  >
                    {adding === String(recipe.id) ? "Adding…" : "+ Plan"}
                  </button>
                ) : (
                  <a
                    href={recipe.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 border border-stone-300 text-stone-600 rounded-lg text-sm hover:bg-stone-50 block"
                  >
                    View →
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
