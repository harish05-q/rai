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

export type AnalyticsOverview = {
  generated_at: string;
  data_source: string;
  synthetic: boolean;
  payments_at_risk: number;
  recoverable_cases: number;
  revenue_at_risk: string;
  recovered_revenue: string;
  recovered_cases: number;
  recovery_rate: number | null;
  successful_actions: number;
  approvals_pending: number;
  open_recovery_cases: number;
};

export type AnalyticsRecovery = {
  funnel: Record<string, number>;
  recent_recovered: Array<{
    id: string;
    external_payment_id: string;
    customer_name: string | null;
    recovered_amount: string;
    outcome_status: string | null;
    resolved_at: string | null;
  }>;
  synthetic: boolean;
};

export type AnalyticsEvaluation = {
  synthetic: boolean;
  disclaimer: string;
  cases_evaluated: number;
  metrics: {
    revenue_at_risk: string;
    baseline_recoverable_revenue: string;
    rai_recoverable_revenue: string;
    baseline_recovery_rate: number | null;
    rai_recovery_rate: number | null;
    recovery_lift: number | null;
    ai_baseline_agreement: number | null;
    policy_block_rate: number | null;
    approval_rate: number | null;
    execution_success_rate: number | null;
    revenue_actually_recovered: string;
  };
};

export type AnalyticsActions = {
  total: number;
  by_status: Record<string, number>;
  by_workflow: Record<string, number>;
  by_action: Record<string, number>;
  execution_success_rate: number | null;
  policy_block_rate: number | null;
  provider: string;
};

export type AnalyticsOutcomes = {
  total: number;
  by_status: Record<string, number>;
  amount_recovered: string;
};

export type RecoveryOutcome = {
  id: string;
  outcome_status: string;
  provider: string;
  provider_reference: string | null;
  workflow: string;
  amount_recovered: string | null;
  observed_at: string;
  source: string;
};

