"use client";

import { Menu, Search } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Sidebar, navigation } from "@/components/sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchDialog = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [mobileRoute, setMobileRoute] = useState<string | null>(null);
  const mobileOpen = mobileRoute === pathname;
  const current = navigation.find(({ href }) => pathname === href || pathname.startsWith(href + "/"));
  const matches = navigation.filter(({ label, description }) =>
    (label + " " + description).toLowerCase().includes(query.trim().toLowerCase())
  );

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k" && searchDialog.current) {
        event.preventDefault();
        setQuery("");
        if (!searchDialog.current.open) searchDialog.current.showModal();
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);

  if (pathname === "/") return <>{children}</>;

  function openSearch() {
    setQuery("");
    searchDialog.current?.showModal();
  }

  return (
    <div className="workspace">
      <a className="workspace-skip" href="#workspace-content">Skip to content</a>
      <Sidebar pathname={pathname} mobileOpen={mobileOpen} onNavigate={() => setMobileRoute(null)} />
      <div className="workspace-body">
        <header className="workspace-top">
          <button type="button" className="workspace-menu workspace-tool" aria-expanded={mobileOpen}
            aria-controls="workspace-nav" onClick={() => setMobileRoute(mobileOpen ? null : pathname)}>
            <Menu size={18} aria-hidden /> <span>Menu</span>
          </button>
          <span className="workspace-location">{current?.label ?? "Workspace"}{pathname.startsWith("/recovery/") ? " / Case detail" : ""}</span>
          <button type="button" className="workspace-tool" onClick={openSearch}>
            <Search size={16} aria-hidden /> <span>Find a page</span> <kbd>Ctrl / ⌘ K</kbd>
          </button>
        </header>
        <main id="workspace-content" tabIndex={-1} className="workspace-main">
          <div key={pathname} className="workspace-view">{children}</div>
        </main>
      </div>
      <dialog ref={searchDialog} className="workspace-dialog" aria-labelledby="workspace-search-title">
        <div className="flex items-center justify-between gap-4">
          <h2 id="workspace-search-title" className="font-semibold">Find a workspace page</h2>
          <form method="dialog"><button className="workspace-tool">Close</button></form>
        </div>
        <input autoFocus aria-label="Search pages" placeholder="Search payments, approvals, settings…"
          value={query} onChange={(event) => setQuery(event.target.value)} />
        <SidebarLinks matches={matches} close={() => searchDialog.current?.close()} />
      </dialog>
    </div>
  );
}

function SidebarLinks({ matches, close }: { matches: typeof navigation; close: () => void }) {
  const router = useRouter();

  return matches.length ? (
    <ul className="workspace-results">
      {matches.map(({ href, label, description, icon: Icon }) => (
        <li key={href}>
          <button type="button" onClick={() => { close(); router.push(href); }}>
            <Icon size={18} aria-hidden />
            <span>{label}<small>{description}</small></span>
          </button>
        </li>
      ))}
    </ul>
  ) : <p role="status" className="py-5 text-sm">No matching pages.</p>;
}
