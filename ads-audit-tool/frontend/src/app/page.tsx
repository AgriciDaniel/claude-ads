import { ArrowRight, BarChart3, Shield, Zap } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-6">
      <div className="max-w-3xl text-center space-y-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 text-blue-400 text-sm font-medium">
          <Zap className="w-4 h-4" />
          Powered by 186 weighted audit checks
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-white">
          Google Ads{" "}
          <span className="text-blue-500">Audit Tool</span>
        </h1>

        <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
          One-click audits for your Google Ads account. Get actionable insights
          on quality score, budget allocation, ad copy, keywords, and bidding
          strategy in minutes.
        </p>

        <Link
          href="/auth/login"
          className="inline-flex items-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-colors text-lg"
        >
          Connect Google Ads
          <ArrowRight className="w-5 h-5" />
        </Link>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-12">
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <BarChart3 className="w-8 h-8 text-blue-500 mb-3" />
            <h3 className="font-semibold text-white mb-1">Deep Analysis</h3>
            <p className="text-sm text-gray-400">
              Account structure, quality scores, and performance metrics reviewed automatically.
            </p>
          </div>
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <Shield className="w-8 h-8 text-green-500 mb-3" />
            <h3 className="font-semibold text-white mb-1">Best Practices</h3>
            <p className="text-sm text-gray-400">
              Every check mapped to Google Ads best practices and industry benchmarks.
            </p>
          </div>
          <div className="p-6 rounded-xl bg-gray-900 border border-gray-800">
            <Zap className="w-8 h-8 text-yellow-500 mb-3" />
            <h3 className="font-semibold text-white mb-1">Quick Fixes</h3>
            <p className="text-sm text-gray-400">
              Prioritized recommendations so you know exactly what to fix first.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
