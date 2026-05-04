"use client";

import { useState, useRef } from "react";
import type { AdMetrics } from "@/lib/types";
import Papa from "papaparse";

const SELECT = "select";
const TEXT = "text";

interface Field {
  key: keyof AdMetrics;
  label: string;
  type: typeof SELECT | typeof TEXT;
  options?: { value: string; label: string }[];
  placeholder?: string;
  required?: boolean;
  hint?: string;
}

const SECTIONS: { title: string; icon: string; fields: Field[] }[] = [
  {
    title: "Account Info",
    icon: "🏢",
    fields: [
      {
        key: "businessType",
        label: "Business Type",
        type: SELECT,
        required: true,
        options: [
          { value: "", label: "Select type…" },
          { value: "E-commerce", label: "E-commerce / D2C" },
          { value: "Lead Generation", label: "Lead Generation" },
          { value: "App Installs", label: "App Installs" },
          { value: "Brand Awareness", label: "Brand Awareness" },
          { value: "Local Business", label: "Local Business" },
          { value: "B2B SaaS", label: "B2B / SaaS" },
          { value: "Other", label: "Other" },
        ],
      },
      {
        key: "monthlySpend",
        label: "Monthly Ad Spend ($)",
        type: TEXT,
        placeholder: "e.g. 5000",
        hint: "Approximate monthly budget",
      },
    ],
  },
  {
    title: "Pixel & Tracking",
    icon: "📡",
    fields: [
      {
        key: "pixelInstalled",
        label: "Meta Pixel installed & firing",
        type: SELECT,
        required: true,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — firing on all pages" },
          { value: "partial", label: "Partial — not on all pages" },
          { value: "no", label: "No" },
          { value: "unsure", label: "Not sure" },
        ],
      },
      {
        key: "capiActive",
        label: "Conversions API (CAPI) active",
        type: SELECT,
        required: true,
        hint: "Server-side event tracking — critical post-iOS 14.5",
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — active alongside Pixel" },
          { value: "planned", label: "Planned but not deployed" },
          { value: "no", label: "No" },
          { value: "unsure", label: "Not sure" },
        ],
      },
      {
        key: "emqScore",
        label: "Event Match Quality (EMQ) score",
        type: TEXT,
        placeholder: "e.g. 7.2 (0–10 scale in Events Manager)",
        hint: "Find this in Meta Events Manager → Pixel → Event Match Quality",
      },
      {
        key: "eventDedup",
        label: "Event deduplication configured",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — event_id matching active" },
          { value: "no", label: "No" },
          { value: "unsure", label: "Not sure" },
        ],
      },
      {
        key: "domainVerified",
        label: "Business domain verified",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes" },
          { value: "no", label: "No" },
          { value: "unsure", label: "Not sure" },
        ],
      },
      {
        key: "attributionWindow",
        label: "Attribution window setting",
        type: SELECT,
        hint: "Post-Jan 2026: 7d/28d view-through windows were removed",
        options: [
          { value: "", label: "Select…" },
          { value: "7-day-click-1-day-view", label: "7-day click / 1-day view" },
          { value: "1-day-click", label: "1-day click only" },
          { value: "not-configured", label: "Not configured" },
          { value: "unsure", label: "Not sure" },
        ],
      },
    ],
  },
  {
    title: "Creative",
    icon: "🎨",
    fields: [
      {
        key: "creativeFormats",
        label: "Active creative formats",
        type: SELECT,
        required: true,
        hint: "Static image, video, carousel, collection, etc.",
        options: [
          { value: "", label: "Select…" },
          { value: "1", label: "1 format only" },
          { value: "2", label: "2 formats" },
          { value: "3+", label: "3 or more formats" },
        ],
      },
      {
        key: "creativesPerAdset",
        label: "Creatives per ad set",
        type: SELECT,
        required: true,
        options: [
          { value: "", label: "Select…" },
          { value: "<3", label: "Less than 3" },
          { value: "3-4", label: "3–4" },
          { value: "5-9", label: "5–9" },
          { value: "10+", label: "10 or more" },
        ],
      },
      {
        key: "daysSinceRefresh",
        label: "Days since last creative refresh",
        type: TEXT,
        placeholder: "e.g. 21",
        hint: "Andromeda compresses creative lifespan to 2–4 weeks",
      },
      {
        key: "fatigueDetected",
        label: "Creative fatigue detected (CTR drop >20% in 14 days)",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — CTR dropping" },
          { value: "no", label: "No" },
          { value: "unsure", label: "Not monitoring" },
        ],
      },
      {
        key: "ugcPercentage",
        label: "UGC / social-native content percentage",
        type: SELECT,
        hint: "User-generated content, testimonials, authentic social-style ads",
        options: [
          { value: "", label: "Select…" },
          { value: "<10%", label: "Less than 10%" },
          { value: "10-30%", label: "10–30%" },
          { value: ">30%", label: "More than 30%" },
        ],
      },
      {
        key: "videoAspectRatios",
        label: "Video aspect ratios used",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "9:16 only", label: "9:16 vertical only (Reels/Stories)" },
          { value: "multiple", label: "Multiple ratios (9:16 + others)" },
          { value: "no-9:16", label: "No 9:16 vertical video" },
          { value: "no-video", label: "No video assets" },
        ],
      },
      {
        key: "advantagePlusCreative",
        label: "Advantage+ Creative enhancements enabled",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes" },
          { value: "no", label: "No" },
          { value: "unsure", label: "Not sure" },
        ],
      },
    ],
  },
  {
    title: "Account Structure",
    icon: "🏗️",
    fields: [
      {
        key: "campaignCount",
        label: "Number of active campaigns",
        type: SELECT,
        required: true,
        options: [
          { value: "", label: "Select…" },
          { value: "1-3", label: "1–3 (recommended)" },
          { value: "4-5", label: "4–5" },
          { value: "6+", label: "6 or more" },
        ],
      },
      {
        key: "budgetType",
        label: "Budget optimization type",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "CBO", label: "CBO — Campaign Budget Optimization" },
          { value: "ABO", label: "ABO — Ad Set Budget" },
          { value: "mixed", label: "Mixed" },
          { value: "unsure", label: "Not sure" },
        ],
      },
      {
        key: "dailyBudget",
        label: "Daily ad spend ($)",
        type: TEXT,
        placeholder: "e.g. 200",
      },
      {
        key: "targetCpa",
        label: "Target CPA ($)",
        type: TEXT,
        placeholder: "e.g. 35",
        hint: "Used to check if budget ≥5× CPA",
      },
      {
        key: "learningLimitedPct",
        label: "% of ad sets in Learning Limited",
        type: SELECT,
        required: true,
        hint: ">50% in Learning Limited = Critical failure",
        options: [
          { value: "", label: "Select…" },
          { value: "<30%", label: "Less than 30% (healthy)" },
          { value: "30-50%", label: "30–50% (warning)" },
          { value: ">50%", label: "More than 50% (critical)" },
          { value: "unsure", label: "Not sure" },
        ],
      },
      {
        key: "advantagePlusSales",
        label: "Advantage+ Sales campaigns active",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes" },
          { value: "no", label: "No" },
          { value: "na", label: "N/A — not e-commerce" },
        ],
      },
      {
        key: "utmParameters",
        label: "UTM parameters on all ads",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — all ads have UTMs" },
          { value: "some", label: "Some ads only" },
          { value: "no", label: "No" },
        ],
      },
      {
        key: "abTestingActive",
        label: "Active A/B test (Experiments)",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes" },
          { value: "no", label: "No" },
        ],
      },
    ],
  },
  {
    title: "Audience",
    icon: "🎯",
    fields: [
      {
        key: "customAudiences",
        label: "Custom Audiences created",
        type: SELECT,
        required: true,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — website visitors, customer list, engagement" },
          { value: "some", label: "Some audiences created" },
          { value: "no", label: "No" },
        ],
      },
      {
        key: "lookalikeAudiences",
        label: "Lookalike Audiences active",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes" },
          { value: "no", label: "No" },
        ],
      },
      {
        key: "purchaserExclusions",
        label: "Purchasers excluded from prospecting",
        type: SELECT,
        required: true,
        hint: "Stops showing acquisition ads to existing customers",
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — converters excluded" },
          { value: "partial", label: "Partial exclusions" },
          { value: "no", label: "No" },
        ],
      },
      {
        key: "prospectingFrequency",
        label: "Prospecting frequency (7-day)",
        type: SELECT,
        hint: "Average number of times a person sees your ad in 7 days",
        options: [
          { value: "", label: "Select…" },
          { value: "<3", label: "Under 3.0 (healthy)" },
          { value: "3-5", label: "3.0–5.0 (warning)" },
          { value: ">5", label: "Over 5.0 (audience exhausted)" },
          { value: "unsure", label: "Not monitoring" },
        ],
      },
      {
        key: "retargetingFrequency",
        label: "Retargeting frequency (7-day)",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "<8", label: "Under 8.0 (healthy)" },
          { value: "8-12", label: "8.0–12.0 (warning)" },
          { value: ">12", label: "Over 12.0 (overexposing)" },
          { value: "na", label: "No retargeting campaigns" },
        ],
      },
      {
        key: "advantagePlusAudience",
        label: "Advantage+ Audience tested",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "yes", label: "Yes — tested vs manual" },
          { value: "no", label: "No" },
        ],
      },
    ],
  },
  {
    title: "Performance Metrics",
    icon: "📊",
    fields: [
      {
        key: "ctr",
        label: "Click-Through Rate (CTR %)",
        type: TEXT,
        placeholder: "e.g. 1.4",
        hint: "Benchmark: ≥1.0% for paid traffic",
      },
      {
        key: "cpc",
        label: "Cost Per Click (CPC $)",
        type: TEXT,
        placeholder: "e.g. 0.85",
      },
      {
        key: "roas",
        label: "Return on Ad Spend (ROAS)",
        type: TEXT,
        placeholder: "e.g. 2.8",
        hint: "Industry median: 2.19 — retargeting median: 3.61",
      },
      {
        key: "cpm",
        label: "Cost Per 1,000 Impressions (CPM $)",
        type: TEXT,
        placeholder: "e.g. 12.50",
      },
      {
        key: "cpl",
        label: "Cost Per Lead or CPA ($)",
        type: TEXT,
        placeholder: "e.g. 27.50",
        hint: "Lead gen benchmark: $27.66 avg",
      },
    ],
  },
  {
    title: "Organic Posts (Optional)",
    icon: "📱",
    fields: [
      {
        key: "organicPostsPerWeek",
        label: "Posts per week",
        type: TEXT,
        placeholder: "e.g. 5",
      },
      {
        key: "organicEngagementRate",
        label: "Average engagement rate (%)",
        type: TEXT,
        placeholder: "e.g. 3.2",
        hint: "Likes + comments + shares ÷ reach × 100",
      },
      {
        key: "organicReachPerPost",
        label: "Average reach per post",
        type: TEXT,
        placeholder: "e.g. 1500",
      },
      {
        key: "organicTopFormat",
        label: "Best performing content format",
        type: SELECT,
        options: [
          { value: "", label: "Select…" },
          { value: "Reels/Video", label: "Reels / Video" },
          { value: "Static Image", label: "Static Image" },
          { value: "Carousel", label: "Carousel" },
          { value: "Stories", label: "Stories" },
          { value: "Text/Link", label: "Text / Link posts" },
          { value: "unsure", label: "Not tracking" },
        ],
      },
    ],
  },
];

