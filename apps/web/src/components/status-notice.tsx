export function StatusNotice({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="rounded-lg border border-line bg-white p-8 shadow-soft">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-ink/65">{description}</p>
    </section>
  );
}
