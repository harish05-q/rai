"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { StatusNotice } from "@/components/status-notice";
import {
  analyzeAgentCase,
  evaluateCasePolicy,
  executeRecoveryCase,
  getActions,
  getAgentCaseAnalysis,
  getApprovals,
  getAudit,
  getRecoveryCase,
  type ActionExecution,
  type AgentCaseResponse,
  type ApprovalRequest,
  type AuditLogItem,
  type ExecutionPreview,
  type RecoveryCaseDetail
} from "@/lib/api-client";
import { formatDate, formatInr, formatLabel } from "@/lib/format";

export function RecoveryCaseDetailView({ caseId }: { caseId: string }) {
  const [detail, setDetail] = useState<RecoveryCaseDetail | null>(null);
  const [agent, setAgent] = useState<AgentCaseResponse | null>(null);
  const [preview, setPreview] = useState<ExecutionPreview | null>(null);
  const [executions, setExecutions] = useState<ActionExecution[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [audit, setAudit] = useState<AuditLogItem[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [analyzing, setAnalyzing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([
      getRecoveryCase(caseId),
      getAgentCaseAnalysis(caseId),
      getActions({ case_id: caseId, limit: 20 }),
      getApprovals({ case_id: caseId, limit: 20 }),
      getAudit({ case_id: caseId, limit: 50 })
    ])
      .then(async ([caseDetail, analysis, actions, approvalList, auditList]) => {
        setDetail(caseDetail);
        setAgent(analysis);
        setExecutions(actions.items);
        setApprovals(approvalList.items);
        setAudit(auditList.items);
        if (analysis.analysis) {
          try {
            setPreview(await evaluateCasePolicy(caseId));
          } catch {
            setPreview(null);
          }
        } else {
          setPreview(null);
        }
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [caseId]);

  useEffect(() => {
    load();
  }, [load]);

  function runAnalysis() {
    setAnalyzing(true);
    setError(null);
    analyzeAgentCase(caseId)
      .then(() => load())
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "R.AI analysis is unavailable.");
      })
      .finally(() => setAnalyzing(false));
  }

  function runExecute() {
    setExecuting(true);
    setError(null);
    executeRecoveryCase(caseId)
      .then(() => load())
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Execution is unavailable.");
      })
      .finally(() => setExecuting(false));
  }

  const analysis = agent?.analysis;
  const latest = executions[0];
  const pendingApproval = approvals.find((item) => item.status === "pending");
  const policyLabel = preview?.policy_decision ?? "not evaluated";
  const executionLabel = latest?.status ?? "none";

  return (
    <div className="space-y-6">
      <p className="text-sm">
        <Link href="/recovery" className="font-medium text-accent">
          ← Recovery cases
        </Link>
      </p>

      {state === "loading" ? <StatusNotice title="Loading recovery case" description="Fetching case, policy, and execution history." /> : null}
      {state === "error" ? (
        <StatusNotice title="Unable to load this case" description="The recovery case could not be retrieved." />
      ) : null}

      {state === "ready" && detail ? (
        <>
          <section className="flex flex-col gap-4 border-b border-line pb-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Recovery case</p>
              <h1 className="mt-2 text-3xl font-semibold text-ink">{detail.external_payment_id}</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
                R.AI recommends. The Policy Engine authorizes. The Action Executor may create a Payment Link or a
                deferred subscription workflow. Direct charges are never invented.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={runAnalysis}
                disabled={analyzing}
                className="rounded-md border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
              >
                {analyzing ? "Analyzing…" : "Analyze with R.AI"}
              </button>
              {preview?.can_execute ? (
                <button
                  type="button"
                  onClick={runExecute}
                  disabled={executing}
                  className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {executing ? "Executing…" : "Execute recovery"}
                </button>
              ) : null}
              {preview?.can_request_approval ? (
                <button
                  type="button"
                  onClick={runExecute}
                  disabled={executing}
                  className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {executing ? "Submitting…" : "Request approval"}
                </button>
              ) : null}
              {preview?.blocked ? (
                <span className="rounded-md border border-warning/30 bg-warning/10 px-4 py-2 text-sm font-semibold text-warning">
                  Blocked
                </span>
              ) : null}
              <Link href={`/audit?case=${caseId}`} className="rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink">
                View audit
              </Link>
            </div>
          </section>

          {error ? <p className="text-sm text-warning">{error}</p> : null}

          <section className="grid gap-4 md:grid-cols-4">
            <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm text-ink/60">Revenue at risk</p>
              <p className="mt-2 text-2xl font-semibold">{formatInr(detail.revenue_at_risk)}</p>
            </article>
            <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm text-ink/60">R.AI recommendation</p>
              <p className="mt-2 text-2xl font-semibold">{formatLabel(analysis?.strategy.recommended_action ?? detail.suggested_action)}</p>
            </article>
            <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm text-ink/60">Policy decision</p>
              <p className="mt-2 text-2xl font-semibold">{formatLabel(policyLabel)}</p>
            </article>
            <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm text-ink/60">Execution status</p>
              <p className="mt-2 text-2xl font-semibold">{formatLabel(executionLabel)}</p>
            </article>
          </section>

          <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-ink">Case context</h2>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-ink/50">Customer</dt>
                <dd>{detail.customer_name}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Failure</dt>
                <dd>{formatLabel(detail.failure_category)}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Method</dt>
                <dd>{formatLabel(detail.payment_method)}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Attempt</dt>
                <dd>{detail.attempt_number}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Eligibility</dt>
                <dd>{formatLabel(detail.eligibility)}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Payment history</dt>
                <dd>
                  {detail.customer_successful_payments} succeeded / {detail.customer_failed_payments} failed /{" "}
                  {detail.customer_total_payments} total
                </dd>
              </div>
            </dl>
          </section>

          <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-ink">R.AI analysis</h2>
                <p className="mt-1 text-sm text-ink/60">Structured recommendation. It cannot authorize execution.</p>
              </div>
              <span className="rounded-full border border-line bg-field px-3 py-1 text-xs font-semibold text-ink/70">
                Recommendation only until policy allows
              </span>
            </div>
            {!analysis ? (
              <p className="mt-4 text-sm text-ink/65">This case has not been analyzed by R.AI yet.</p>
            ) : (
              <dl className="mt-5 grid gap-3 text-sm md:grid-cols-2">
                <div>
                  <dt className="text-ink/50">Recommended strategy</dt>
                  <dd className="font-medium text-ink">{formatLabel(analysis.strategy.recommended_action)}</dd>
                </div>
                <div>
                  <dt className="text-ink/50">Confidence</dt>
                  <dd>{Math.round(analysis.ai_confidence * 100)}%</dd>
                </div>
                <div className="md:col-span-2">
                  <dt className="text-ink/50">Rationale</dt>
                  <dd className="leading-6 text-ink/75">{analysis.strategy.rationale}</dd>
                </div>
              </dl>
            )}
          </section>

          <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-ink">Policy and execution</h2>
            <p className="mt-1 text-sm text-ink/60">{preview?.reason ?? "Analyze the case to evaluate deterministic policy."}</p>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-ink/50">Workflow</dt>
                <dd>{formatLabel(preview?.workflow ?? latest?.workflow)}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Approval state</dt>
                <dd>{formatLabel(pendingApproval?.status ?? (latest?.approval_id ? "linked" : "none"))}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Provider</dt>
                <dd>{latest?.provider ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Provider reference</dt>
                <dd className="break-all">{latest?.provider_reference ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-ink/50">Payment link</dt>
                <dd>
                  {typeof latest?.result?.payment_link_url === "string" ? (
                    <a className="text-accent" href={latest.result.payment_link_url} target="_blank" rel="noreferrer">
                      Open link
                    </a>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-ink/50">Audit reference</dt>
                <dd>
                  {audit[0] ? (
                    <Link className="text-accent" href={`/audit?case=${caseId}`}>
                      {audit[audit.length - 1]?.id.slice(0, 8)}
                    </Link>
                  ) : (
                    "—"
                  )}
                </dd>
              </div>
            </dl>
            {latest?.status === "succeeded" && latest.result?.mock === true ? (
              <p className="mt-3 text-xs text-ink/50">Mock provider result. This is not a live Razorpay operation.</p>
            ) : null}
          </section>

          <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
            <h2 className="text-lg font-semibold text-ink">Execution history</h2>
            {executions.length === 0 ? (
              <p className="mt-3 text-sm text-ink/65">No executions yet.</p>
            ) : (
              <ul className="mt-4 divide-y divide-line text-sm">
                {executions.map((item) => (
                  <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                    <span className="font-medium">{formatLabel(item.action)}</span>
                    <span>{formatLabel(item.status)}</span>
                    <span className="text-ink/55">{formatDate(item.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
