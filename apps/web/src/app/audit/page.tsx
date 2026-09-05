import { Suspense } from "react";

import { AuditTimeline } from "@/components/audit-timeline";
import { StatusNotice } from "@/components/status-notice";

export default function AuditPage() {
  return (
    <Suspense fallback={<StatusNotice title="Loading audit" description="Preparing the execution timeline." />}>
      <AuditTimeline />
    </Suspense>
  );
}
