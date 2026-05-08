"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { billingApi } from "@/lib/api";

function useProfile() {
  const supabase = createClient();
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      return user;
    },
    staleTime: 60_000,
  });
}

const TIER_LABELS: Record<string, string> = {
  starter: "Starter",
  pro: "Pro",
  enterprise: "Enterprise",
};

export function SettingsPage() {
  const { data: user } = useProfile();
  const [portalLoading, setPortalLoading] = useState(false);
  const [upgradeLoading, setUpgradeLoading] = useState(false);

  async function handleBillingPortal() {
    setPortalLoading(true);
    try {
      const { portal_url } = await billingApi.portal();
      window.open(portal_url, "_blank");
    } catch {
      alert("Kan factuurportaal niet openen.");
    } finally {
      setPortalLoading(false);
    }
  }

  async function handleUpgrade(tier: "pro" | "enterprise") {
    setUpgradeLoading(true);
    try {
      const { checkout_url } = await billingApi.checkout({
        plan_tier: tier,
        redirect_url: window.location.origin + "/settings",
      });
      window.location.href = checkout_url;
    } catch {
      alert("Kan checkout niet starten.");
    } finally {
      setUpgradeLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Account */}
      <section className="rounded-lg border border-border bg-card p-5 space-y-3">
        <h2 className="text-sm font-medium">Account</h2>
        <dl className="space-y-1.5">
          <Row label="E-mail" value={user?.email ?? "—"} />
          <Row label="Gebruiker-ID" value={user?.id ? user.id.slice(0, 8) + "…" : "—"} />
        </dl>
      </section>

      {/* Subscription */}
      <section className="rounded-lg border border-border bg-card p-5 space-y-4">
        <h2 className="text-sm font-medium">Abonnement</h2>

        <div className="grid grid-cols-3 gap-3">
          {(["starter", "pro", "enterprise"] as const).map((tier) => (
            <div
              key={tier}
              className="rounded-lg border border-border p-3 space-y-1"
            >
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {TIER_LABELS[tier]}
              </p>
              <p className="text-sm text-muted-foreground">
                {tier === "starter" && "1 provincie · 5 leads/dag"}
                {tier === "pro" && "Heel NL · Onbeperkt · CSV export"}
                {tier === "enterprise" && "Custom scoring · API-toegang"}
              </p>
              {tier !== "starter" && (
                <button
                  onClick={() => handleUpgrade(tier)}
                  disabled={upgradeLoading}
                  className="mt-2 rounded-md bg-primary px-3 h-7 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  Upgraden
                </button>
              )}
            </div>
          ))}
        </div>

        <button
          onClick={handleBillingPortal}
          disabled={portalLoading}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          {portalLoading ? "Laden…" : "Facturen en betaalgegevens"}
        </button>
      </section>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-4 text-sm">
      <span className="w-28 shrink-0 text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
