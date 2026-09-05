"use client";

import { useCallback, useEffect, useState } from "react";

import { StatusNotice } from "@/components/status-notice";
import { getPayments, type PaymentListItem } from "@/lib/api-client";
import { formatDate, formatInr, formatLabel } from "@/lib/format";

const STATUSES = ["", "succeeded", "failed", "abandoned", "pending"];
const METHODS = ["", "card", "upi", "netbanking", "wallet"];
const FAILURES = [
  "",
  "temporary_timeout",
  "insufficient_funds",
  "expired_card",
  "authentication_failure",
  "declined",
  "abandoned_checkout",
  "non_recoverable",
  "other"
];

export function PaymentsTable() {
  const [status, setStatus] = useState("");
  const [method, setMethod] = useState("");
  const [failure, setFailure] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<PaymentListItem[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const limit = 25;

  const load = useCallback(() => {
    getPayments({
      status: status || undefined,
      payment_method: method || undefined,
      failure_category: failure || undefined,
      limit,
      offset
    })
      .then((payload) => {
        setItems(payload.items);
        setTotal(payload.total);
        setState(payload.total === 0 ? "empty" : "ready");
      })
      .catch(() => setState("error"));
  }, [status, method, failure, offset]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <section className="border-b border-line pb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Payments</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Payment events</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
          Synthetic payment traffic used to exercise recoverability scoring. No live processor calls.
        </p>
      </section>

      <div className="flex flex-wrap gap-3">
        <FilterSelect label="Status" value={status} options={STATUSES} onChange={(value) => { setOffset(0); setStatus(value); }} />
        <FilterSelect label="Method" value={method} options={METHODS} onChange={(value) => { setOffset(0); setMethod(value); }} />
        <FilterSelect label="Failure" value={failure} options={FAILURES} onChange={(value) => { setOffset(0); setFailure(value); }} />
      </div>

      {state === "loading" ? <StatusNotice title="Loading payments" description="Requesting the payments API." /> : null}
      {state === "error" ? <StatusNotice title="Unable to load payments" description="The payments API request failed." /> : null}
      {state === "empty" ? (
        <StatusNotice title="No payments match these filters" description="Adjust filters or seed demo data with scripts/seed_demo.py." />
      ) : null}

      {state === "ready" ? (
        <div className="overflow-x-auto rounded-lg border border-line bg-white shadow-soft">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-ink/55">
              <tr>
                <th className="px-4 py-3 font-semibold">Payment ID</th>
                <th className="px-4 py-3 font-semibold">Amount</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Method</th>
                <th className="px-4 py-3 font-semibold">Failure</th>
                <th className="px-4 py-3 font-semibold">Customer</th>
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Recovery</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-line last:border-b-0">
                  <td className="px-4 py-3 font-medium text-ink">{item.external_payment_id}</td>
                  <td className="px-4 py-3">{formatInr(item.amount)}</td>
                  <td className="px-4 py-3">{formatLabel(item.status)}</td>
                  <td className="px-4 py-3">{formatLabel(item.payment_method)}</td>
                  <td className="px-4 py-3">{formatLabel(item.failure_category)}</td>
                  <td className="px-4 py-3">{item.customer_name}</td>
                  <td className="px-4 py-3">{formatDate(item.created_at)}</td>
                  <td className="px-4 py-3">{formatLabel(item.recovery_status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <Pagination offset={offset} limit={limit} total={total} onChange={setOffset} />
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

function Pagination({
  offset,
  limit,
  total,
  onChange
}: {
  offset: number;
  limit: number;
  total: number;
  onChange: (value: number) => void;
}) {
  const next = offset + limit;
  return (
    <div className="flex items-center justify-between text-sm text-ink/65">
      <span>
        {total === 0 ? "0 results" : `${offset + 1}–${Math.min(next, total)} of ${total}`}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded-md border border-line px-3 py-1 disabled:opacity-40"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          Previous
        </button>
        <button
          type="button"
          className="rounded-md border border-line px-3 py-1 disabled:opacity-40"
          disabled={next >= total}
          onClick={() => onChange(next)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
