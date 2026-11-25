export function StatusNotice({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <section role="status" className="workspace-panel border-l-4 border-l-accent p-6">
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-ink/65">{description}</p>
    </section>
  );
}
