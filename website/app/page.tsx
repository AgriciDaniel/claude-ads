"use client";

import { useState, useRef } from "react";
import InputForm from "@/components/InputForm";
import ResultsDashboard from "@/components/ResultsDashboard";
import type { AdMetrics, AnalysisResult } from "@/lib/types";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  async function handleAnalyze(metrics: AdMetrics) {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ metrics }),
      });

      const data = await res.json();

      if (!res.ok || data.error) {
        throw new Error(data.error ?? "Analysis failed");
      }

      setResult(data.result);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setResult(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">📈</span>
            <span className="font-bold text-slate-900 text-sm sm:text-base">
              Meta Performance Analyzer
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className="hidden sm:inline">Powered by</span>
            <span className="font-semibold text-slate-700">Claude Sonnet</span>
            <span className="bg-blue-100 text-blue-700 font-semibold px-2 py-0.5 rounded-full">
              50 checks
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 space-y-10">
        {/* Hero */}
        <div className="text-center max-w-2xl mx-auto">
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-3 leading-tight">
            Diagnose Your Meta Ads
            <span className="text-blue-600"> in 60 Seconds</span>
          </h1>
          <p className="text-slate-600 text-base sm:text-lg leading-relaxed">
            Get your Meta Ads health score across 50 audit checks — Pixel/CAPI,
            creative fatigue, account structure, and targeting. Powered by the same
            framework used by top performance marketing agencies.
          </p>

          {/* Feature pills */}
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            {[
              "50-check audit",
              "Health score 0-100",
              "Quick wins",
              "Andromeda analysis",
              "EMQ evaluation",
              "Creative fatigue",
            ].map((f) => (
              <span
                key={f}
                className="text-xs bg-blue-50 text-blue-700 font-medium px-3 py-1 rounded-full border border-blue-100"
              >
                {f}
              </span>
            ))}
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
            <div className="flex justify-center mb-4">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
            <h3 className="font-semibold text-slate-800 text-lg mb-1">
              Running your 50-check audit…
            </h3>
            <p className="text-slate-500 text-sm">
              Claude is evaluating Pixel health, creative fatigue, account structure, and
              audience targeting. This takes about 15–30 seconds.
            </p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
            <p className="text-red-800 font-semibold mb-1">Analysis failed</p>
            <p className="text-red-600 text-sm">{error}</p>
            <p className="text-red-500 text-xs mt-2">
              Make sure ANTHROPIC_API_KEY is set in your .env.local file.
            </p>
          </div>
        )}

        {/* Input form (hidden while loading or showing results) */}
        {!loading && !result && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm">
            <InputForm onAnalyze={handleAnalyze} loading={loading} />
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div ref={resultsRef}>
            <ResultsDashboard result={result} onReset={handleReset} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 mt-16 py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center text-xs text-slate-400">
          <p>
            Built with{" "}
            <a
              href="https://github.com/zoeresonance/claude-ads"
              className="text-slate-500 hover:text-blue-600 underline transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              claude-ads
            </a>{" "}
            · Audit framework v1.5 · Benchmarks updated 2026
          </p>
        </div>
      </footer>
    </div>
  );
}
