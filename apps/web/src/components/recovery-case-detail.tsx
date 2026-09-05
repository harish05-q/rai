"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { StatusNotice } from "@/components/status-notice";
import {
  analyzeAgentCase,
  getAgentCaseAnalysis,
  getRecoveryCase,
  type AgentCaseResponse,
  type RecoveryCaseDetail
} from "@/lib/api-client";
import { formatDate, formatInr, formatLabel, formatScore } from "@/lib/format";

export function RecoveryCaseDetailView({ caseId }: { caseId: string }) {
  const [detail, setDetail] = useState<RecoveryCaseDetail | null>(null);
  const [agent, setAgent] = useState<AgentCaseResponse | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setState("loading");
    Promise.all([getRecoveryCase(caseId), getAgentCaseAnalysis(caseId)])
      .then(([caseDetail, analysis]) => {
        setDetail(caseDetail);
        setAgent(analysis);
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

  const analysis = agent?.analysis;

  return (
    <div className="space-y-6">
      <p className="text-sm">
        <Link href="/recovery" className="font-medium text-accent">
          ← Recovery cases
        </Link>
      </p>

      {state === "loading" ? <StatusNotice title="Loading recovery case" description="Fetching case and any stored R.AI analysis." /> : null}
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
                Deterministic baseline plus optional R.AI recommendation. No payment action is executed from this page.
              </p>
            </div>
            <button
              type="button"
              onClick={runAnalysis}
              disabled={analyzing}
              className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {analyzing ? "Analyzing…" : "Analyze with R.AI"}
            </button>
          </section>

          {error ? <p className="text-sm text-warning">{error}</p> : null}

          <section className="grid gap-4 md:grid-cols-3">
            <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm text-ink/60">Revenue at risk</p>
              <p className="mt-2 text-2xl font-semibold">{formatInr(detail.revenue_at_risk)}</p>
            </article>
            <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm text-ink/60">Baseline action</p>
              <p className="mt-2 text-2xl font-semibold">{formatLabel(detail.suggested_action)}</p>
            </article>
            <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm text-ink/60">Recoverability</p>
              <p className="mt-2 text-2xl font-semibold">{formatScore(detail.recoverability_score)}</p>
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
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-ink/70">
              {detail.explanation_factors.map((factor) => (
                <li key={factor}>{factor}</li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-ink">R.AI analysis</h2>
                <p className="mt-1 text-sm text-ink/60">Structured recommendation compared with the deterministic baseline.</p>
              </div>
              <span className="rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-xs font-semibold text-warning">
                Recommendation only · no action executed
              </span>
            </div>

            {!analysis ? (
              <p className="mt-4 text-sm text-ink/65">This case has not been analyzed by R.AI yet.</p>
            ) : (
              <div className="mt-5 grid gap-6 lg:grid-cols-2">
                <dl className="grid gap-3 text-sm">
                  <div>
                    <dt className="text-ink/50">AI diagnosis</dt>
                    <dd className="font-medium text-ink">{formatLabel(analysis.diagnosis.failure_category)}</dd>
                    <dd className="text-ink/65">
                      Severity {formatLabel(analysis.diagnosis.failure_severity)} · recoverability{" "}
                      {formatLabel(analysis.diagnosis.recoverability_assessment)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-ink/50">Recommended strategy</dt>
                    <dd className="font-medium text-ink">{formatLabel(analysis.strategy.recommended_action)}</dd>
                    <dd className="text-ink/65">Timing {formatLabel(analysis.strategy.timing)}</dd>
                  </div>
                  <div>
                    <dt className="text-ink/50">Confidence</dt>
                    <dd>{Math.round(analysis.ai_confidence * 100)}%</dd>
                  </div>
                  <div>
                    <dt className="text-ink/50">Rationale</dt>
                    <dd className="leading-6 text-ink/75">{analysis.strategy.rationale}</dd>
                  </div>
                </dl>
                <dl className="grid gap-3 text-sm">
                  <div>
                    <dt className="text-ink/50">Baseline recommendation</dt>
                    <dd>
                      {formatLabel(analysis.baseline_action)} · score {formatScore(analysis.baseline_score)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-ink/50">AI / baseline comparison</dt>
                    <dd className="font-medium text-ink">
                      {analysis.comparison.status === "aligned" ? "Aligned" : "AI differs from baseline"}
                    </dd>
                    <dd className="mt-1 leading-6 text-ink/75">{analysis.comparison.reason}</dd>
                  </div>
                  <div>
                    <dt className="text-ink/50">Key factors</dt>
                    <dd>
                      <ul className="mt-1 list-disc space-y-1 pl-5 text-ink/75">
                        {analysis.diagnosis.key_context_factors.map((factor) => (
                          <li key={factor}>{factor}</li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                  <div>
                    <dt className="text-ink/50">Model</dt>
                    <dd>
                      {analysis.provider} · {analysis.model}
                      {analysis.ai_mode === "mock" ? " · mock mode" : ""}
                    </dd>
                    <dd className="text-ink/55">{formatDate(analysis.created_at)}</dd>
                  </div>
                </dl>
              </div>
            )}
            {agent && agent.history_count > 1 ? (
              <p className="mt-4 text-xs text-ink/50">{agent.history_count} analyses stored. Showing the latest record.</p>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}