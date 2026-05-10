import Link from "next/link";
import { Building2, Clock, Eye, AlertTriangle, CheckCircle2, ArrowRight, ChevronRight } from "lucide-react";
import { createClient } from "@/lib/supabase/server";

async function getPublicStats() {
  try {
    const supabase = await createClient();
    const { data, error } = await supabase.rpc("get_pipeline_stats");
    if (error || !data) return { vroeg: 72, pijplijn: 200, totaal: 1750 };
    return {
      vroeg:    Number(data.vroeg    ?? 72),
      pijplijn: Number(data.pijplijn ?? 200),
      totaal:   Number(data.totaal   ?? 1750),
    };
  } catch {
    return { vroeg: 72, pijplijn: 200, totaal: 1750 };
  }
}

const EXAMPLE_LEADS = [
  { adres: "Stuwstraat 2 t/m 72",         gemeente: "'s-Gravenhage", tier: "vroeg"    as const, oppervlakte: "4.200 m²", timing: "3 weken geleden",   eigenaar: "Staedion" },
  { adres: "Zeesluisweg 44 t/m 76",        gemeente: "'s-Gravenhage", tier: "pijplijn" as const, oppervlakte: "2.100 m²", timing: "2 mnd geleden",     eigenaar: "Vestia" },
  { adres: "Buitenruststraat 1-43",        gemeente: "Middelburg",    tier: "pijplijn" as const, oppervlakte: "3.500 m²", timing: "4 mnd geleden",     eigenaar: "Onbekend" },
  { adres: "Lichtenbergweg 29 t/m 111",   gemeente: "Maastricht",    tier: "laat"     as const, oppervlakte: "6.800 m²", timing: "5 weken geleden",   eigenaar: "Woonpunt" },
];