const EMPTY_METRICS: AdMetrics = {
  businessType: "",
  monthlySpend: "",
  pixelInstalled: "",
  capiActive: "",
  emqScore: "",
  eventDedup: "",
  domainVerified: "",
  aemConfigured: "unsure",
  attributionWindow: "",
  creativeFormats: "",
  creativesPerAdset: "",
  daysSinceRefresh: "",
  fatigueDetected: "",
  ugcPercentage: "",
  videoAspectRatios: "",
  advantagePlusCreative: "",
  campaignCount: "",
  budgetType: "",
  dailyBudget: "",
  targetCpa: "",
  learningLimitedPct: "",
  advantagePlusSales: "",
  utmParameters: "",
  abTestingActive: "",
  customAudiences: "",
  lookalikeAudiences: "",
  purchaserExclusions: "",
  prospectingFrequency: "",
  retargetingFrequency: "",
  advantagePlusAudience: "",
  ctr: "",
  cpc: "",
  roas: "",
  cpm: "",
  cpl: "",
  organicPostsPerWeek: "",
  organicEngagementRate: "",
  organicReachPerPost: "",
  organicTopFormat: "",
  additionalContext: "",
};

interface Props {
  onAnalyze: (metrics: AdMetrics) => void;
  loading: boolean;
}

