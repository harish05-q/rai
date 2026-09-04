"use client";

import { Wifi, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { getHealth } from "@/lib/api-client";

type HealthState = "checking" | "online" | "offline";

export function HealthIndicator() {
  const [state, setState] = useState<HealthState>("checking");

  useEffect(() => {
    let active = true;

    getHealth()
      .then((health) => {
        if (active) {
          setState(health.status === "ok" ? "online" : "offline");
        }
      })
      .catch(() => {
        if (active) {
          setState("offline");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const online = state === "online";
  const Icon = online ? Wifi : WifiOff;
  const label = state === "checking" ? "Checking API" : online ? "API connected" : "API unavailable";

  return (
    <div className="inline-flex w-fit items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-semibold text-ink shadow-sm">
      <Icon aria-hidden="true" className={online ? "text-success" : "text-warning"} size={16} />
      <span>{label}</span>
    </div>
  );
}
