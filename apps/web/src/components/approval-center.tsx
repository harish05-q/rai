"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { StatusNotice } from "@/components/status-notice";
import { approveRequest, getApprovals, rejectRequest, type ApprovalRequest } from "@/lib/api-client";
import { formatDate, formatInr, formatLabel } from "@/lib/format";

const TABS = ["pending", "approved", "rejected", "expired"] as const;

export function ApprovalCenter() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("pending");
  const [items, setItems] = useState<ApprovalRequest[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    getApprovals({ status: tab, limit: 50 })
      .then((payload) => {
        setItems(payload.items);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [tab]);

  const empty = useMemo(() => items.length === 0, [items.length]);

  function resolve(id: string, action: "approve" | "reject") {
    setBusy(id);
    const request = action === "approve" ? approveRequest(id, "Approved from Approval Center") : rejectRequest(id, "Rejected from Approval Center");
    request
      .then(() => getApprovals({ status: tab, limit: 50 }))
      .then((payload) => setItems(payload.items))
      .finally(() => setBusy(null));
  }

  return (
    <div className="space-y-6">
      <section className="border-b border-line pb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Approvals</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Approval Center</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
          High-value and uncertain recoveries pause here. Execution starts only after an operator approves.
        </p>
      </section>

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setTab(item)}
            className={[
              "rounded-md px-3 py-2 text-sm font-semibold",
              tab === item ? "bg-ink text-white" : "border border-line bg-white text-ink"
            ].join(" ")}
          >
            {formatLabel(item)}
          </button>
        ))}
      </div>

      {state === "loading" ? <StatusNotice title="Loading approvals" description="Fetching approval requests." /> : null}
      {state === "error" ? <StatusNotice title="Unable to load approvals" description="The approvals API is unavailable." /> : null}
      {state === "ready" && empty ? (
        <StatusNotice title={`No ${tab} approvals`} description="Requests appear here when policy requires a human gate." />
      ) : null}

      {state === "ready" && !empty ? (
        <div className="overflow-x-auto rounded-lg border border-line bg-white shadow-soft">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-line bg-field text-ink/60">
              <tr>
                <th className="px-4 py-3 font-medium">Case</th>
                <th className="px-4 py-3 font-medium">Customer</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Policy reason</th>
                <th className="px-4 py-3 font-medium">Requested</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-line last:border-0">
                  <td className="px-4 py-3">
                    <Link className="font-medium text-accent" href={`/recovery/${item.recovery_case_id}`}>
                      {item.external_payment_id ?? item.recovery_case_id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{item.customer_name ?? "—"}</td>
                  <td className="px-4 py-3">{formatInr(item.amount)}</td>
                  <td className="px-4 py-3">{formatLabel(item.requested_action)}</td>
                  <td className="max-w-xs px-4 py-3 text-ink/70">{item.reason}</td>
                  <td className="px-4 py-3">{formatDate(item.requested_at)}</td>
                  <td className="px-4 py-3">
                    {item.status === "pending" ? (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={busy === item.id}
                          onClick={() => resolve(item.id, "approve")}
                          className="rounded-md bg-ink px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          disabled={busy === item.id}
                          onClick={() => resolve(item.id, "reject")}
                          className="rounded-md border border-line px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    ) : (
                      <span className="text-ink/55">{formatLabel(item.status)}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