export default function InputForm({ onAnalyze, loading }: Props) {
  const [metrics, setMetrics] = useState<AdMetrics>(EMPTY_METRICS);
  const [activeSection, setActiveSection] = useState(0);
  const [csvParsed, setCsvParsed] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function update(key: keyof AdMetrics, value: string) {
    setMetrics((prev) => ({ ...prev, [key]: value }));
  }

  function handleCSV(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      complete(results) {
        if (!results.data.length) return;

        const rows = results.data;
        const updates: Partial<AdMetrics> = {};

        // Aggregate numeric columns from the CSV
        function avg(col: string): number | null {
          const vals = rows
            .map((r) => parseFloat(r[col] ?? ""))
            .filter((v) => !isNaN(v));
          if (!vals.length) return null;
          return vals.reduce((a, b) => a + b, 0) / vals.length;
        }

        function sum(col: string): number | null {
          const vals = rows
            .map((r) => parseFloat(r[col] ?? ""))
            .filter((v) => !isNaN(v));
          if (!vals.length) return null;
          return vals.reduce((a, b) => a + b, 0);
        }

        const ctrVal = avg("CTR (Link Click-Through Rate)") ?? avg("CTR");
        if (ctrVal !== null) updates.ctr = (ctrVal * 100).toFixed(2);

        const cpcVal = avg("CPC (Cost per Link Click)") ?? avg("CPC");
        if (cpcVal !== null) updates.cpc = cpcVal.toFixed(2);

        const cpmVal = avg("CPM (Cost per 1,000 Impressions)") ?? avg("CPM");
        if (cpmVal !== null) updates.cpm = cpmVal.toFixed(2);

        const spendVal = sum("Amount Spent (USD)") ?? sum("Spend");
        if (spendVal !== null) updates.monthlySpend = Math.round(spendVal).toString();

        const roasVal = avg("Purchase ROAS (Return on Ad Spend)") ?? avg("ROAS");
        if (roasVal !== null) updates.roas = roasVal.toFixed(2);

        const cpaVal = avg("Cost Per Result") ?? avg("CPA") ?? avg("CPL");
        if (cpaVal !== null) updates.cpl = cpaVal.toFixed(2);

        const freqVal = avg("Frequency");
        if (freqVal !== null) {
          if (freqVal < 3) updates.prospectingFrequency = "<3";
          else if (freqVal <= 5) updates.prospectingFrequency = "3-5";
          else updates.prospectingFrequency = ">5";
        }

        // Add context note about the CSV
        const campaigns = [...new Set(rows.map((r) => r["Campaign name"] ?? r["Campaign"]).filter(Boolean))];
        if (campaigns.length) {
          updates.additionalContext = `CSV Data Import — Campaigns: ${campaigns.slice(0, 5).join(", ")}${campaigns.length > 5 ? ` (+${campaigns.length - 5} more)` : ""}`;
          updates.campaignCount =
            campaigns.length <= 3 ? "1-3" : campaigns.length <= 5 ? "4-5" : "6+";
        }

        setMetrics((prev) => ({ ...prev, ...updates }));
        setCsvParsed(true);
      },
    });
  }

  function validate(): boolean {
    const required = SECTIONS.flatMap((s) =>
      s.fields.filter((f) => f.required).map((f) => f.key)
    );
    return required.every((k) => !!metrics[k]);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) {
      alert("Please fill in all required fields (marked with *).");
      return;
    }
    onAnalyze(metrics);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* CSV Upload banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3">
        <span className="text-2xl">📁</span>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-blue-900 text-sm">
            Speed up setup: Import from Meta Ads Manager
          </p>
          <p className="text-blue-700 text-xs mt-0.5">
            Export a CSV from Ads Manager (Campaigns view, last 30 days) to auto-fill key metrics.
          </p>
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Upload CSV
            </button>
            {csvParsed && (
              <span className="text-xs text-green-700 font-medium">
                ✓ CSV imported — metrics pre-filled below
              </span>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleCSV}
          />
        </div>
      </div>

      {/* Section tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-hide">
        {SECTIONS.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setActiveSection(i)}
            className={`flex-shrink-0 text-xs px-3 py-2 rounded-lg font-medium transition-colors whitespace-nowrap ${
              activeSection === i
                ? "bg-blue-600 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:border-blue-300"
            }`}
          >
            {s.icon} {s.title}
          </button>
        ))}
      </div>

      {/* Active section fields */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <span>{SECTIONS[activeSection].icon}</span>
          {SECTIONS[activeSection].title}
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {SECTIONS[activeSection].fields.map((field) => (
            <div key={field.key} className="space-y-1">
              <label className="block text-sm font-medium text-slate-700">
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {field.hint && (
                <p className="text-xs text-slate-500">{field.hint}</p>
              )}
              {field.type === SELECT ? (
                <select
                  value={metrics[field.key] ?? ""}
                  onChange={(e) => update(field.key, e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800"
                >
                  {field.options?.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={metrics[field.key] ?? ""}
                  onChange={(e) => update(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800 placeholder-slate-400"
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Additional context */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Additional Context (optional)
        </label>
        <p className="text-xs text-slate-500 mb-2">
          Anything else that would help: campaign goals, recent changes, specific concerns.
        </p>
        <textarea
          value={metrics.additionalContext ?? ""}
          onChange={(e) => update("additionalContext", e.target.value)}
          rows={3}
          placeholder="e.g. We recently switched from manual targeting to Advantage+ audience. ROAS dropped from 3.2 to 2.1 in the last 2 weeks…"
          className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 placeholder-slate-400 resize-none"
        />
      </div>

      {/* Navigation + Submit */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setActiveSection((i) => Math.max(0, i - 1))}
            disabled={activeSection === 0}
            className="text-sm px-4 py-2 border border-slate-200 rounded-lg text-slate-600 hover:border-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            ← Previous
          </button>
          <button
            type="button"
            onClick={() => setActiveSection((i) => Math.min(SECTIONS.length - 1, i + 1))}
            disabled={activeSection === SECTIONS.length - 1}
            className="text-sm px-4 py-2 border border-slate-200 rounded-lg text-slate-600 hover:border-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors shadow-sm text-sm flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing…
            </>
          ) : (
            "Analyze My Meta Ads →"
          )}
        </button>
      </div>
    </form>
  );
}
