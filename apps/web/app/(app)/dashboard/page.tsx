import { Suspense } from "react";
import { LeadsDashboard } from "./leads-dashboard";

export const metadata = { title: "Dashboard — Sloopradar" };

export default function DashboardPage() {
  return (
    <Suspense>
      <LeadsDashboard />
    </Suspense>
  );
}
