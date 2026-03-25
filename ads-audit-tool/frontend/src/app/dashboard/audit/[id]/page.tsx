"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { getAudit, type Audit } from "@/lib/api";
import { ScoreGauge } from "@/components/score-gauge";
import { CheckCard } from "@/components/check-card";
import { ArrowLeft, Loader2 } from "lucide-react";

const categoryLabels: Record<string, string> = {
  account_structure: "Account Structure",
  quality_score: "Quality Score",
  budget: "Budget",
  ad_copy: "Ad Copy",
  keywords: "Keywords",
  bidding: "Bidding",
};

export default function AuditReportPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [audit, setAudit] = useState<Audit | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchAudit = useCallback(async () => {
    try {
      const data = await getAudit(params.id);
      setAudit(data);
      return data.status;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit");
      return "failed";
    }
  }, [params.id]);

  useEffect(() => {
    let timer: NodeJS.Timeout;

    async function poll() {
      const status = await fetchAudit();
      if (status === "running") {
        timer = setTimeout(poll, 3000);
      }
    }

    poll();
    return () => clearTimeout(timer);
  }, [fetchAudit]);

  if (error) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen px-6 gap-4">
        <p className="text-red-400">{error}</p>
        <button
          onClick={() => router.push("/dashboard")}
          className="text-blue-400 hover:text-blue-300 underline"
        >
          Back to dashboard
        </button>
      </main>
    );
  }

  if (!audit) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </main>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-12">
      <button
        onClick={() => router.push("/dashboard")}
        className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-8"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to dashboard
      </button>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 mb-10">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Audit Report</h1>
          <p className="text-gray-500">
            {new Date(audit.createdAt).toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>

        {audit.status === "running" ? (
          <div className="flex items-center gap-3 px-4 py-2 bg-yellow-500/10 text-yellow-400 rounded-lg">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="font-medium">Audit in progress...</span>
          </div>
        ) : (
          <ScoreGauge score={audit.overallScore} />
        )}
      </div>

      {audit.status !== "running" && audit.categories && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-10">
          {Object.entries(audit.categories).map(([key, score]) => {
            const color =
              score >= 80
                ? "border-green-500/30 text-green-400"
                : score >= 50
                  ? "border-yellow-500/30 text-yellow-400"
                  : "border-red-500/30 text-red-400";
            return (
              <div
                key={key}
                className={`p-4 bg-gray-900 border rounded-lg text-center ${color}`}
              >
                <div className="text-2xl font-bold">{score}</div>
                <div className="text-xs text-gray-400 mt-1">
                  {categoryLabels[key] || key}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {audit.checks && audit.checks.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">
            Detailed Checks ({audit.checks.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {audit.checks.map((check, i) => (
              <CheckCard key={i} check={check} />
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
