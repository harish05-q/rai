import { CheckCircle2, CircleDot, RotateCcw } from "lucide-react";

type ActivityItem = {
  title: string;
  description: string;
  time: string;
  kind: "analysis" | "strategy" | "recovered";
};

const iconByKind = {
  analysis: CircleDot,
  strategy: RotateCcw,
  recovered: CheckCircle2
};

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <section className="rounded-lg border border-line bg-white p-6 shadow-soft">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-ink">AI Recovery Activity</h2>
          <p className="mt-1 text-sm text-ink/60">Mock events for dashboard layout validation.</p>
        </div>
      </div>
      <div className="mt-5 space-y-4">
        {items.map((item) => {
          const Icon = iconByKind[item.kind];
          return (
            <article key={`${item.title}-${item.time}`} className="flex gap-4 border-t border-line pt-4 first:border-t-0 first:pt-0">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line bg-field text-accent">
                <Icon aria-hidden="true" size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                  <time className="text-xs font-medium text-ink/50">{item.time}</time>
                </div>
                <p className="mt-1 text-sm leading-6 text-ink/65">{item.description}</p>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
