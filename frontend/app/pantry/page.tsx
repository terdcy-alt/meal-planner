"use client";

import { useState, useEffect } from "react";
import { api, PantryItem } from "@/lib/api";

const CATEGORY_ORDER = ["produce", "protein", "dairy", "grain", "condiment", "spice", "oil", "pantry", "other"];

function groupByCategory(items: PantryItem[]) {
  const groups: Record<string, PantryItem[]> = {};
  for (const item of items) {
    const cat = item.category || "other";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(item);
  }
  return CATEGORY_ORDER
    .filter((cat) => groups[cat])
    .map((cat) => ({ category: cat, items: groups[cat] }));
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default function PantryPage() {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newQty, setNewQty] = useState("");
  const [newUnit, setNewUnit] = useState("");
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const loadPantry = async () => {
    const data = await api.pantry.list();
    setItems(data);
    setLoading(false);
  };

  useEffect(() => {
    loadPantry();
  }, []);

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setAdding(true);
    try {
      await api.pantry.add(
        newName.trim(),
        newQty ? parseFloat(newQty) : undefined,
        newUnit.trim() || undefined,
      );
      setNewName("");
      setNewQty("");
      setNewUnit("");
      await loadPantry();
      showToast(`Added "${newName.trim()}" to pantry`);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : "Failed to add item");
    } finally {
      setAdding(false);
    }
  };

  const removeItem = async (id: number, name: string) => {
    setRemoving(id);
    try {
      await api.pantry.remove(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      showToast(`Removed "${name}"`);
    } finally {
      setRemoving(null);
    }
  };

  const groups = groupByCategory(items);

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {toast && (
        <div className="fixed bottom-4 right-4 bg-green-700 text-white px-4 py-2 rounded-lg shadow-lg z-50 text-sm">
          {toast}
        </div>
      )}

      <h1 className="text-2xl font-bold">My Pantry</h1>
      <p className="text-sm text-stone-500">
        Items here won&apos;t appear on your grocery list. Condiments, spices, and oils are marked as staples and won&apos;t auto-deplete when you cook.
      </p>

      {/* Add item form */}
      <form onSubmit={addItem} className="bg-white border border-stone-200 rounded-xl p-4 space-y-3">
        <h2 className="font-medium text-stone-800">Add an item</h2>
        <div className="flex gap-2">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="e.g. soy sauce, green onion, tofu…"
            className="flex-1 px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            required
          />
          <input
            type="number"
            value={newQty}
            onChange={(e) => setNewQty(e.target.value)}
            placeholder="Qty"
            className="w-20 px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none"
          />
          <input
            type="text"
            value={newUnit}
            onChange={(e) => setNewUnit(e.target.value)}
            placeholder="Unit"
            className="w-24 px-3 py-2 border border-stone-300 rounded-lg text-sm focus:outline-none"
          />
          <button
            type="submit"
            disabled={adding || !newName.trim()}
            className="px-4 py-2 bg-green-700 text-white rounded-lg text-sm font-medium hover:bg-green-800 disabled:opacity-50"
          >
            {adding ? "Adding…" : "Add"}
          </button>
        </div>
      </form>

      {/* Pantry list */}
      {loading ? (
        <p className="text-stone-400 text-sm">Loading…</p>
      ) : items.length === 0 ? (
        <div className="text-center py-10 text-stone-400">
          <p>Your pantry is empty.</p>
          <p className="text-sm mt-1">Add items you already have so they don&apos;t show up on your grocery list.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map(({ category, items: catItems }) => (
            <div key={category}>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-400 mb-2">
                {capitalize(category)}
              </h3>
              <div className="bg-white border border-stone-200 rounded-xl divide-y divide-stone-100">
                {catItems.map((item) => (
                  <div key={item.id} className="flex items-center px-4 py-2.5 gap-3">
                    <div className="flex-1">
                      <span className="text-sm font-medium text-stone-800">
                        {item.canonical_name}
                      </span>
                      {item.is_pantry_staple && (
                        <span className="ml-2 text-xs text-stone-400 bg-stone-100 px-1.5 py-0.5 rounded">
                          staple
                        </span>
                      )}
                      {(item.quantity || item.unit) && (
                        <span className="ml-2 text-xs text-stone-400">
                          {item.quantity} {item.unit}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => removeItem(item.id, item.canonical_name)}
                      disabled={removing === item.id}
                      className="text-xs text-stone-400 hover:text-red-600 disabled:opacity-50"
                    >
                      {removing === item.id ? "…" : "Remove"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
