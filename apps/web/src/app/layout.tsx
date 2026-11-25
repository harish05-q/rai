import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import "./globals.css";
import "./workspace.css";

export const metadata: Metadata = {
  title: "R.AI",
  description: "Revenue Intelligence & Recovery"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
