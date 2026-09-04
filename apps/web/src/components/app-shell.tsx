"use client";

import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-field">
      <Sidebar pathname={pathname} />
      <main className="min-h-screen px-4 py-5 md:pl-72 md:pr-8 lg:px-10 lg:pl-80">
        <div className="mx-auto max-w-7xl">{children}</div>
      </main>
    </div>
  );
}
