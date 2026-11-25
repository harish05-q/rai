type Metric = {
  label: string;
  value: string;
  note: string;
};

export function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {metrics.map((metric) => (
        <article key={metric.label} className="workspace-panel p-5">
          <p className="text-sm font-medium text-ink/60">{metric.label}</p>
          <p key={metric.value} className="workspace-metric mt-3 break-words text-3xl font-semibold tabular-nums text-ink">{metric.value}</p>
          <p className="mt-3 text-sm leading-6 text-ink/60">{metric.note}</p>
        </article>
      ))}
    </section>
  );
}
