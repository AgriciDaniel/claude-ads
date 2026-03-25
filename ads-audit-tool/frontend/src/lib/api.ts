const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (auth && typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export interface Account {
  id: string;
  name: string;
  customerId: string;
}

export interface AuditCheck {
  name: string;
  category: string;
  status: "pass" | "warn" | "fail";
  score: number;
  detail: string;
}

export interface Audit {
  id: string;
  accountId: string;
  status: "running" | "complete" | "failed";
  overallScore: number;
  categories: Record<string, number>;
  checks: AuditCheck[];
  createdAt: string;
}

export interface AuthResponse {
  token: string;
}

export function login() {
  window.location.href = `${BASE_URL}/auth/login`;
}

export function authCallback(code: string): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/callback", {
    method: "POST",
    body: { code },
    auth: false,
  });
}

export function getAccounts(): Promise<Account[]> {
  return request<Account[]>("/api/accounts");
}

export function startAudit(accountId: string): Promise<Audit> {
  return request<Audit>("/api/audits", {
    method: "POST",
    body: { accountId },
  });
}

export function getAudit(id: string): Promise<Audit> {
  return request<Audit>(`/api/audits/${id}`);
}

export function listAudits(): Promise<Audit[]> {
  return request<Audit[]>("/api/audits");
}
