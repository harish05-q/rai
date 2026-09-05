"use client";

import { useEffect, useMemo, useState } from "react";

import { ActivityFeed } from "@/components/activity-feed";
import { HealthIndicator } from "@/components/health-indicator";
import { MetricGrid } from "@/components/metric-grid";
import { StatusNotice } from "@/components/status-notice";
import { getAgentSummary, getRecoveryCases, getRecoverySummary, type AgentSummary, type RecoverySummary } from "@/lib/api-client";
import { formatInr } from "@/lib/format";

type LoadState = "loading" | "ready" | "empty" | "error";

export function DashboardOverview() {
  const [summary, setSummary] = useState<RecoverySummary | null>(null);
  const [aiSummary, setAiSummary] = useState<AgentSummary | null>(null);
  const [activity, setActivity] = useState<{ title: string; description: string; time: string; kind: "analysis" | "strategy" | "recovered" }[]>([]);
  const [state, setState] = useState<LoadState>("loading");

  useEffect(() => {
    let active = true;

    Promise.all([
      getRecoverySummary(),
      getRecoveryCases({ limit: 5, offset: 0 }),
      getAgentSummary().catch(() => null)
    ])
      .then(([metrics, cases, agentMetrics]) => {
        if (!active) {
          return;
        }
        setSummary(metrics);
        setAiSummary(agentMetrics);
        setActivity(
          cases.items.map((item) => ({
            title: item.status === "recovered" ? "Payment recovered" : "Recovery case scored",
            description: `${item.customer_name}: ${item.suggested_action.replaceAll("_", " ")} (${item.priority} priority).`,
            time: new Date(item.created_at).toLocaleString("en-IN"),
            kind: item.status === "recovered" ? "recovered" : item.suggested_action === "smart_retry" ? "strategy" : "analysis"
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
    const atRisk = Number(summary.revenue_at_risk);
    const recovered = Number(summary.recovered_revenue);
    const denom = atRisk + recovered;
    const rate = denom > 0 ? `${((recovered / denom) * 100).toFixed(1)}%` : "0.0%";
    return [
      {
        label: "Revenue at Risk",
        value: formatInr(summary.revenue_at_risk),
        note: "Open recovery cases from failed and abandoned payments."
      },
      {
        label: "Recovered Revenue",
        value: formatInr(summary.recovered_revenue),
        note: "Synthetic cases marked recovered after deterministic analysis."
      },
      {
        label: "Recovery Rate",
        value: rate,
        note: "Recovered revenue divided by recovered plus currently at-risk revenue."
      },
      {
        label: "Active Recovery Cases",
        value: String(summary.open_recovery_cases),
        note: `${summary.recoverable_payments} eligible cases across ${summary.total_failed_payments} failed payments.`
      }
    ];
  }, [summary]);

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 border-b border-line pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Operations Dashboard</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Revenue recovery command center</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
            Sprint 3 KPIs are sourced from recovery and agent APIs. Opening the dashboard does not call
            an LLM. Analysis is recommendation-only and does not execute payments.
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

      {state === "ready" ? (
        <section className="space-y-3">
          <div>
            <h2 className="text-lg font-semibold text-ink">R.AI intelligence</h2>
            <p className="mt-1 text-sm text-ink/60">Stored recommendations only. The dashboard never triggers analysis.</p>
          </div>
          {!aiSummary || aiSummary.cases_analyzed === 0 ? (
            <StatusNotice
              title="No AI analyses yet"
              description="Open a recovery case and choose Analyze with R.AI. Mock mode works without an LLM API key."
            />
          ) : (
            <MetricGrid
              metrics={[
                {
                  label: "AI cases analyzed",
                  value: String(aiSummary.cases_analyzed),
                  note: `${aiSummary.recommendations} stored recommendations.`
                },
                {
                  label: "Average AI confidence",
                  value:
                    aiSummary.average_confidence === null
                      ? "—"
                      : `${Math.round(aiSummary.average_confidence * 100)}%`,
                  note: "Mean confidence across immutable AI decisions."
                },
                {
                  label: "AI / baseline agreement",
                  value:
                    aiSummary.agreement_rate === null ? "—" : `${Math.round(aiSummary.agreement_rate * 100)}%`,
                  note: "Neutral comparison. Disagreement is not treated as superiority."
                },
                {
                  label: "Cases requiring review",
                  value: String(aiSummary.cases_requiring_review),
                  note: "Latest stored recommendations of human review."
                }
              ]}
            />
          )}
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ActivityFeed
          items={activity}
          subtitle="Recent recovery cases from deterministic analysis."
        />
        <div className="rounded-lg border border-line bg-white p-6 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Policy posture</h2>
              <p className="mt-2 text-sm leading-6 text-ink/65">
                Recovery execution remains blocked. Suggested actions are a deterministic baseline for
                later comparison against R.AI&apos;s AI strategy.
              </p>
            </div>
            <span className="rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-xs font-semibold text-warning">
              Analyze-only
            </span>
          </div>
          <div className="mt-6 grid gap-3 text-sm text-ink/75">
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>Payment execution</span>
              <span className="font-semibold text-ink">Disabled</span>
            </div>
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>Provider credentials</span>
              <span className="font-semibold text-ink">Not configured</span>
            </div>
            <div className="flex items-center justify-between border-t border-line pt-3">
              <span>Human approval path</span>
              <span className="font-semibold text-ink">Planned</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
