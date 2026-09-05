"use client";

import { useEffect, useState } from "react";

import { StatusNotice } from "@/components/status-notice";
import {
  getAnalyticsActions,
  getAnalyticsEvaluation,
  getAnalyticsOverview,
  getAnalyticsOutcomes,
  getAnalyticsRecovery,
  runRecoveryDemo,
  type AnalyticsActions,
  type AnalyticsEvaluation,
  type AnalyticsOverview,
  type AnalyticsOutcomes,
  type AnalyticsRecovery,
  type RecoveryDemoResult
} from "@/lib/api-client";
import { formatInr, formatLabel } from "@/lib/format";

function percent(value: number | null): string {
  return value === null ? "-" : `${Math.round(value * 100)}%`;
}

function Metric({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
      <p className="text-sm font-medium text-ink/60">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-ink">{value}</p>
      {note ? <p className="mt-2 text-xs leading-5 text-ink/55">{note}</p> : null}
    </article>
  );
}

function Breakdown({ title, values }: { title: string; values: Record<string, number> }) {
  const total = Object.values(values).reduce((sum, value) => sum + value, 0);
  return (
    <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <div className="mt-5 space-y-4">
        {Object.entries(values).length === 0 ? <p className="text-sm text-ink/55">No recorded data yet.</p> : null}
        {Object.entries(values).map(([key, value]) => (
          <div key={key}>
            <div className="flex justify-between text-sm">
              <span>{formatLabel(key)}</span>
              <span className="font-semibold">{value}</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-field">
              <div className="h-2 rounded-full bg-accent" style={{ width: `${total ? (value / total) * 100 : 0}%` }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function AnalyticsCenter() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [recovery, setRecovery] = useState<AnalyticsRecovery | null>(null);
  const [evaluation, setEvaluation] = useState<AnalyticsEvaluation | null>(null);
  const [actions, setActions] = useState<AnalyticsActions | null>(null);
  const [outcomes, setOutcomes] = useState<AnalyticsOutcomes | null>(null);
  const [demo, setDemo] = useState<RecoveryDemoResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    Promise.all([getAnalyticsOverview(), getAnalyticsRecovery(), getAnalyticsEvaluation(), getAnalyticsActions(), getAnalyticsOutcomes()])
      .then(([nextOverview, nextRecovery, nextEvaluation, nextActions, nextOutcomes]) => {
        setOverview(nextOverview);
        setRecovery(nextRecovery);
        setEvaluation(nextEvaluation);
        setActions(nextActions);
        setOutcomes(nextOutcomes);
        setError(null);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Analytics are unavailable."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    const handle = window.setTimeout(load, 0);
    return () => window.clearTimeout(handle);
  }, []);

  function demoRun() {
    setRunning(true);
    runRecoveryDemo()
      .then((result) => {
        setDemo(result);
        load();
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "The mock demo could not run."))
      .finally(() => setRunning(false));
  }

  const metrics = evaluation?.metrics;
  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 border-b border-line pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Performance Center</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Recovery intelligence, measured</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">Operational outcomes and deterministic evaluation in one view.</p>
        </div>
        <button type="button" onClick={demoRun} disabled={running} className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
          {running ? "Running mock demo..." : "Run Recovery Demo"}
        </button>
      </section>

      {loading ? <StatusNotice title="Loading performance data" description="Reading recovery, outcome, action, and evaluation APIs." /> : null}
      {error ? <StatusNotice title="Performance data unavailable" description={error} /> : null}
      {overview && metrics ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="Revenue at risk" value={formatInr(overview.revenue_at_risk)} />
            <Metric label="Revenue recovered" value={formatInr(overview.recovered_revenue)} note="Observed paid outcomes only." />
            <Metric label="R.AI recovery rate" value={percent(metrics.rai_recovery_rate)} />
            <Metric label="Baseline recovery rate" value={percent(metrics.baseline_recovery_rate)} />
            <Metric label="Recovery lift" value={percent(metrics.recovery_lift)} note="Synthetic evaluation metric." />
            <Metric label="AI / baseline agreement" value={percent(metrics.ai_baseline_agreement)} />
            <Metric label="Execution success rate" value={percent(metrics.execution_success_rate)} />
            <Metric label="Policy block rate" value={percent(metrics.policy_block_rate)} />
            <Metric label="Approval rate" value={percent(metrics.approval_rate)} />
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
            <div className="rounded-lg border border-line bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-ink">Baseline vs R.AI</h2>
              <p className="mt-1 text-xs text-ink/55">Synthetic evaluation on the same stored cases, not live settlement.</p>
              <div className="mt-6 grid grid-cols-2 gap-4">
                <Metric label="Baseline recoverable" value={formatInr(metrics.baseline_recoverable_revenue)} />
                <Metric label="R.AI recoverable" value={formatInr(metrics.rai_recoverable_revenue)} />
              </div>
            </div>
            {recovery ? <Breakdown title="Recovery funnel" values={recovery.funnel} /> : null}
          </section>

          <section className="grid gap-6 xl:grid-cols-3">
            {actions ? <Breakdown title="Action and workflow breakdown" values={{ ...actions.by_action, ...actions.by_workflow }} /> : null}
            {outcomes ? <Breakdown title="Outcome breakdown" values={outcomes.by_status} /> : null}
            <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
              <h2 className="text-lg font-semibold text-ink">Recent recovered cases</h2>
              <div className="mt-4 divide-y divide-line">
                {recovery?.recent_recovered.length ? recovery.recent_recovered.map((item) => (
                  <div key={item.id} className="py-3 text-sm"><p className="font-medium">{item.external_payment_id}</p><p className="mt-1 text-ink/55">{item.customer_name ?? "Unknown customer"} · {formatInr(item.recovered_amount)}</p></div>
                )) : <p className="text-sm text-ink/55">No recovered cases observed yet.</p>}
              </div>
            </section>
          </section>
        </>
      ) : null}

      {demo ? <section className="rounded-lg border border-accent/30 bg-accent/5 p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-semibold text-ink">Mock demo complete</h2><span className="text-sm font-semibold">{demo.recovered ? "Recovered" : "Observed"}</span></div><p className="mt-2 text-sm text-ink/65">{demo.disclaimer}</p><ol className="mt-4 grid gap-2 text-sm md:grid-cols-3">{demo.steps.map((step) => <li key={step.stage} className="rounded-md border border-line bg-white p-3"><span className="font-semibold">{step.label}</span><span className="mt-1 block text-ink/55">{step.detail}</span></li>)}</ol></section> : null}
    </div>
  );
}