import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Meal Planner",
  description: "Plan meals, minimize food waste, generate grocery lists",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={geist.className}>
      <body className="bg-stone-50 text-stone-900 min-h-screen">
        <nav className="bg-white border-b border-stone-200 sticky top-0 z-50">
          <div className="max-w-5xl mx-auto px-4 flex items-center gap-6 h-14">
            <Link href="/" className="font-semibold text-lg text-green-700 tracking-tight">
              🥦 Meal Planner
            </Link>
            <Link href="/search" className="text-sm text-stone-600 hover:text-stone-900">
              Find Recipes
            </Link>
            <Link href="/pantry" className="text-sm text-stone-600 hover:text-stone-900">
              Pantry
            </Link>
          </div>
        </nav>
        <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
