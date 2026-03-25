"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getAccounts,
  listAudits,
  startAudit,
  type Account,
  type Audit,
} from "@/lib/api";
import {
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
} from "lucide-react";

const statusConfig = {
  running: { label: "Running", icon: Clock, className: "bg-yellow-500/10 text-yellow-400" },
  complete: { label: "Complete", icon: CheckCircle2, className: "bg-green-500/10 text-green-400" },
  failed: { label: "Failed", icon: XCircle, className: "bg-red-500/10 text-red-400" },
} as const;

export default function DashboardPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string>("");
  const [audits, setAudits] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/");
      return;
    }

    Promise.all([getAccounts(), listAudits()])
      .then(([accts, auds]) => {
        setAccounts(accts);
        setAudits(auds);
        if (accts.length > 0) {
          setSelectedAccount(accts[0].id);
        }
      })
      .catch(() => {
        localStorage.removeItem("token");
        router.push("/");
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function handleRunAudit() {
    if (!selectedAccount) return;
    setStarting(true);
    try {
      const audit = await startAudit(selectedAccount);
      router.push(`/dashboard/audit/${audit.id}`);
    } catch {
      setStarting(false);
    }
  }

  if (loading) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold text-white mb-8">Dashboard</h1>

      <div className="flex flex-col sm:flex-row gap-4 mb-10">
        <div className="relative flex-1">
          <select
            value={selectedAccount}
            onChange={(e) => setSelectedAccount(e.target.value)}
            className="w-full appearance-none bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 pr-10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.customerId})
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
        </div>

        <button
          onClick={handleRunAudit}
          disabled={starting || !selectedAccount}
          className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors"
        >
          {starting ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Play className="w-5 h-5" />
          )}
          Run Audit
        </button>
      </div>

      <h2 className="text-xl font-semibold text-white mb-4">Previous Audits</h2>

      {audits.length === 0 ? (
        <p className="text-gray-500">No audits yet. Run your first audit above.</p>
      ) : (
        <div className="space-y-3">
          {audits.map((audit) => {
            const status = statusConfig[audit.status];
            const StatusIcon = status.icon;
            return (
              <button
                key={audit.id}
                onClick={() => router.push(`/dashboard/audit/${audit.id}`)}
                className="w-full flex items-center justify-between p-4 bg-gray-900 border border-gray-800 rounded-lg hover:border-gray-700 transition-colors text-left"
              >
                <div className="space-y-1">
                  <div className="text-white font-medium">
                    Audit {audit.id.slice(0, 8)}
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(audit.createdAt).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {audit.status === "complete" && (
                    <span className="text-2xl font-bold text-white">
                      {audit.overallScore}
                    </span>
                  )}
                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${status.className}`}
                  >
                    <StatusIcon className="w-4 h-4" />
                    {status.label}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </main>
  );
}
