export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section className="rounded-lg border border-line bg-white p-8 shadow-soft">
      <p className="text-sm font-semibold uppercase tracking-[0.12em] text-accent">R.AI workspace</p>
      <h1 className="mt-3 text-3xl font-semibold text-ink">{title}</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/65">{description}</p>
    </section>
  );
}
