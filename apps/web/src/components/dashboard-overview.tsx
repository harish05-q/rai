"use client";

import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ActivityFeed } from "@/components/activity-feed";
import { HealthIndicator } from "@/components/health-indicator";
import { MetricGrid } from "@/components/metric-grid";
import { StatusNotice } from "@/components/status-notice";
import {
  getActions,
  getAgentSummary,
  getAnalyticsOverview,
  getExecutionSummary,
  getMerchantPolicy,
  getRecoverySummary,
  type AgentSummary,
  type AnalyticsOverview,
  type ExecutionSummary,
  type MerchantPolicy,
  type RecoverySummary
} from "@/lib/api-client";
import { formatInr } from "@/lib/format";

type LoadState = "loading" | "ready" | "empty" | "error";

export function DashboardOverview() {
  const [summary, setSummary] = useState<RecoverySummary | null>(null);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [aiSummary, setAiSummary] = useState<AgentSummary | null>(null);
  const [execution, setExecution] = useState<ExecutionSummary | null>(null);
  const [policy, setPolicy] = useState<MerchantPolicy | null>(null);
  const [activity, setActivity] = useState<{ title: string; description: string; time: string; kind: "analysis" | "strategy" | "recovered" }[]>([]);
  const [state, setState] = useState<LoadState>("loading");

  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;

    Promise.all([
      getRecoverySummary(),
      getExecutionSummary().catch(() => null),
      getMerchantPolicy().catch(() => null),
      getActions({ limit: 5 }).catch(() => ({ items: [], total: 0, limit: 5, offset: 0 })),
      getAgentSummary().catch(() => null),
      getAnalyticsOverview().catch(() => null)
    ])
      .then(([metrics, executionMetrics, merchantPolicy, actions, agentMetrics, analyticsOverview]) => {
        if (!active) {
          return;
        }
        setSummary(metrics);
        setOverview(analyticsOverview);
        setExecution(executionMetrics);
        setPolicy(merchantPolicy);
        setAiSummary(agentMetrics);
        setActivity(
          actions.items.map((item) => ({
            title: `Execution ${item.status.replaceAll("_", " ")}`,
            description: `${item.action.replaceAll("_", " ")} via ${item.provider}. Policy ${item.policy_decision.replaceAll("_", " ")}.`,
            time: new Date(item.created_at).toLocaleString("en-IN"),
            kind: item.status === "succeeded" ? "recovered" : item.status === "blocked" ? "analysis" : "strategy"
          }))
        );
        setState(metrics.total_payments === 0 ? "empty" : "ready");
      })
      .catch(() => {
        if (active) {
          setState("error");
        }
      });

    return () => {
      active = false;
    };
  }, [refresh]);

  const metrics = useMemo(() => {
    if (!summary) {
      return [];
    }
    return [
      {
        label: "Actions executed",
        value: execution ? String(execution.actions_executed) : "—",
        note: "Policy-approved executions that reached a provider or no-op success."
      },
      {
        label: "Actions blocked",
        value: execution ? String(execution.actions_blocked) : "—",
        note: "Deterministic Policy Engine denials."
      },
      {
        label: "Approvals pending",
        value: execution ? String(execution.approvals_pending) : "—",
        note: "High-value or uncertain cases waiting for an operator."
      }
    ];
  }, [summary, execution]);

  const executionMetrics = useMemo(() => {
    if (!execution) {
      return [];
    }
    const rate =
      execution.provider_success_rate === null ? "—" : `${Math.round(execution.provider_success_rate * 100)}%`;
    return [
      {
        label: "Recovery workflow amount",
        value: formatInr(execution.recovered_workflow_amount),
        note: "Amount associated with succeeded provider workflows. Not claimed as settled revenue."
      },
      {
        label: "Provider success rate",
        value: rate,
        note: `${execution.provider} provider. Failed executions are excluded from successes.`
      },
      {
        label: "Failed executions",
        value: String(execution.actions_failed),
        note: "Provider errors recorded in the audit trail."
      },
      {
        label: "AI cases analyzed",
        value: aiSummary ? String(aiSummary.cases_analyzed) : "—",
        note: "Stored recommendations. The dashboard does not trigger analysis."
      }
    ];
  }, [execution, aiSummary]);

  return (
    <div className="space-y-8">
      <section className="workspace-hero grid gap-8 xl:grid-cols-2 xl:items-end">
        <div>
          <h1>Revenue recovery</h1>
          <p className="mt-4 max-w-lg leading-7">Track revenue at risk, review recovery cases, and see which payments recovered.</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link className="rounded-md bg-white px-4 py-2 text-sm font-semibold text-ink" href="/recovery">Open recovery queue</Link>
            <Link className="rounded-md bg-field px-4 py-2 text-sm font-semibold text-ink" href="/approvals">Review approvals</Link>
          </div>
        </div>
        <dl className="grid gap-5 border-t border-white/25 pt-6 sm:grid-cols-2 xl:border-t-0 xl:pt-0" aria-busy={state === "loading"}>
          <div>
            <dt className="text-sm text-white/80">Revenue at risk</dt>
            <dd key={summary?.revenue_at_risk ?? "risk"} className="workspace-metric mt-2 break-words text-3xl tabular-nums">
              {summary ? formatInr(summary.revenue_at_risk) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-white/80">Observed recovery</dt>
            <dd key={overview?.recovered_revenue ?? "recovered"} className="workspace-metric mt-2 break-words text-3xl tabular-nums">
              {overview ? formatInr(overview.recovered_revenue) : "—"}
            </dd>
          </div>
        </dl>
      </section>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <HealthIndicator key={refresh} />
        <button type="button" className="workspace-tool" disabled={state === "loading"}
          onClick={() => { setState("loading"); setRefresh((value) => value + 1); }}>
          <RefreshCw size={15} aria-hidden /> {state === "loading" ? "Refreshing…" : "Refresh data"}
        </button>
      </div>

      {state === "loading" ? <StatusNotice title="Loading recovery metrics" description="Fetching summary data from the R.AI API." /> : null}
      {state === "error" ? (
        <StatusNotice title="Unable to load dashboard" description="The recovery summary API is unavailable. Confirm the API container is healthy." />
      ) : null}
      {state === "empty" ? (
        <StatusNotice
          title="No payment data yet"
          description="Seed the demo dataset with python scripts/seed_demo.py or docker compose exec api python -m app.data.seed."
        />
      ) : null}
      {state === "ready" ? <MetricGrid metrics={metrics} /> : null}
      {state === "ready" && execution ? (
        <details className="workspace-panel p-5">
          <summary className="cursor-pointer font-semibold">Execution and provider metrics</summary>
          <div className="mt-4"><MetricGrid metrics={executionMetrics} /></div>
        </details>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ActivityFeed items={activity} subtitle="Recent action executions from the Policy Engine and Action Executor." />
        <div className="rounded-lg border border-line bg-white p-6 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Policy posture</h2>
              <p className="mt-2 text-sm leading-6 text-ink/65">
                Autonomous execution is merchant policy. The LLM never authorizes a provider call.
              </p>
            </div>
            <span className="rounded-full border border-line bg-field px-3 py-1 text-xs font-semibold text-ink/70">
              {policy ? (policy.autonomous_execution ? "Scoped autonomy" : "Approval first") : "Unavailable"}
            </span>
          </div>
          <div className="mt-6 grid gap-3 text-sm text-ink/75">
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>High-value approval</span>
              <span className="font-semibold text-ink">{policy ? (policy.require_approval_for_high_value ? "Required" : "Off") : "—"}</span>
            </div>
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>Payment Link recovery</span>
              <span className="font-semibold text-ink">{policy ? (policy.payment_link_creation_allowed ? "Enabled" : "Disabled") : "—"}</span>
            </div>
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>Provider</span>
              <span className="font-semibold text-ink">{execution?.provider ?? "—"}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
