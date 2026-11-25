import { BarChart3, Bot, CreditCard, Gauge, RotateCcw, ScrollText, Settings, ShieldCheck } from "lucide-react";
import Link from "next/link";

export const navigation = [
  { href: "/dashboard", label: "Overview", description: "Revenue and recent activity", icon: Gauge, group: "Operations" },
  { href: "/payments", label: "Payments", description: "Payment events and failures", icon: CreditCard, group: "Operations" },
  { href: "/recovery", label: "Recovery", description: "Recovery queue and cases", icon: RotateCcw, group: "Operations" },
  { href: "/approvals", label: "Approvals", description: "Review policy decisions", icon: ShieldCheck, group: "Operations" },
  { href: "/agent", label: "Agent", description: "Analyze cases and recommendations", icon: Bot, group: "Oversight" },
  { href: "/analytics", label: "Analytics", description: "Outcomes and evaluation", icon: BarChart3, group: "Oversight" },
  { href: "/audit", label: "Audit", description: "Execution event history", icon: ScrollText, group: "Oversight" },
  { href: "/settings", label: "Settings", description: "Merchant policy and guardrails", icon: Settings, group: "Oversight" }
];

export function Sidebar({ pathname, mobileOpen, onNavigate }: {
  pathname: string;
  mobileOpen: boolean;
  onNavigate: () => void;
}) {
  return (
    <aside className="workspace-sidebar" data-mobile-open={mobileOpen}>
      <Link href="/dashboard" className="workspace-brand" onClick={onNavigate}>
        <span aria-hidden>r<b>.</b></span>
        <div><strong>R.AI</strong><small>Revenue recovery</small></div>
      </Link>
      <nav id="workspace-nav" aria-label="Workspace">
        {["Operations", "Oversight"].map((group) => (
          <div key={group} className="workspace-group">
            <p>{group}</p>
            {navigation.filter((item) => item.group === group).map(({ href, label, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(href + "/");
              return (
                <Link key={href} href={href} aria-current={active ? "page" : undefined} onClick={onNavigate}>
                  <Icon size={18} aria-hidden /> {label}
                </Link>
              );
            })}
          </div>
        ))}
        <Link href="/" className="workspace-home" onClick={onNavigate}>Back to landing page</Link>
      </nav>
    </aside>
  );
}
