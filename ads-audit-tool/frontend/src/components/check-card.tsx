"use client";

import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import type { AuditCheck } from "@/lib/api";

const statusConfig = {
  pass: {
    icon: CheckCircle2,
    iconColor: "text-green-400",
    barColor: "bg-green-500",
  },
  warn: {
    icon: AlertTriangle,
    iconColor: "text-yellow-400",
    barColor: "bg-yellow-500",
  },
  fail: {
    icon: XCircle,
    iconColor: "text-red-400",
    barColor: "bg-red-500",
  },
} as const;

const categoryColors: Record<string, string> = {
  "account structure": "bg-purple-500/10 text-purple-400",
  "quality score": "bg-blue-500/10 text-blue-400",
  budget: "bg-green-500/10 text-green-400",
  "ad copy": "bg-orange-500/10 text-orange-400",
  keywords: "bg-cyan-500/10 text-cyan-400",
  bidding: "bg-pink-500/10 text-pink-400",
};

interface CheckCardProps {
  check: AuditCheck;
}

export function CheckCard({ check }: CheckCardProps) {
  const status = statusConfig[check.status];
  const StatusIcon = status.icon;
  const categoryStyle =
    categoryColors[check.category.toLowerCase()] ||
    "bg-gray-500/10 text-gray-400";

  return (
    <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <StatusIcon className={`w-5 h-5 shrink-0 ${status.iconColor}`} />
          <h3 className="font-medium text-white truncate">{check.name}</h3>
        </div>
        <span
          className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium ${categoryStyle}`}
        >
          {check.category}
        </span>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Score</span>
          <span className="text-white font-medium">{check.score}/100</span>
        </div>
        <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${status.barColor}`}
            style={{ width: `${check.score}%` }}
          />
        </div>
      </div>

      <p className="text-sm text-gray-400 leading-relaxed">{check.detail}</p>
    </div>
  );
}
