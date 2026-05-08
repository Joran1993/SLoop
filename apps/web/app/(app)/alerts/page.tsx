import { Suspense } from "react";
import { AlertsPage } from "./alerts-page";

export const metadata = { title: "Meldingen — Sloopradar" };

export default function Page() {
  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-base font-semibold">Meldingen</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Ontvang automatisch nieuwe sloopkansen die aan uw criteria voldoen.
        </p>
      </div>
      <Suspense>
        <AlertsPage />
      </Suspense>
    </div>
  );
}
