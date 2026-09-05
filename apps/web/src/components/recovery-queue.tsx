"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusNotice } from "@/components/status-notice";
import { analyzeRecovery, getRecoveryCases, type RecoveryCaseListItem } from "@/lib/api-client";
import { formatDate, formatInr, formatLabel, formatScore } from "@/lib/format";

const STATUSES = ["", "open", "recovered", "resolved", "blocked"];
const PRIORITIES = ["", "high", "medium", "low"];
const ELIGIBILITY = ["", "eligible", "ineligible", "review"];
const ACTIONS = ["", "smart_retry", "payment_reminder", "alternate_payment_method", "wait", "human_review", "do_nothing"];

export function RecoveryQueue() {
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [eligibility, setEligibility] = useState("");
  const [action, setAction] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<RecoveryCaseListItem[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [analyzing, setAnalyzing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const limit = 25;

  const load = useCallback(() => {
    setState("loading");
    getRecoveryCases({
      status: status || undefined,
      priority: priority || undefined,
      eligibility: eligibility || undefined,
      suggested_action: action || undefined,
      limit,
      offset
    })
      .then((payload) => {
        setItems(payload.items);
        setTotal(payload.total);
        setState(payload.total === 0 ? "empty" : "ready");
      })
      .catch(() => setState("error"));
  }, [status, priority, eligibility, action, offset]);

  useEffect(() => {
    load();
  }, [load]);

  function runAnalysis() {
    setAnalyzing(true);
    setNotice(null);
    analyzeRecovery()
      .then((result) => {
        setNotice(
          `Analyzed ${result.payments_analyzed} payments. Created ${result.cases_created}, updated ${result.cases_updated}, skipped ${result.cases_skipped}. No payment operations executed.`
        );
        load();
      })
      .catch(() => setNotice("Analysis failed. Confirm the API is reachable."))
      .finally(() => setAnalyzing(false));
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 border-b border-line pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Recovery</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Recovery cases</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
            Deterministic baseline strategy for later comparison against R.AI&apos;s AI strategy. This
            page never retries or captures a payment.
          </p>
        </div>
        <button
          type="button"
          onClick={runAnalysis}
          disabled={analyzing}
          className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {analyzing ? "Analyzing…" : "Run analysis"}
        </button>
      </section>

      {notice ? <p className="text-sm text-ink/70">{notice}</p> : null}

      <div className="flex flex-wrap gap-3">
        <FilterSelect label="Status" value={status} options={STATUSES} onChange={(value) => { setOffset(0); setStatus(value); }} />
        <FilterSelect label="Priority" value={priority} options={PRIORITIES} onChange={(value) => { setOffset(0); setPriority(value); }} />
        <FilterSelect label="Eligibility" value={eligibility} options={ELIGIBILITY} onChange={(value) => { setOffset(0); setEligibility(value); }} />
        <FilterSelect label="Action" value={action} options={ACTIONS} onChange={(value) => { setOffset(0); setAction(value); }} />
      </div>

      {state === "loading" ? <StatusNotice title="Loading recovery cases" description="Requesting the recovery cases API." /> : null}
      {state === "error" ? <StatusNotice title="Unable to load recovery cases" description="The recovery API request failed." /> : null}
      {state === "empty" ? (
        <StatusNotice title="No recovery cases yet" description="Run analysis on failed payments or seed demo data." />
      ) : null}

      {state === "ready" ? (
        <div className="overflow-x-auto rounded-lg border border-line bg-white shadow-soft">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-ink/55">
              <tr>
                <th className="px-4 py-3 font-semibold">Recovery case</th>
                <th className="px-4 py-3 font-semibold">Amount</th>
                <th className="px-4 py-3 font-semibold">Failure</th>
                <th className="px-4 py-3 font-semibold">Score</th>
                <th className="px-4 py-3 font-semibold">Priority</th>
                <th className="px-4 py-3 font-semibold">Suggested action</th>
                <th className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-line last:border-b-0">
                  <td className="px-4 py-3">
                    <div className="font-medium text-ink">{item.external_payment_id}</div>
                    <div className="text-xs text-ink/55">{item.customer_name}</div>
                  </td>
                  <td className="px-4 py-3">{formatInr(item.revenue_at_risk)}</td>
                  <td className="px-4 py-3">{formatLabel(item.failure_category)}</td>
                  <td className="px-4 py-3">{formatScore(item.recoverability_score)}</td>
                  <td className="px-4 py-3">{formatLabel(item.priority)}</td>
                  <td className="px-4 py-3">{formatLabel(item.suggested_action)}</td>
                  <td className="px-4 py-3">{formatLabel(item.status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <div className="flex items-center justify-between text-sm text-ink/65">
        <span>{total === 0 ? "0 results" : `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}</span>
        <div className="flex gap-2">
          <button type="button" className="rounded-md border border-line px-3 py-1 disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
            Previous
          </button>
          <button type="button" className="rounded-md border border-line px-3 py-1 disabled:opacity-40" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-ink/70">
      <span>{label}</span>
      <select
        className="rounded-md border border-line bg-white px-2 py-1 text-ink"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option || "all"} value={option}>
            {option ? option.replaceAll("_", " ") : "All"}
          </option>
        ))}
      </select>
    </label>
  );
}
