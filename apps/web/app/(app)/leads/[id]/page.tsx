import { Suspense } from "react";
import { LeadDetailPage } from "./lead-detail-page";

export default function Page({ params }: { params: { id: string } }) {
  return (
    <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-muted-foreground">Laden…</div>}>
      <LeadDetailPage id={params.id} />
    </Suspense>
  );
}
