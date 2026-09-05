"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { StatusNotice } from "@/components/status-notice";
import { getAudit, type AuditLogItem } from "@/lib/api-client";
import { formatDate, formatLabel } from "@/lib/format";

export function AuditTimeline() {
  const search = useSearchParams();
  const caseId = search.get("case") ?? undefined;
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    getAudit({ case_id: caseId, limit: 100 })
      .then((payload) => {
        setItems(payload.items);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [caseId]);

  const subtitle = useMemo(
    () =>
      caseId
        ? "Timeline for the selected recovery case."
        : "Append-only execution events across recommendation, policy, approval, and provider result.",
    [caseId]
  );

  return (
    <div className="space-y-6">
      <section className="border-b border-line pb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Audit</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Execution audit trail</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">{subtitle}</p>
      </section>

      {state === "loading" ? <StatusNotice title="Loading audit events" description="Fetching append-only records." /> : null}
      {state === "error" ? <StatusNotice title="Unable to load audit" description="The audit API is unavailable." /> : null}
      {state === "ready" && items.length === 0 ? (
        <StatusNotice title="No audit events yet" description="Execute a recovery action to record recommendation, policy, and provider events." />
      ) : null}

      {state === "ready" && items.length > 0 ? (
        <ol className="space-y-0">
          {items.map((item, index) => (
            <li key={item.id} className="relative grid grid-cols-[16px_1fr] gap-4 pb-8 last:pb-0">
              <div className="flex flex-col items-center">
                <span className="mt-1 h-3 w-3 rounded-full bg-ink" />
                {index < items.length - 1 ? <span className="w-px flex-1 bg-line" /> : null}
              </div>
              <article className="rounded-lg border border-line bg-white p-5 shadow-soft">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-sm font-semibold text-ink">
                    {formatLabel(item.source)} · {formatLabel(item.status)}
                  </h2>
                  <time className="text-xs text-ink/50">{formatDate(item.created_at)}</time>
                </div>
                <p className="mt-2 text-sm leading-6 text-ink/70">{item.reason}</p>
                <dl className="mt-3 grid gap-2 text-xs text-ink/55 sm:grid-cols-3">
                  <div>
                    <dt>Actor</dt>
                    <dd className="font-medium text-ink/80">{item.actor}</dd>
                  </div>
                  <div>
                    <dt>Action</dt>
                    <dd className="font-medium text-ink/80">{formatLabel(item.requested_action)}</dd>
                  </div>
                  <div>
                    <dt>Provider</dt>
                    <dd className="font-medium text-ink/80">{item.provider ?? "—"}</dd>
                  </div>
                </dl>
              </article>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}
