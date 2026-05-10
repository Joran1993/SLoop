import Link from "next/link";
import { Building2, ChevronRight, Clock, Eye, AlertTriangle, CheckCircle2, ArrowRight, Zap } from "lucide-react";
import { createClient } from "@/lib/supabase/server";

async function getPublicStats() {
  try {
    const supabase = await createClient();
    const { data } = await supabase
      .from("pipeline_projects_api")
      .select("source_type")
      .in("source_type", ["eindhoven_vergunning", "pijplijn", "koop_sloopmelding"]);

    if (!data) return { vroeg: 72, pijplijn: 200, totaal: 1750 };
    const vroeg = data.filter((r) => r.source_type === "eindhoven_vergunning").length;
    const pijplijn = data.filter((r) => r.source_type === "pijplijn").length;
    return { vroeg, pijplijn, totaal: data.length };
  } catch {
    return { vroeg: 72, pijplijn: 200, totaal: 1750 };
  }
}

const EXAMPLE_LEADS = [
  {
    adres: "Stuwstraat 2 t/m 72",
    gemeente: "'s-Gravenhage",
    type: "Aanvraag omgevingsvergunning — sloop woonblok",
    timing: "3 weken geleden",
    tier: "vroeg" as const,
    oppervlakte: "~4.200 m²",
  },
  {
    adres: "Zeesluisweg 44 t/m 76",
    gemeente: "'s-Gravenhage",
    type: "Aanvraag omgevingsvergunning — sloop woningen",
    timing: "2 maanden geleden",
    tier: "pijplijn" as const,
    oppervlakte: "~2.100 m²",
  },
  {
    adres: "Buitenruststraat 1-43",
    gemeente: "Middelburg",
    type: "Aanvraag omgevingsvergunning — herstructurering 41 appartementen",
    timing: "4 maanden geleden",
    tier: "pijplijn" as const,
    oppervlakte: "~3.500 m²",
  },
  {
    adres: "Lichtenbergweg 29 t/m 111",
    gemeente: "Maastricht",
    type: "Sloopvergunning verleend",
    timing: "5 weken geleden",
    tier: "laat" as const,
    oppervlakte: "~6.800 m²",
  },
];

const TIER_CONFIG = {
  vroeg: {
    label: "Vroeg",
    color: "bg-emerald-100 text-emerald-700",
    icon: Clock,
    iconColor: "text-emerald-500",
  },
  pijplijn: {
    label: "Pijplijn",
    color: "bg-blue-100 text-blue-700",
    icon: Eye,
    iconColor: "text-blue-500",
  },
  laat: {
    label: "Laat",
    color: "bg-amber-100 text-amber-700",
    icon: AlertTriangle,
    iconColor: "text-amber-500",
  },
};

