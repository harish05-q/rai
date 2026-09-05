export type HealthResponse = {
  status: "ok";
  service: "rai-api";
};

export type PaymentListItem = {
  id: string;
  external_payment_id: string;
  amount: string;
  currency: string;
  status: string;
  payment_method: string;
  failure_category: string | null;
  customer_name: string;
  customer_email: string;
  created_at: string;
  recovery_status: string | null;
};

export type PaginatedPayments = {
  items: PaymentListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type RecoveryCaseListItem = {
  id: string;
  payment_id: string;
  external_payment_id: string;
  revenue_at_risk: string;
  currency: string;
  failure_category: string | null;
  recoverability_score: string;
  priority: string;
  eligibility: string;
  suggested_action: string;
  status: string;
  customer_name: string;
  explanation_factors: string[];
  created_at: string;
};

export type PaginatedRecoveryCases = {
  items: RecoveryCaseListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type RecoverySummary = {
  total_payments: number;
  total_failed_payments: number;
  recoverable_payments: number;
  revenue_at_risk: string;
  open_recovery_cases: number;
  recovered_cases: number;
  recovered_revenue: string;
};

export type AnalyzeResponse = {
  payments_analyzed: number;
  cases_created: number;
  cases_updated: number;
  cases_skipped: number;
  executed_payment_operations: boolean;
};

export type RecoveryCaseDetail = RecoveryCaseListItem & {
  payment_method: string;
  attempt_number: number;
  checkout_completed: boolean;
  failure_code: string | null;
  failure_message: string | null;
  customer_successful_payments: number;
  customer_failed_payments: number;
  customer_total_payments: number;
};

export type AIDiagnosis = {
  failure_category: string;
  failure_severity: string;
  recoverability_assessment: string;
  key_context_factors: string[];
};

export type AIStrategy = {
  recommended_action: string;
  rationale: string;
  confidence: number;
  timing: string;
  alternative_action: string | null;
  concerns: string[];
};

export type AIRecoveryDecision = {
  id: string;
  case_id: string;
  diagnosis: AIDiagnosis;
  strategy: AIStrategy;
  baseline_action: string;
  baseline_score: string;
  ai_confidence: number;
  comparison: {
    status: string;
    reason: string;
  };
  model: string;
  provider: string;
  ai_mode: string;
  recommendation_only: boolean;
  created_at: string;
};

export type AgentCaseResponse = {
  case_id: string;
  analysis: AIRecoveryDecision | null;
  history_count: number;
  recommendation_only: boolean;
};

export type AgentActivityItem = {
  id: string;
  case_id: string;
  external_payment_id: string;
  title: string;
  diagnosis_label: string;
  recommended_action: string;
  confidence: string;
  baseline_action: string;
  comparison_status: string;
  comparison_reason: string;
  ai_mode: string;
  created_at: string;
};

export type PaginatedAgentActivity = {
  items: AgentActivityItem[];
  total: number;
  limit: number;
  offset: number;
};

export type AgentSummary = {
  cases_analyzed: number;
  recommendations: number;
  average_confidence: number | null;
  agreement_rate: number | null;
  cases_requiring_review: number;
  ai_mode: string;
  recommendation_only: boolean;
};

export type AgentStatus = {
  ai_mode: string;
  provider: string;
  model: string;
  available: boolean;
  recommendation_only: boolean;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function readApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown; error?: string };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (body.detail && typeof body.detail === "object" && "message" in body.detail) {
      const message = (body.detail as { message?: unknown }).message;
      if (typeof message === "string") {
        return message;
      }
    }
    if (typeof body.error === "string") {
      return body.error;
    }
  } catch {
    /* use status fallback */
  }
  return `API request failed with status ${response.status}`;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json"
    },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return response.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: Record<string, unknown> = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    cache: "no-store",
    body: JSON.stringify(body)
  });

  if (!response.ok) {
    throw new Error(await readApiError(response));
  }

  return response.json() as Promise<T>;
}

function withQuery(path: string, params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export function getHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}

export function getPayments(params: {
  status?: string;
  payment_method?: string;
  failure_category?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedPayments> {
  return apiGet<PaginatedPayments>(
    withQuery("/api/v1/payments", {
      status: params.status,
      payment_method: params.payment_method,
      failure_category: params.failure_category,
      limit: params.limit,
      offset: params.offset
    })
  );
}

export function getRecoveryCases(params: {
  status?: string;
  priority?: string;
  eligibility?: string;
  suggested_action?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedRecoveryCases> {
  return apiGet<PaginatedRecoveryCases>(
    withQuery("/api/v1/recovery/cases", {
      status: params.status,
      priority: params.priority,
      eligibility: params.eligibility,
      suggested_action: params.suggested_action,
      limit: params.limit,
      offset: params.offset
    })
  );
}

export function getRecoverySummary(): Promise<RecoverySummary> {
  return apiGet<RecoverySummary>("/api/v1/recovery/summary");
}

export function analyzeRecovery(): Promise<AnalyzeResponse> {
  return apiPost<AnalyzeResponse>("/api/v1/recovery/analyze");
}

export function getRecoveryCase(caseId: string): Promise<RecoveryCaseDetail> {
  return apiGet<RecoveryCaseDetail>(`/api/v1/recovery/cases/${caseId}`);
}

export function getAgentStatus(): Promise<AgentStatus> {
  return apiGet<AgentStatus>("/api/v1/agent/status");
}

export function getAgentSummary(): Promise<AgentSummary> {
  return apiGet<AgentSummary>("/api/v1/agent/summary");
}

export function getAgentActivity(params: { limit?: number; offset?: number } = {}): Promise<PaginatedAgentActivity> {
  return apiGet<PaginatedAgentActivity>(
    withQuery("/api/v1/agent/activity", {
      limit: params.limit,
      offset: params.offset
    })
  );
}

export function getAgentCaseAnalysis(caseId: string): Promise<AgentCaseResponse> {
  return apiGet<AgentCaseResponse>(`/api/v1/agent/cases/${caseId}`);
}

export function analyzeAgentCase(caseId: string): Promise<AIRecoveryDecision> {
  return apiPost<AIRecoveryDecision>(`/api/v1/agent/analyze/${caseId}`);
}
