"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { authCallback } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function AuthCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("Missing authorization code.");
      return;
    }

    authCallback(code)
      .then((data) => {
        localStorage.setItem("token", data.token);
        router.push("/dashboard");
      })
      .catch((err) => {
        setError(err.message || "Authentication failed.");
      });
  }, [searchParams, router]);

  return (
    <main className="flex flex-col items-center justify-center min-h-screen px-6">
      {error ? (
        <div className="text-center space-y-4">
          <div className="text-red-400 text-lg font-medium">{error}</div>
          <a
            href="/"
            className="text-blue-400 hover:text-blue-300 underline text-sm"
          >
            Back to home
          </a>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-lg">Connecting your account...</p>
        </div>
      )}
    </main>
  );
}
