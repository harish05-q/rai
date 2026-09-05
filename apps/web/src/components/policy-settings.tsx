"use client";

import { useEffect, useState } from "react";

import { StatusNotice } from "@/components/status-notice";
import { getMerchantPolicy, updateMerchantPolicy, type MerchantPolicy } from "@/lib/api-client";
import { formatInr } from "@/lib/format";

export function PolicySettings() {
  const [policy, setPolicy] = useState<MerchantPolicy | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getMerchantPolicy()
      .then((payload) => {
        setPolicy(payload);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  function toggle(key: keyof MerchantPolicy, value: boolean) {
    if (!policy) {
      return;
    }
    const next = { ...policy, [key]: value };
    setPolicy(next);
    persist({ [key]: value });
  }

  function persist(body: Record<string, unknown>) {
    setSaving(true);
    setMessage(null);
    updateMerchantPolicy(body)
      .then((payload) => {
        setPolicy(payload);
        setMessage("Guardrails saved. The Policy Engine uses these values on the next execution.");
      })
      .catch((err: unknown) => {
        setMessage(err instanceof Error ? err.message : "Unable to save policy.");
      })
      .finally(() => setSaving(false));
  }

  return (
    <div className="space-y-6">
      <section className="border-b border-line pb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Settings</p>
        <h1 className="mt-2 text-3xl font-semibold text-ink">Execution guardrails</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
          These values are merchant policy for the deterministic Policy Engine. They cannot be overridden from an
          execute request or by the LLM.
        </p>
      </section>

      {state === "loading" ? <StatusNotice title="Loading policy" description="Fetching merchant guardrails." /> : null}
      {state === "error" ? <StatusNotice title="Unable to load settings" description="The policies API is unavailable." /> : null}

      {state === "ready" && policy ? (
        <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
          <dl className="grid gap-5 text-sm">
            <SettingRow
              label="Autonomous execution"
              description="When off, provider actions require approval."
              checked={policy.autonomous_execution}
              onChange={(value) => toggle("autonomous_execution", value)}
            />
            <div className="flex items-center justify-between border-t border-line pt-4">
              <div>
                <p className="font-medium text-ink">High-value threshold</p>
                <p className="text-ink/60">{formatInr(policy.high_value_threshold)} requires approval</p>
              </div>
            </div>
            <SettingRow
              label="Approval requirement for high-value cases"
              description="Policy Engine will not auto-execute above the high-value threshold."
              checked={policy.require_approval_for_high_value}
              onChange={(value) => toggle("require_approval_for_high_value", value)}
            />
            <div className="flex items-center justify-between border-t border-line pt-4">
              <div>
                <p className="font-medium text-ink">Maximum recovery attempts</p>
                <p className="text-ink/60">{policy.max_recovery_attempts} provider recoveries per case</p>
              </div>
            </div>
            <SettingRow
              label="Payment Link recovery enabled"
              description="Allows creating Razorpay Payment Links for reminders and one-time recovery."
              checked={policy.payment_link_creation_allowed}
              onChange={(value) => toggle("payment_link_creation_allowed", value)}
            />
            <SettingRow
              label="Notifications enabled"
              description="Allows Payment Link email notification where the provider supports it."
              checked={policy.notifications_allowed}
              onChange={(value) => toggle("notifications_allowed", value)}
            />
            <SettingRow
              label="Subscription recovery enabled"
              description="Allows provider-managed/deferred subscription recovery. No invented retry charge."
              checked={policy.subscription_recovery_allowed}
              onChange={(value) => toggle("subscription_recovery_allowed", value)}
            />
          </dl>
          <p className="mt-6 text-xs text-ink/50">
            Policy version {policy.policy_version}
            {saving ? " · saving" : ""}
          </p>
          {message ? <p className="mt-2 text-sm text-ink/70">{message}</p> : null}
        </section>
      ) : null}
    </div>
  );
}

function SettingRow({
  label,
  description,
  checked,
  onChange
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-t border-line pt-4 first:border-t-0 first:pt-0">
      <div>
        <p className="font-medium text-ink">{label}</p>
        <p className="mt-1 max-w-xl text-ink/60">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={[
          "relative h-6 w-11 rounded-full",
          checked ? "bg-ink" : "bg-line"
        ].join(" ")}
      >
        <span className={["absolute top-0.5 h-5 w-5 rounded-full bg-white transition", checked ? "left-5" : "left-0.5"].join(" ")} />
      </button>
    </div>
  );
}
