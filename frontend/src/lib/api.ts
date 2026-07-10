import type {
  AccessibilityFinding,
  AIReport,
  AuditJob,
  Business,
  BusinessListResponse,
  BusinessStatus,
  Campaign,
  CampaignStage,
  LeadListResponse,
  LeadScore,
  LighthouseReport,
  OutreachEmail,
  Screenshot,
  SecurityFinding,
  TechnicalFinding,
  User,
  VisionAnalysis,
} from "./types";

// Relative by default — resolves against whatever origin actually served
// the page (localhost:3000, a Cloudflare Tunnel URL, a real domain, ...),
// and next.config.js's rewrites() forwards it to the backend internally.
// Override with an absolute URL only if the frontend and backend are ever
// deployed on genuinely different origins.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

const ACCESS_TOKEN_KEY = "leadforge_access_token";
const REFRESH_TOKEN_KEY = "leadforge_refresh_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getStoredToken(key: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(key);
}

export function getAccessToken(): string | null {
  return getStoredToken(ACCESS_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getStoredToken(REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;

  const data = await response.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (auth) {
      const token = getAccessToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let response = await doFetch();

  // One transparent retry after a token refresh on 401 — keeps callers simple.
  if (response.status === 401 && auth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await doFetch();
    }
  }

  if (!response.ok) {
    let code = "unknown_error";
    let message = response.statusText;
    try {
      const data = await response.json();
      code = data?.error?.code ?? code;
      message = data?.error?.message ?? message;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(response.status, code, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; refresh_token: string }>("/auth/login", {
        method: "POST",
        body: { email, password },
        auth: false,
      }),
    register: (organization_name: string, full_name: string, email: string, password: string) =>
      request<{ access_token: string; refresh_token: string }>("/auth/register", {
        method: "POST",
        body: { organization_name, full_name, email, password },
        auth: false,
      }),
    me: () => request<User>("/auth/me"),
  },

  businesses: {
    list: (params: { city?: string; category?: string; status?: BusinessStatus; page?: number } = {}) => {
      const search = new URLSearchParams();
      if (params.city) search.set("city", params.city);
      if (params.category) search.set("category", params.category);
      if (params.status) search.set("status", params.status);
      if (params.page) search.set("page", String(params.page));
      const qs = search.toString();
      return request<BusinessListResponse>(`/businesses${qs ? `?${qs}` : ""}`);
    },
    get: (id: string) => request<Business>(`/businesses/${id}`),
    create: (data: {
      name: string;
      category: string;
      city: string;
      country: string;
      website_url?: string;
      phone?: string;
      address?: string;
    }) => request<Business>("/businesses", { method: "POST", body: data }),
    archive: (id: string) => request<Business>(`/businesses/${id}/archive`, { method: "PATCH" }),
    delete: (id: string) => request<void>(`/businesses/${id}`, { method: "DELETE" }),
  },

  discovery: {
    search: (country: string, city: string, category: string, limit = 20) =>
      request<{ task_id: string; status: string }>("/discovery/search", {
        method: "POST",
        body: { country, city, category, limit },
      }),
    jobStatus: (taskId: string) =>
      request<{ task_id: string; status: string; discovered_count?: number; error?: string }>(
        `/discovery/jobs/${taskId}`,
      ),
  },

  audits: {
    start: (businessId: string) =>
      request<{ audit_job_id: string; status: string }>(`/businesses/${businessId}/audits`, { method: "POST" }),
    get: (auditJobId: string) => request<AuditJob>(`/audits/${auditJobId}`),
    lighthouse: (auditJobId: string) => request<LighthouseReport>(`/audits/${auditJobId}/lighthouse`),
    accessibility: (auditJobId: string) => request<AccessibilityFinding>(`/audits/${auditJobId}/accessibility`),
    security: (auditJobId: string) => request<SecurityFinding>(`/audits/${auditJobId}/security`),
    technical: (auditJobId: string) => request<TechnicalFinding>(`/audits/${auditJobId}/technical`),
    vision: (auditJobId: string) => request<VisionAnalysis[]>(`/audits/${auditJobId}/vision`),
    screenshots: (auditJobId: string) => request<Screenshot[]>(`/audits/${auditJobId}/screenshots`),
    report: (auditJobId: string) => request<AIReport>(`/audits/${auditJobId}/report`),
  },

  leads: {
    list: (params: { priority?: string; page?: number } = {}) => {
      const search = new URLSearchParams();
      if (params.priority) search.set("priority", params.priority);
      if (params.page) search.set("page", String(params.page));
      const qs = search.toString();
      return request<LeadListResponse>(`/leads${qs ? `?${qs}` : ""}`);
    },
    score: (businessId: string) => request<LeadScore>(`/leads/${businessId}/score`),
  },

  emails: {
    draft: (businessId: string, templateKey = "default") =>
      request<OutreachEmail>(`/businesses/${businessId}/emails`, {
        method: "POST",
        body: { template_key: templateKey },
      }),
    list: (businessId: string) => request<OutreachEmail[]>(`/businesses/${businessId}/emails`),
    update: (emailId: string, patch: Partial<Pick<OutreachEmail, "subject" | "body_text" | "body_html">>) =>
      request<OutreachEmail>(`/emails/${emailId}`, { method: "PATCH", body: patch }),
    send: (emailId: string, toAddress: string) =>
      request<OutreachEmail>(`/emails/${emailId}/send`, { method: "POST", body: { to_address: toAddress } }),
    delete: (emailId: string) => request<void>(`/emails/${emailId}`, { method: "DELETE" }),
  },

  campaigns: {
    list: (stage?: CampaignStage) =>
      request<Campaign[]>(`/campaigns${stage ? `?stage=${stage}` : ""}`),
    setStage: (campaignId: string, stage: CampaignStage) =>
      request<Campaign>(`/campaigns/${campaignId}/stage`, { method: "PATCH", body: { stage } }),
    addNote: (campaignId: string, note: string) =>
      request<Campaign>(`/campaigns/${campaignId}/notes`, { method: "POST", body: { note } }),
    setFollowUp: (campaignId: string, followUpAt: string) =>
      request<Campaign>(`/campaigns/${campaignId}/follow-up`, {
        method: "PATCH",
        body: { follow_up_at: followUpAt },
      }),
  },
};