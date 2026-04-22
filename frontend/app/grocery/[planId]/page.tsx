"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { api, GroceryCategory } from "@/lib/api";

export default function GroceryPage({ params }: { params: Promise<{ planId: string }> }) {
  const { planId } = use(params);
  const [list, setList] = useState<GroceryCategory[]>([]);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.grocery
      .get(Number(planId))
      .then((data) => { setList(data); setLoading(false); })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load grocery list");
        setLoading(false);
      });
  }, [planId]);

  const toggle = (key: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const copyToClipboard = () => {
    const text = list
      .map((cat) => {
        const items = cat.items
          .map((item) => {
            const qty = item.quantity ? `${item.quantity}${item.unit ? " " + item.unit : ""}` : "";
            return `  - ${item.name}${qty ? " (" + qty + ")" : ""}`;
          })
          .join("\n");
        return `${cat.category}:\n${items}`;
      })
      .join("\n\n");

    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const totalItems = list.reduce((acc, cat) => acc + cat.items.length, 0);
  const checkedCount = checked.size;

  return (
    <div className="max-w-lg mx-auto space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/" className="text-stone-400 hover:text-stone-700 text-sm">
          ← Back to planner
        </Link>
      </div>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Grocery List</h1>
          {!loading && (
            <p className="text-sm text-stone-400 mt-0.5">
              {checkedCount}/{totalItems} items checked
            </p>
          )}
        </div>
        {!loading && list.length > 0 && (
          <button
            onClick={copyToClipboard}
            className="px-3 py-1.5 border border-stone-300 rounded-lg text-sm hover:bg-stone-100"
          >
            {copied ? "Copied!" : "Copy list"}
          </button>
        )}
      </div>

      {loading && (
        <div className="text-stone-400 text-sm py-8 text-center">
          <p>Generating your grocery list…</p>
          <p className="text-xs mt-1">Claude is comparing recipes and your pantry</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {!loading && list.length === 0 && !error && (
        <div className="text-center py-10 text-stone-400">
          <p>Nothing to buy! Your pantry covers everything.</p>
        </div>
      )}

      {list.map((cat) => (
        <div key={cat.category}>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-stone-400 mb-2">
            {cat.category}
          </h2>
          <div className="bg-white border border-stone-200 rounded-xl divide-y divide-stone-100">
            {cat.items.map((item) => {
              const key = `${cat.category}:${item.name}`;
              const isChecked = checked.has(key);
              return (
                <label
                  key={key}
                  className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-stone-50 ${
                    isChecked ? "opacity-50" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggle(key)}
                    className="mt-0.5 h-4 w-4 rounded border-stone-300 text-green-600 focus:ring-green-500"
                  />
                  <div className="flex-1">
                    <span className={`text-sm font-medium ${isChecked ? "line-through text-stone-400" : "text-stone-800"}`}>
                      {item.name}
                    </span>
                    {(item.quantity || item.unit) && (
                      <span className="ml-2 text-xs text-stone-400">
                        {item.quantity} {item.unit}
                      </span>
                    )}
                    {item.recipes.length > 0 && (
                      <p className="text-xs text-stone-400 mt-0.5">
                        For: {item.recipes.join(", ")}
                      </p>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      ))}

      {!loading && totalItems > 0 && (
        <div className="pt-4 pb-8 text-center">
          <p className="text-sm text-stone-400">
            {totalItems - checkedCount === 0
              ? "All done! Happy cooking 🎉"
              : `${totalItems - checkedCount} item${totalItems - checkedCount !== 1 ? "s" : ""} left`}
          </p>
        </div>
      )}
    </div>
  );
}
