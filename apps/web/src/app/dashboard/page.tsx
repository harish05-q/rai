import { ActivityFeed } from "@/components/activity-feed";
import { HealthIndicator } from "@/components/health-indicator";
import { MetricGrid } from "@/components/metric-grid";
import { dashboardActivity, dashboardMetrics } from "@/lib/mock-dashboard";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 border-b border-line pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">Operations Dashboard</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Revenue recovery command center</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/70">
            Mock Sprint 1 telemetry for recovery readiness. These values are placeholders until backend
            product data is introduced in a future sprint.
          </p>
        </div>
        <HealthIndicator />
      </section>

      <MetricGrid metrics={dashboardMetrics} />

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <ActivityFeed items={dashboardActivity} />
        <div className="rounded-lg border border-line bg-white p-6 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-ink">Policy posture</h2>
              <p className="mt-2 text-sm leading-6 text-ink/65">
                Sprint 1 keeps recovery execution blocked. Future agent proposals must pass deterministic
                policy validation before any provider action can occur.
              </p>
            </div>
            <span className="rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-xs font-semibold text-warning">
              Mock-only
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
