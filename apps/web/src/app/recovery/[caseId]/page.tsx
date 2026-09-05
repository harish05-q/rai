import { RecoveryCaseDetailView } from "@/components/recovery-case-detail";

export default async function RecoveryCasePage({
  params
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  return <RecoveryCaseDetailView caseId={caseId} />;
}