export default async function LandingPage() {
  const stats = await getPublicStats();

  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: "-apple-system, BlinkMacSystemFont, var(--font-inter), 'Segoe UI', sans-serif" }}>

      {/* ─── NAV ─────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-black/[0.06] bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex h-[52px] max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <Building2 className="h-[18px] w-[18px] text-amber-500" strokeWidth={2} />
            <span className="text-[15px] font-semibold tracking-tight">Sloopradar</span>
          </div>
          <div className="flex items-center gap-7">
            <Link href="#hoe" className="hidden sm:block text-[13px] text-black/50 hover:text-black transition-colors">Hoe het werkt</Link>
            <Link href="#pricing" className="hidden sm:block text-[13px] text-black/50 hover:text-black transition-colors">Prijzen</Link>
            <Link href="/login" className="hidden sm:block text-[13px] text-black/50 hover:text-black transition-colors">Inloggen</Link>
            <Link href="/login" className="rounded-full bg-black px-4 py-1.5 text-[13px] font-medium text-white hover:bg-black/80 transition-colors">
              Gratis proberen
            </Link>
          </div>
        </div>
      </header>

      {/* ─── HERO ────────────────────────────────────────────────────── */}
      <section className="px-6 pt-24 pb-20 text-center">
        <div className="mx-auto max-w-4xl">

          {/* Live badge */}
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-black/[0.03] px-3.5 py-1.5 text-[12px] font-medium text-black/50">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {stats.vroeg} nieuwe sloopkansen deze week · live data
          </div>

          {/* Headline */}
          <h1 className="text-[clamp(40px,7vw,72px)] font-bold leading-[1.04] tracking-[-0.03em] text-black">
            De aanvraag staat online.<br />
            Uw concurrent weet het<br className="hidden sm:block" /> nog niet.
          </h1>

          {/* Sub */}
          <p className="mx-auto mt-7 max-w-[480px] text-[18px] leading-[1.6] text-black/50">
            Sloopradar monitort dagelijks alle Nederlandse gemeentebladen en levert nieuwe sloopkansen als lead — weken vóór de offertefase.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 rounded-full bg-black px-7 py-3.5 text-[15px] font-semibold text-white hover:bg-black/80 transition-colors"
            >
              14 dagen gratis proberen
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="#preview"
              className="inline-flex items-center gap-1.5 rounded-full border border-black/[0.1] px-6 py-3.5 text-[15px] font-medium text-black/60 hover:text-black hover:border-black/20 transition-colors"
            >
              Voorbeeldleads bekijken
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

        </div>
      </section>

      {/* ─── STATS ───────────────────────────────────────────────────── */}
      <section className="border-y border-black/[0.06] bg-black/[0.02]">
        <div className="mx-auto max-w-3xl px-6 py-16">
          <div className="grid grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-[52px] font-bold leading-none tabular-nums tracking-tight">
                {stats.totaal.toLocaleString("nl-NL")}
              </div>
              <div className="mt-2.5 text-[13px] text-black/45">actieve sloopkansen</div>
            </div>
            <div>
              <div className="text-[52px] font-bold leading-none tabular-nums tracking-tight text-emerald-600">
                {stats.vroeg}
              </div>
              <div className="mt-2.5 text-[13px] text-black/45">vroeg — aanvraagfase</div>
            </div>
            <div>
              <div className="text-[52px] font-bold leading-none tabular-nums tracking-tight text-blue-600">
                {stats.pijplijn}
              </div>
              <div className="mt-2.5 text-[13px] text-black/45">pijplijn — vergunning verleend</div>
            </div>
          </div>
          <p className="mt-8 text-center text-[11px] font-medium uppercase tracking-widest text-black/25">
            Dagelijks bijgewerkt via officiële overheidsregistraties
          </p>
        </div>
      </section>

      {/* ─── PRODUCT PREVIEW ─────────────────────────────────────────── */}
      <section id="preview" className="px-6 py-28">
        <div className="mx-auto max-w-5xl">
          <div className="mb-14 text-center">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-black/30">Het dashboard</p>
            <h2 className="text-[40px] font-bold tracking-[-0.025em]">Uw leads, direct inzichtelijk</h2>
          </div>

          {/* Fake app window */}
          <div className="overflow-hidden rounded-2xl border border-black/[0.08] bg-white shadow-[0_24px_64px_-12px_rgba(0,0,0,0.14)]">

            {/* Browser chrome */}
            <div className="flex items-center gap-5 border-b border-black/[0.06] bg-black/[0.02] px-5 py-3.5">
              <div className="flex items-center gap-1.5 shrink-0">
                <span className="h-3 w-3 rounded-full bg-[#FF5F57]" />
                <span className="h-3 w-3 rounded-full bg-[#FEBC2E]" />
                <span className="h-3 w-3 rounded-full bg-[#28C840]" />
              </div>
              <div className="flex h-6 flex-1 max-w-xs items-center rounded-md border border-black/[0.07] bg-white px-3 text-[11px] text-black/35 font-mono">
                app.sloopradar.nl/dashboard
              </div>
            </div>

            {/* Topbar */}
            <div className="flex items-center justify-between border-b border-black/[0.06] px-5 py-3">
              <span className="text-[13px] font-semibold">
                {stats.totaal.toLocaleString("nl-NL")}&thinsp;
                <span className="font-normal text-black/40">leads</span>
              </span>
              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />{stats.vroeg} vroeg
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 ring-1 ring-inset ring-blue-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />{stats.pijplijn} pijplijn
                </span>
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              {/* Header */}
              <div className="flex items-center gap-4 border-b border-black/[0.06] bg-black/[0.015] px-5 py-2.5">
                <span className="w-[88px] shrink-0 text-[10px] font-semibold uppercase tracking-wider text-black/35" />
                <span className="min-w-0 flex-1 text-[10px] font-semibold uppercase tracking-wider text-black/35">Adres</span>
                <span className="w-[130px] shrink-0 text-[10px] font-semibold uppercase tracking-wider text-black/35">Gemeente</span>
                <span className="w-[80px] shrink-0 text-[10px] font-semibold uppercase tracking-wider text-black/35">Opp.</span>
                <span className="w-[100px] shrink-0 text-[10px] font-semibold uppercase tracking-wider text-black/35">Signaal</span>
                <span className="w-[100px] shrink-0 text-[10px] font-semibold uppercase tracking-wider text-black/35">Eigenaar</span>
              </div>

              {EXAMPLE_LEADS.map((lead, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-4 border-b border-black/[0.04] px-5 py-3.5 last:border-0 ${i === 0 ? "bg-amber-50/50" : ""}`}
                >
                  {/* Tier */}
                  <div className="w-[88px] shrink-0">
                    {lead.tier === "vroeg" ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />Vroeg
                      </span>
                    ) : lead.tier === "pijplijn" ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700 ring-1 ring-inset ring-blue-200">
                        <span className="h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />Pijplijn
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-semibold text-stone-600 ring-1 ring-inset ring-stone-200">
                        <span className="h-1.5 w-1.5 rounded-full bg-stone-400 shrink-0" />Laat
                      </span>
                    )}
                  </div>
                  <span className="min-w-0 flex-1 truncate text-[13px] font-medium">{lead.adres}</span>
                  <span className="w-[130px] shrink-0 text-[13px] text-black/45">{lead.gemeente}</span>
                  <span className="w-[80px] shrink-0 text-[13px] tabular-nums text-black/45">{lead.oppervlakte}</span>
                  <span className="w-[100px] shrink-0 text-[13px] text-black/45">{lead.timing}</span>
                  <span className="w-[100px] shrink-0 text-[13px] text-black/45">{lead.eigenaar}</span>
                </div>
              ))}

              <div className="border-t border-black/[0.04] bg-black/[0.015] px-5 py-3 text-center">
                <span className="text-[12px] text-black/35">
                  + {(stats.totaal - 4).toLocaleString("nl-NL")} leads zichtbaar na aanmelden
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ────────────────────────────────────────────── */}
      <section id="hoe" className="border-y border-black/[0.06] bg-black/[0.02] px-6 py-28">
        <div className="mx-auto max-w-5xl">
          <div className="mb-16 text-center">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-black/30">Hoe het werkt</p>
            <h2 className="text-[40px] font-bold tracking-[-0.025em]">Van publicatie naar telefoongesprek</h2>
          </div>

          <div className="grid gap-5 sm:grid-cols-3">
            {[
              {
                n: "01",
                title: "We scannen continu",
                body: "Dagelijks crawlen we alle Nederlandse gemeentebladen, het Kadaster en de BAG op sloopsignalen — omgevingsvergunningen, bestemmingswijzigingen en sloopmeldingen.",
              },
              {
                n: "02",
                title: "We classificeren op timing",
                body: "Elk pand krijgt een tier: Vroeg (aanvraagfase), Pijplijn (in behandeling) of Laat (vergunning verleend). Zo ziet u in één oogopslag waar de urgentie zit.",
              },
              {
                n: "03",
                title: "U belt als eerste",
                body: "Het dashboard toont adres, eigenaar, contactgegevens en sloopkans. Eén klik en u bent in gesprek vóórdat uw concurrent weet dat er een project is.",
              },
            ].map(({ n, title, body }) => (
              <div key={n} className="rounded-2xl bg-white border border-black/[0.06] p-8 shadow-sm">
                <div className="mb-5 text-[13px] font-semibold tabular-nums text-black/25">{n}</div>
                <h3 className="text-[18px] font-semibold tracking-tight">{title}</h3>
                <p className="mt-3 text-[14px] leading-[1.65] text-black/50">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── THREE TIERS ─────────────────────────────────────────────── */}
      <section className="px-6 py-28">
        <div className="mx-auto max-w-5xl">
          <div className="mb-16 text-center">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-black/30">Timing is alles</p>
            <h2 className="text-[40px] font-bold tracking-[-0.025em]">Drie fases. Één voorsprong.</h2>
            <p className="mx-auto mt-4 max-w-[520px] text-[17px] leading-[1.6] text-black/50">
              Elke lead krijgt een timing-label op basis van publicatiedatum en type bekendmaking — zodat u weet of u vandaag moet bellen of het voor volgend kwartaal kunt plannen.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-3">
            {/* Vroeg */}
            <div className="rounded-2xl border border-emerald-200/80 bg-white p-8 shadow-sm">
              <div className="mb-6">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  Vroeg signaal
                </span>
              </div>
              <h3 className="text-[18px] font-semibold tracking-tight">Vergunningfase —<br />voor de markt uit</h3>
              <p className="mt-3 text-[14px] leading-[1.65] text-black/50">
                Sloopvergunning aangevraagd voor een monument of pand in beschermd gebied. De procedure loopt nog. De eigenaar oriënteert zich en heeft zelden al een sloopbedrijf in beeld.
              </p>
              <div className="mt-6 flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3">
                <Clock className="h-4 w-4 text-emerald-600 shrink-0" />
                <span className="text-[13px] font-semibold text-emerald-800">4 – 12 maanden tot sloop</span>
              </div>
            </div>

            {/* Pijplijn */}
            <div className="rounded-2xl border border-blue-200/80 bg-white p-8 shadow-sm">
              <div className="mb-6">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-[11px] font-semibold text-blue-700 ring-1 ring-inset ring-blue-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                  Pijplijn
                </span>
              </div>
              <h3 className="text-[18px] font-semibold tracking-tight">Vergunning verleend —<br />fase van offertes</h3>
              <p className="mt-3 text-[14px] leading-[1.65] text-black/50">
                Sloopvergunning verleend (monument of beschermd gebied). De eigenaar gaat nu sloopbedrijven vergelijken. Wie deze week belt, zit in de eerste ronde offertes.
              </p>
              <div className="mt-6 flex items-center gap-2 rounded-xl bg-blue-50 px-4 py-3">
                <Eye className="h-4 w-4 text-blue-600 shrink-0" />
                <span className="text-[13px] font-semibold text-blue-800">1 – 6 maanden tot sloop</span>
              </div>
            </div>

            {/* Korte termijn */}
            <div className="rounded-2xl border border-amber-200/80 bg-white p-8 shadow-sm">
              <div className="mb-6">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  Korte termijn
                </span>
              </div>
              <h3 className="text-[18px] font-semibold tracking-tight">Sloopmelding ingediend —<br />werk staat ingepland</h3>
              <p className="mt-3 text-[14px] leading-[1.65] text-black/50">
                Reguliere sloop mag wettelijk pas 4 weken na melding starten. Bij particulieren en MKB is op dit moment nog niet altijd een definitieve sloper gekozen. Direct contact loont.
              </p>
              <div className="mt-6 flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-3">
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                <span className="text-[13px] font-semibold text-amber-800">4 – 12 weken tot sloop</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── PRICING ─────────────────────────────────────────────────── */}
      <section id="pricing" className="border-y border-black/[0.06] bg-black/[0.02] px-6 py-28">
        <div className="mx-auto max-w-lg text-center">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-black/30">Prijzen</p>
          <h2 className="text-[40px] font-bold tracking-[-0.025em]">Één prijs.<br />Alles inbegrepen.</h2>
          <p className="mt-4 text-[17px] leading-[1.6] text-black/50">
            14 dagen gratis proberen. Daarna €149 per maand. Opzegbaar wanneer u wilt.
          </p>

          {/* Card */}
          <div className="mt-12 rounded-3xl border border-black/[0.08] bg-white p-10 text-left shadow-[0_8px_40px_-8px_rgba(0,0,0,0.10)]">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-black/35">Pro</p>
                <div className="mt-2.5 flex items-baseline gap-2">
                  <span className="text-[56px] font-bold leading-none tracking-[-0.03em]">€149</span>
                  <span className="text-[15px] text-black/40">/ maand excl. btw</span>
                </div>
              </div>
              <span className="mt-1 rounded-full bg-amber-100 px-3 py-1 text-[11px] font-semibold text-amber-700 ring-1 ring-inset ring-amber-200 shrink-0">
                Meest gekozen
              </span>
            </div>

            <div className="mt-8 space-y-3.5">
              {[
                "Alle sloopkansen in heel Nederland",
                "Vroeg, Pijplijn én Laat tier",
                "Contactgegevens eigenaar & corporatie",
                "Onbeperkt leads exporteren (CSV)",
                "Real-time e-mailmeldingen",
                "Filter op regio, type pand en bouwjaar",
                "Opzegbaar per maand",
              ].map((f) => (
                <div key={f} className="flex items-center gap-3 text-[14px]">
                  <CheckCircle2 className="h-[17px] w-[17px] shrink-0 text-emerald-500" />
                  {f}
                </div>
              ))}
            </div>

            <Link
              href="/login"
              className="mt-10 flex w-full items-center justify-center gap-2 rounded-full bg-black py-4 text-[15px] font-semibold text-white hover:bg-black/80 transition-colors"
            >
              14 dagen gratis proberen
              <ArrowRight className="h-4 w-4" />
            </Link>
            <p className="mt-3.5 text-center text-[12px] text-black/35">
              Geen creditcard vereist · Betalen via iDEAL · Opzegbaar per maand
            </p>
          </div>

          <p className="mt-8 text-[13px] text-black/40">
            Meerdere gebruikers of API-toegang nodig?{" "}
            <a href="mailto:hallo@sloopradar.nl" className="text-black underline-offset-2 hover:underline">
              Neem contact op voor Enterprise
            </a>
          </p>
        </div>
      </section>

      {/* ─── FINAL CTA ───────────────────────────────────────────────── */}
      <section className="px-6 py-16">
        <div className="mx-auto max-w-4xl overflow-hidden rounded-3xl bg-black px-12 py-20 text-center text-white">
          <h2 className="text-[clamp(32px,5vw,48px)] font-bold tracking-[-0.03em] leading-[1.1]">
            Begin vandaag.<br />Bel morgen.
          </h2>
          <p className="mx-auto mt-5 max-w-sm text-[17px] leading-[1.6] text-white/45">
            {stats.vroeg} sloopkansen staan nu in de aanvraagfase. Hoeveel van uw concurrenten zijn er al op gebeld?
          </p>
          <Link
            href="/login"
            className="mt-10 inline-flex items-center gap-2 rounded-full bg-white px-8 py-3.5 text-[15px] font-semibold text-black hover:bg-white/90 transition-colors"
          >
            Gratis starten — geen creditcard
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* ─── FOOTER ──────────────────────────────────────────────────── */}
      <footer className="border-t border-black/[0.06] px-6 py-8">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-amber-500" strokeWidth={2} />
            <span className="text-[14px] font-semibold">Sloopradar</span>
          </div>
          <div className="flex flex-wrap items-center gap-6 text-[12px] text-black/40">
            <a href="mailto:hallo@sloopradar.nl" className="hover:text-black transition-colors">hallo@sloopradar.nl</a>
            <Link href="/login" className="hover:text-black transition-colors">Inloggen</Link>
            <span>© 2026 Sloopradar · Gemaakt in Nederland</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
