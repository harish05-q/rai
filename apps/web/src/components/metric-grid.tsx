type Metric = {
  label: string;
  value: string;
  note: string;
};

export function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <article key={metric.label} className="rounded-lg border border-line bg-white p-5 shadow-soft">
          <p className="text-sm font-medium text-ink/60">{metric.label}</p>
          <p className="mt-3 text-3xl font-semibold text-ink">{metric.value}</p>
          <p className="mt-3 text-sm leading-6 text-ink/60">{metric.note}</p>
        </article>
      ))}
    </section>
  );
}
