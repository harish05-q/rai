"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  analyzeAgentCase,
  getAgentActivity,
  getAgentStatus,
  getAgentSummary,
  getRecoveryCases,
  type AgentActivityItem,
  type AgentStatus,
  type AgentSummary,
  type RecoveryCaseListItem
} from "@/lib/api-client";
import { formatDate, formatLabel, formatScore } from "@/lib/format";
import { StatusNotice } from "@/components/status-notice";

function percent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(value * 100)}%`;
}

export function AgentWorkspace() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [summary, setSummary] = useState<AgentSummary | null>(null);
  const [activity, setActivity] = useState<AgentActivityItem[]>([]);
  const [cases, setCases] = useState<RecoveryCaseListItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  const load = useCallback(() => {
    Promise.all([
      getAgentStatus(),
      getAgentSummary(),
      getAgentActivity({ limit: 20, offset: 0 }),
      getRecoveryCases({ limit: 25, offset: 0 })
    ])
      .then(([agentStatus, agentSummary, agentActivity, recoveryCases]) => {
        setStatus(agentStatus);
        setSummary(agentSummary);
        setActivity(agentActivity.items);
        setCases(recoveryCases.items);
        setSelectedId((current) => current || recoveryCases.items[0]?.id || "");
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const metrics = useMemo(() => {
    if (!summary) {
      return [];
    }
    return [
      {
        label: "Cases analyzed",
        value: String(summary.cases_analyzed),
        note: "Distinct recovery cases with a stored R.AI decision."
      },
      {
        label: "AI recommendations",
        value: String(summary.recommendations),
        note: "Immutable analysis records. Re-runs append history."
      },
      {
        label: "Average confidence",
        value: percent(summary.average_confidence),
        note: "Mean model confidence across stored decisions."
      },
      {
        label: "AI vs baseline disagreement",
        value: summary.agreement_rate === null ? "—" : percent(1 - summary.agreement_rate),
        note: `${summary.cases_requiring_review} cases recommended for human review.`
      }
    ];
  }, [summary]);

  function runAnalysis() {
    if (!selectedId) {
      return;
    }
    setAnalyzing(true);
    setError(null);
    analyzeAgentCase(selectedId)
      .then(() => load())
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "R.AI analysis is unavailable.");
      })
      .finally(() => setAnalyzing(false));
  }

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 border-b border-line pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">R.AI Agent</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Recovery intelligence and decision support</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
            R.AI analyzes a recovery opportunity, recommends a bounded strategy, and compares it with the
            deterministic baseline. Recommendations are not executed.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {status?.ai_mode === "mock" ? (
            <span className="rounded-full border border-line bg-field px-3 py-1 text-xs font-semibold text-ink/70">
              Mock mode
            </span>
          ) : (
            <span className="rounded-full border border-line bg-field px-3 py-1 text-xs font-semibold text-ink/70">
              {status?.provider || "Provider"} {status?.model ? `· ${status.model}` : ""}
            </span>
          )}
          <span className="rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-xs font-semibold text-warning">
            Recommendation only
          </span>
        </div>
      </section>

      {state === "error" ? (
        <StatusNotice
          title="Unable to load the agent workspace"
          description="The agent API is unavailable. Payments and recovery remain usable without AI."
        />
      ) : null}

      {state === "ready" && summary?.cases_analyzed === 0 ? (
        <StatusNotice
          title="No AI analyses yet"
          description="Select a recovery case and run Analyze with R.AI. Opening this page does not call the model."
        />
      ) : null}

      {state === "ready" ? (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <article key={metric.label} className="rounded-lg border border-line bg-white p-5 shadow-soft">
              <p className="text-sm font-medium text-ink/60">{metric.label}</p>
              <p className="mt-3 text-3xl font-semibold text-ink">{metric.value}</p>
              <p className="mt-3 text-sm leading-6 text-ink/60">{metric.note}</p>
            </article>
          ))}
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-lg border border-line bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-ink">Case selector</h2>
          <p className="mt-2 text-sm leading-6 text-ink/65">
            Analysis runs only when requested. No payment operation is performed.
          </p>
          <label className="mt-4 block text-sm text-ink/70">
            Recent recovery cases
            <select
              className="mt-2 w-full rounded-md border border-line bg-white px-3 py-2 text-ink"
              value={selectedId}
              onChange={(event) => setSelectedId(event.target.value)}
            >
              {cases.length === 0 ? <option value="">No cases available</option> : null}
              {cases.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.external_payment_id} · {formatLabel(item.suggested_action)} · score {formatScore(item.recoverability_score)}
                </option>
              ))}
            </select>
          </label>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={runAnalysis}
              disabled={!selectedId || analyzing}
              className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {analyzing ? "Analyzing…" : "Analyze with R.AI"}
            </button>
            {selectedId ? (
              <Link href={`/recovery/${selectedId}`} className="rounded-md border border-line px-4 py-2 text-sm font-semibold text-ink">
                Open case
              </Link>
            ) : null}
          </div>
          {error ? <p className="mt-3 text-sm text-warning">{error}</p> : null}
        </div>

        <div className="rounded-lg border border-line bg-white p-6 shadow-soft">
          <h2 className="text-lg font-semibold text-ink">AI activity</h2>
          <p className="mt-1 text-sm text-ink/60">Stored R.AI decisions only. Not live model calls.</p>
          <div className="mt-5 space-y-4">
            {activity.length === 0 ? <p className="text-sm text-ink/60">No AI activity yet.</p> : null}
            {activity.map((item) => (
              <article key={item.id} className="border-t border-line pt-4 first:border-t-0 first:pt-0">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                  <time className="text-xs font-medium text-ink/50">{formatDate(item.created_at)}</time>
                </div>
                <dl className="mt-2 grid gap-1 text-sm text-ink/70 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-ink/45">Diagnosis</dt>
                    <dd>{formatLabel(item.diagnosis_label)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-ink/45">Recommendation</dt>
                    <dd>{formatLabel(item.recommended_action)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-ink/45">Confidence</dt>
                    <dd>{percent(Number(item.confidence))}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-ink/45">Baseline</dt>
                    <dd>{formatLabel(item.baseline_action)}</dd>
                  </div>
                </dl>
                <p className="mt-2 text-sm text-ink/65">
                  Comparison: {item.comparison_status === "aligned" ? "Aligned" : "AI differs from baseline"}
                </p>
                {item.ai_mode === "mock" ? <p className="mt-1 text-xs text-ink/45">Mock decision</p> : null}
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}