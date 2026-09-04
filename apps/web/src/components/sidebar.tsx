import {
  Activity,
  BarChart3,
  Bot,
  CreditCard,
  Gauge,
  RotateCcw,
  ScrollText,
  Settings
} from "lucide-react";
import Link from "next/link";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/payments", label: "Payments", icon: CreditCard },
  { href: "/recovery", label: "Recovery", icon: RotateCcw },
  { href: "/agent", label: "Agent", icon: Bot },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/audit", label: "Audit", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function Sidebar({ pathname }: { pathname: string }) {
  return (
    <aside className="border-line bg-white/95 md:fixed md:inset-y-0 md:left-0 md:w-64 md:border-r">
      <div className="flex h-full flex-col gap-6 px-4 py-5">
        <Link href="/dashboard" className="flex items-center gap-3 rounded-lg px-2 py-1">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-ink text-white">
            <Activity aria-hidden="true" size={20} />
          </div>
          <div>
            <div className="text-xl font-semibold text-ink">R.AI</div>
            <div className="text-xs font-medium text-ink/60">Revenue Intelligence & Recovery</div>
          </div>
        </Link>

        <nav className="grid gap-1">
          {navigation.map((item) => {
            const active = pathname === item.href || (item.href === "/dashboard" && pathname === "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition",
                  active ? "bg-field text-ink" : "text-ink/65 hover:bg-field hover:text-ink"
                ].join(" ")}
              >
                <Icon aria-hidden="true" size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-lg border border-line bg-field p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink/50">Sprint 1</p>
          <p className="mt-2 text-sm leading-6 text-ink/70">Foundation build with mock operational data.</p>
        </div>
      </div>
    </aside>
  );
}