export type RecoveryDemoResult = {
  demo: true;
  mock: true;
  charges_real_customer: false;
  disclaimer: string;
  case_id: string;
  execution_status: string | null;
  outcome_status: string | null;
  recovered: boolean;
  recovered_amount: string | null;
  steps: Array<{ stage: string; label: string; detail: string }>;
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

export type MerchantPolicy = {
  id: string;
  merchant_id: string;
  autonomous_execution: boolean;
  max_autonomous_action_amount: string;
  high_value_threshold: string;
  max_recovery_attempts: number;
  payment_link_creation_allowed: boolean;
  notifications_allowed: boolean;
  subscription_recovery_allowed: boolean;
  require_approval_for_high_value: boolean;
  require_approval_for_uncertain: boolean;
  policy_version: string;
  updated_at: string;
};

export type ExecutionPreview = {
  case_id: string;
  requested_action: string;
  policy_decision: string;
  reason: string;
  required_approval: boolean;
  workflow: string;
  policy_version: string;
  limits_checked: string[];
  can_execute: boolean;
  can_request_approval: boolean;
  blocked: boolean;
  recommendation_only: boolean;
  ai_decision_id: string | null;
};

export type ExecuteResponse = {
  case_id: string;
  requested_action: string;
  policy_decision: string;
  execution_status: string;
  execution_id: string | null;
  provider: string | null;
  provider_reference: string | null;
  payment_link: string | null;
  recommendation_only: boolean;
  audit_id: string | null;
  approval_id: string | null;
  reason: string | null;
  workflow: string | null;
  mock: boolean | null;
};

export type ActionExecution = {
  id: string;
  recovery_case_id: string;
  ai_decision_id: string | null;
  action: string;
  workflow: string;
  provider: string;
  provider_reference: string | null;
  status: string;
  policy_decision: string;
  approval_id: string | null;
  result: Record<string, unknown>;
  created_at: string;
  completed_at: string | null;
};

export type PaginatedActions = {
  items: ActionExecution[];
  total: number;
  limit: number;
  offset: number;
};

export type ExecutionSummary = {
  actions_executed: number;
  actions_blocked: number;
  actions_failed: number;
  approvals_pending: number;
  recovered_workflow_amount: string;
  provider_success_rate: number | null;
  provider: string;
};

export type ApprovalRequest = {
  id: string;
  recovery_case_id: string;
  action_execution_id: string;
  reason: string;
  amount: string;
  requested_action: string;
  status: string;
  requested_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
  expires_at: string | null;
  customer_name: string | null;
  recommended_action: string | null;
  external_payment_id: string | null;
};

export type PaginatedApprovals = {
  items: ApprovalRequest[];
  total: number;
  limit: number;
  offset: number;
};

export type AuditLogItem = {
  id: string;
  actor: string;
  source: string;
  recovery_case_id: string | null;
  ai_decision_id: string | null;
  action_execution_id: string | null;
  approval_id: string | null;
  policy_decision: string | null;
  requested_action: string | null;
  executed_action: string | null;
  provider: string | null;
  provider_reference: string | null;
  status: string;
  reason: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type PaginatedAudit = {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
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

async function apiPut<T>(path: string, body: Record<string, unknown> = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
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

export function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  return apiGet<AnalyticsOverview>("/api/v1/analytics/overview");
}

export function getAnalyticsRecovery(): Promise<AnalyticsRecovery> {
  return apiGet<AnalyticsRecovery>("/api/v1/analytics/recovery");
}

export function getAnalyticsEvaluation(): Promise<AnalyticsEvaluation> {
  return apiGet<AnalyticsEvaluation>("/api/v1/analytics/evaluation");
}

export function getAnalyticsActions(): Promise<AnalyticsActions> {
  return apiGet<AnalyticsActions>("/api/v1/analytics/actions");
}

export function getAnalyticsOutcomes(): Promise<AnalyticsOutcomes> {
  return apiGet<AnalyticsOutcomes>("/api/v1/analytics/outcomes");
}

export function runRecoveryDemo(): Promise<RecoveryDemoResult> {
  return apiPost<RecoveryDemoResult>("/api/v1/demo/recovery");
}

export function getRecoveryOutcomes(caseId: string): Promise<{ items: RecoveryOutcome[]; total: number }> {
  return apiGet<{ items: RecoveryOutcome[]; total: number }>(`/api/v1/outcomes/cases/${caseId}`);
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

export function getMerchantPolicy(): Promise<MerchantPolicy> {
  return apiGet<MerchantPolicy>("/api/v1/policies");
}

export function updateMerchantPolicy(body: Partial<MerchantPolicy>): Promise<MerchantPolicy> {
  return apiPut<MerchantPolicy>("/api/v1/policies", body as Record<string, unknown>);
}

export function evaluateCasePolicy(caseId: string): Promise<ExecutionPreview> {
  return apiGet<ExecutionPreview>(`/api/v1/policies/evaluate/${caseId}`);
}

export function executeRecoveryCase(caseId: string): Promise<ExecuteResponse> {
  return apiPost<ExecuteResponse>(`/api/v1/recovery/cases/${caseId}/execute`);
}

export function getActions(params: { case_id?: string; status?: string; limit?: number; offset?: number } = {}): Promise<PaginatedActions> {
  return apiGet<PaginatedActions>(
    withQuery("/api/v1/actions", {
      case_id: params.case_id,
      status: params.status,
      limit: params.limit,
      offset: params.offset
    })
  );
}

export function getAction(actionId: string): Promise<ActionExecution> {
  return apiGet<ActionExecution>(`/api/v1/actions/${actionId}`);
}

export function getExecutionSummary(): Promise<ExecutionSummary> {
  return apiGet<ExecutionSummary>("/api/v1/actions/summary");
}

export function getApprovals(params: { status?: string; case_id?: string; limit?: number; offset?: number } = {}): Promise<PaginatedApprovals> {
  return apiGet<PaginatedApprovals>(
    withQuery("/api/v1/approvals", {
      status: params.status,
      case_id: params.case_id,
      limit: params.limit,
      offset: params.offset
    })
  );
}

export function approveRequest(approvalId: string, note?: string): Promise<ExecuteResponse> {
  return apiPost<ExecuteResponse>(`/api/v1/approvals/${approvalId}/approve`, note ? { note } : {});
}

export function rejectRequest(approvalId: string, note?: string): Promise<ExecuteResponse> {
  return apiPost<ExecuteResponse>(`/api/v1/approvals/${approvalId}/reject`, note ? { note } : {});
}

export function getAudit(params: { case_id?: string; action_execution_id?: string; limit?: number; offset?: number } = {}): Promise<PaginatedAudit> {
  return apiGet<PaginatedAudit>(
    withQuery("/api/v1/audit", {
      case_id: params.case_id,
      action_execution_id: params.action_execution_id,
      limit: params.limit,
      offset: params.offset
    })
  );
}
