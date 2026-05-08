import { SettingsPage } from "./settings-page";

export const metadata = { title: "Instellingen — Sloopradar" };

export default function Page() {
  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-base font-semibold">Instellingen</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Beheer uw organisatie en abonnement.
        </p>
      </div>
      <SettingsPage />
    </div>
  );
}