export default async function LandingPage() {
  const stats = await getPublicStats();

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Nav */}
      <header className="border-b border-border bg-background/95 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3.5">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" strokeWidth={2} />
            <span className="font-semibold text-sm tracking-tight">Sloopradar</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="#pricing"
              className="hidden sm:block text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Prijzen
            </Link>
            <Link
              href="/login"
              className="flex items-center gap-1 text-sm font-medium text-foreground hover:opacity-80 transition-opacity"
            >
              Inloggen
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto max-w-5xl px-4 pt-16 pb-12 text-center">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground mb-6">
            <Zap className="h-3 w-3 text-amber-500" />
            Dagelijks bijgewerkt via officiële Gemeenteblad-data
          </div>
          <h1 className="text-4xl font-bold tracking-tight leading-[1.15] sm:text-5xl">
            Sloopprojecten vinden
            <br />
            <span className="text-primary">vóór de offertefase begint</span>
          </h1>
          <p className="mx-auto mt-5 max-w-lg text-base text-muted-foreground leading-relaxed">
            Sloopradar scant dagelijks alle Nederlandse gemeentebladen. Zodra een sloopvergunning
            wordt aangevraagd, bent u op de hoogte — weken of maanden voordat de opdracht
            wordt gegund.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              14 dagen gratis proberen
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="#leads"
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-5 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Voorbeeldleads bekijken
            </Link>
          </div>

          {/* Live stats */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-sm">
            <div className="flex items-center gap-1.5">
              <Clock className="h-4 w-4 text-emerald-500" />
              <span className="font-bold text-foreground">{stats.vroeg}</span>
              <span className="text-muted-foreground">vroege signalen nu</span>
            </div>
            <div className="h-4 w-px bg-border hidden sm:block" />
            <div className="flex items-center gap-1.5">
              <Eye className="h-4 w-4 text-blue-500" />
              <span className="font-bold text-foreground">{stats.pijplijn}</span>
              <span className="text-muted-foreground">aanvragen in behandeling</span>
            </div>
            <div className="h-4 w-px bg-border hidden sm:block" />
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-foreground">{stats.totaal.toLocaleString("nl-NL")}</span>
              <span className="text-muted-foreground">projecten in heel Nederland</span>
            </div>
          </div>
        </section>

        {/* Example leads */}
        <section id="leads" className="border-y border-border bg-muted/30 py-14">
          <div className="mx-auto max-w-5xl px-4">
            <div className="mb-8 text-center">
              <h2 className="text-xl font-bold tracking-tight">Zo ziet een lead eruit</h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Echte aanvragen uit het Gemeenteblad — gesorteerd van vroeg naar laat
              </p>
            </div>
            <div className="space-y-2.5">
              {EXAMPLE_LEADS.map((lead, i) => {
                const cfg = TIER_CONFIG[lead.tier];
                const Icon = cfg.icon;
                return (
                  <div
                    key={i}
                    className="flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-3 text-sm"
                  >
                    <Icon className={`h-4 w-4 shrink-0 ${cfg.iconColor}`} />
                    <div className="flex-1 min-w-0">
                      <span className="font-medium">{lead.adres}</span>
                      <span className="text-muted-foreground">, {lead.gemeente}</span>
                    </div>
                    <span className="hidden sm:block text-xs text-muted-foreground truncate max-w-[200px]">
                      {lead.type}
                    </span>
                    <span className="shrink-0 text-xs text-muted-foreground">{lead.oppervlakte}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">{lead.timing}</span>
                    <span className={`shrink-0 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${cfg.color}`}>
                      {cfg.label}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="mt-6 text-center">
              <Link
                href="/login"
                className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline font-medium"
              >
                Zie alle {stats.totaal.toLocaleString("nl-NL")} projecten na aanmelding
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </section>

        {/* Three tiers explained */}
        <section className="mx-auto max-w-5xl px-4 py-16">
          <div className="mb-10 text-center">
            <h2 className="text-2xl font-bold tracking-tight">Drie signaallagen, één voorsprong</h2>
            <p className="mt-2 text-sm text-muted-foreground max-w-lg mx-auto">
              Sloopradar sorteert elke lead op urgentie. Zo weet u direct welke projecten
              nu de meeste kans geven en welke u kunt plannen.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-3">
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 dark:bg-emerald-950/20 dark:border-emerald-900">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="h-4 w-4 text-emerald-600" />
                <span className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">Vroeg signaal</span>
              </div>
              <p className="text-xs text-emerald-700/90 dark:text-emerald-500 leading-relaxed">
                Sloopvergunning aangevraagd, minder dan 5 weken geleden. De eigenaar heeft
                nog geen sloopbedrijf gekozen. Wie nu belt, is de eerste.
              </p>
              <p className="mt-3 text-xs font-semibold text-emerald-800 dark:text-emerald-400">
                Horizon: 3-12 maanden tot sloop
              </p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 dark:bg-blue-950/20 dark:border-blue-900">
              <div className="flex items-center gap-2 mb-3">
                <Eye className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-semibold text-blue-800 dark:text-blue-300">Pijplijn</span>
              </div>
              <p className="text-xs text-blue-700/90 dark:text-blue-500 leading-relaxed">
                Vergunning aangevraagd, 5 weken tot 6 maanden geleden, nog niet verleend.
                De eigenaar selecteert binnenkort. Goed moment voor een eerste gesprek.
              </p>
              <p className="mt-3 text-xs font-semibold text-blue-800 dark:text-blue-400">
                Horizon: 2-9 maanden tot sloop
              </p>
            </div>
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 dark:bg-amber-950/20 dark:border-amber-900">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <span className="text-sm font-semibold text-amber-800 dark:text-amber-300">Laat signaal</span>
              </div>
              <p className="text-xs text-amber-700/90 dark:text-amber-500 leading-relaxed">
                Vergunning verleend of sloopmelding ingediend. Eigenaar vraagt waarschijnlijk
                al offertes op. Snel reageren loont nog steeds.
              </p>
              <p className="mt-3 text-xs font-semibold text-amber-800 dark:text-amber-400">
                Horizon: 0-6 maanden tot sloop
              </p>
            </div>
          </div>
        </section>

        {/* ROI section */}
        <section className="border-y border-border bg-muted/30">
          <div className="mx-auto max-w-3xl px-4 py-16 text-center">
            <h2 className="text-2xl font-bold tracking-tight">Eén gewonnen opdracht betaalt alles terug</h2>
            <p className="mt-4 text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
              Een gemiddeld sloopproject kost €75.000 tot €500.000. Bij een Pro-abonnement
              van €149/maand heeft u uw investering van een heel jaar terugverdiend met
              minder dan één extra opdracht.
            </p>
            <div className="mt-8 grid grid-cols-3 gap-4 text-center max-w-lg mx-auto">
              <div>
                <p className="text-2xl font-bold">€1.788</p>
                <p className="text-xs text-muted-foreground mt-0.5">Per jaar Pro</p>
              </div>
              <div className="flex items-center justify-center">
                <span className="text-2xl text-muted-foreground">vs</span>
              </div>
              <div>
                <p className="text-2xl font-bold text-primary">€75.000+</p>
                <p className="text-xs text-muted-foreground mt-0.5">Gemiddeld sloopproject</p>
              </div>
            </div>
            <Link
              href="/login"
              className="mt-8 inline-flex items-center gap-2 rounded-md bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Start uw gratis proefperiode
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="mx-auto max-w-5xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold tracking-tight">Eenvoudige, transparante prijzen</h2>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            14 dagen gratis proberen. Geen creditcard vereist.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 max-w-2xl mx-auto">
            {/* Pro */}
            <div className="relative rounded-xl border-2 border-primary bg-primary p-6 space-y-5 text-primary-foreground shadow-lg">
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-amber-400 px-3 py-0.5 text-xs font-semibold text-amber-900">
                Meest gekozen
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-primary-foreground/60">Pro</p>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="text-3xl font-bold">€149</span>
                  <span className="text-sm text-primary-foreground/60">/ maand excl. BTW</span>
                </div>
                <p className="mt-1.5 text-sm text-primary-foreground/70">
                  Heel Nederland, onbeperkt, real-time alerts
                </p>
              </div>
              <ul className="space-y-2">
                {[
                  "Alle signalen in heel Nederland",
                  "Onbeperkt leads bekijken en exporteren",
                  "Real-time e-mailmeldingen",
                  "Vroeg + Pijplijn + Laat tier",
                  "Filter op regio, type, score",
                  "14 dagen gratis proberen",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-primary-foreground/80">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-primary-foreground/60" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/login"
                className="block text-center rounded-md bg-background text-foreground px-4 py-2.5 text-sm font-medium hover:bg-background/90 transition-colors"
              >
                Gratis proberen — geen creditcard
              </Link>
            </div>

            {/* Enterprise */}
            <div className="rounded-xl border border-border bg-card p-6 space-y-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Enterprise</p>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="text-3xl font-bold">Op maat</span>
                </div>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  Voor bureaus, projectontwikkelaars en teams
                </p>
              </div>
              <ul className="space-y-2">
                {[
                  "Alles van Pro",
                  "Meerdere gebruikers",
                  "API-toegang voor integratie",
                  "Maatwerk scoring en filters",
                  "Accountmanager",
                  "SLA en prioriteit support",
                ].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href="mailto:hallo@sloopradar.nl"
                className="block text-center rounded-md border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:border-foreground transition-colors"
              >
                Contact opnemen
              </a>
            </div>
          </div>

          {/* Trust signals */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              Gebaseerd op officiële overheidsdata
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              Dagelijks bijgewerkt
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              Opzegbaar per maand
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              Betalen via iDEAL of creditcard
            </span>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-5xl px-4 py-6 flex flex-wrap items-center justify-between gap-4 text-xs text-muted-foreground">
          <span>© 2026 Sloopradar</span>
          <div className="flex items-center gap-4">
            <a href="mailto:hallo@sloopradar.nl" className="hover:text-foreground transition-colors">
              hallo@sloopradar.nl
            </a>
            <span>Gemaakt in Nederland</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
