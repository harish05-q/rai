"use client";

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
  }, []);

  const metrics = useMemo(() => {
    if (!summary) {
      return [];
    }
    return [
      {
        label: "Revenue at Risk",
        value: formatInr(summary.revenue_at_risk),
        note: "Open recovery cases from failed and abandoned payments."
      },
      {
        label: "Actions executed",
        value: String(execution?.actions_executed ?? 0),
        note: "Policy-approved executions that reached a provider or no-op success."
      },
      {
        label: "Revenue recovered",
        value: formatInr(overview?.recovered_revenue ?? "0.00"),
        note: "Observed paid outcomes, not successful execution intent."
      },
      {
        label: "Actions blocked",
        value: String(execution?.actions_blocked ?? 0),
        note: "Deterministic Policy Engine denials."
      },
      {
        label: "Approvals pending",
        value: String(execution?.approvals_pending ?? 0),
        note: "High-value or uncertain cases waiting for an operator."
      }
    ];
  }, [summary, execution, overview]);

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
        value: String(aiSummary?.cases_analyzed ?? 0),
        note: "Stored recommendations. The dashboard does not trigger analysis."
      }
    ];
  }, [execution, aiSummary]);

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 border-b border-line pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Operations Dashboard</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Revenue recovery command center</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
            Recovery, policy, execution, and observed outcome signals for daily operations.
          </p>
        </div>
        <HealthIndicator />
      </section>

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
      {state === "ready" && execution ? <MetricGrid metrics={executionMetrics} /> : null}

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
              {policy?.autonomous_execution ? "Autonomous scoped" : "Approval first"}
            </span>
          </div>
          <div className="mt-6 grid gap-3 text-sm text-ink/75">
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>High-value approval</span>
              <span className="font-semibold text-ink">{policy?.require_approval_for_high_value ? "Required" : "Off"}</span>
            </div>
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>Payment Link recovery</span>
              <span className="font-semibold text-ink">{policy?.payment_link_creation_allowed ? "Enabled" : "Disabled"}</span>
            </div>
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>Provider</span>
              <span className="font-semibold text-ink">{execution?.provider ?? "mock"}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
