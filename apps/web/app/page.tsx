import Link from "next/link";
import Image from "next/image";
import { Building2, Clock, Eye, AlertTriangle, CheckCircle2, ArrowRight, ChevronRight } from "lucide-react";
import { createClient } from "@/lib/supabase/server";
import { WerkgebiedPreview } from "@/components/werkgebied-preview";

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
      <section className="px-6 pt-16 pb-12">
        <div className="mx-auto max-w-6xl">
          <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">

            {/* Left: tekst */}
            <div>
              <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-black/[0.08] bg-black/[0.03] px-3.5 py-1.5 text-[12px] font-medium text-black/50">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {stats.vroeg} nieuwe sloopkansen deze week · live data
              </div>

              <h1 className="text-[clamp(36px,4.5vw,64px)] font-bold leading-[1.04] tracking-[-0.03em] text-black">
                De aanvraag staat online.<br />
                Uw concurrent weet het<br /> nog niet.
              </h1>

              <p className="mt-6 max-w-[440px] text-[18px] leading-[1.6] text-black/50">
                Sloopradar monitort dagelijks alle Nederlandse gemeentebladen en levert nieuwe sloopkansen als lead — weken vóór de offertefase.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
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
                  Bekijk uw werkgebied
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>

            {/* Right: foto */}
            <div className="hidden lg:block">
              <div className="relative h-[460px] overflow-hidden rounded-2xl shadow-[0_20px_60px_-12px_rgba(0,0,0,0.22)]">
                <Image
                  src="https://images.unsplash.com/photo-1665737847143-3080d0a12972?auto=format&fit=crop&w=900&q=80"
                  alt="Sloopwerkzaamheden in Nederland"
                  fill
                  className="object-cover"
                  priority
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-black/10 to-transparent" />
                <div className="absolute bottom-5 left-5 right-5">
                  <p className="text-[13px] font-medium text-white/80">
                    Dagelijks nieuwe sloopkansen via officiële overheidsregistraties
                  </p>
                </div>
              </div>
            </div>

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

      {/* ─── WERKGEBIED PREVIEW ───────────────────────────────────────── */}
      <section id="preview" className="px-6 py-28">
        <div className="mx-auto max-w-2xl">
          <div className="mb-10 text-center">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-black/30">Uw werkgebied</p>
            <h2 className="text-[40px] font-bold tracking-[-0.025em]">Bekijk uw regio</h2>
            <p className="mx-auto mt-3 max-w-sm text-[16px] leading-[1.6] text-black/45">
              Vul uw postcode of plaats in en zie direct hoeveel sloopkansen er nu in uw werkgebied staan.
            </p>
          </div>
          <WerkgebiedPreview />
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

      {/* ─── FOTO STRIP ──────────────────────────────────────────────── */}
      <div className="px-6 pb-8">
        <div className="mx-auto max-w-5xl">
          <div className="relative h-[220px] overflow-hidden rounded-2xl sm:h-[280px]">
            <Image
              src="https://images.unsplash.com/photo-1719047655247-39d1577bfee0?auto=format&fit=crop&w=1400&h=560&q=80"
              alt="Sloopkansen in Nederlandse woonwijken"
              fill
              className="object-cover"
            />
            <div className="absolute inset-0 bg-black/50" />
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center px-6">
              <p className="text-[22px] font-bold tracking-[-0.02em] text-white sm:text-[28px]">
                {stats.totaal.toLocaleString("nl-NL")} panden in Nederland
              </p>
              <p className="text-[14px] text-white/65">
                Gemonitord via officiële publicaties · dagelijks bijgewerkt
              </p>
            </div>
          </div>
        </div>
      </div>

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
        <div className="mx-auto max-w-5xl">
          <div className="mb-16 text-center">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-black/30">Prijzen</p>
            <h2 className="text-[40px] font-bold tracking-[-0.025em]">Kies uw schaal.</h2>
            <p className="mt-4 text-[17px] leading-[1.6] text-black/50">
              14 dagen gratis proberen. Geen creditcard vereist. Opzegbaar per maand.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-3">

            {/* Starter */}
            <div className="rounded-2xl border border-black/[0.08] bg-white p-8 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-black/35">Starter</p>
              <div className="mt-3 flex items-baseline gap-1.5">
                <span className="text-[44px] font-bold leading-none tracking-[-0.03em]">€95</span>
                <span className="text-[14px] text-black/40">/ mnd excl. btw</span>
              </div>
              <p className="mt-2 text-[13px] text-black/45">ZZP &amp; klein sloopbedrijf · 1 regio</p>

              <div className="my-7 border-t border-black/[0.06]" />

              <div className="space-y-3">
                {[
                  "Leads in 1 regio naar keuze",
                  "Pijplijn &amp; Korte termijn tier",
                  "Contactgegevens eigenaar",
                  "E-mailmeldingen nieuwe leads",
                  "Filter op type pand en bouwjaar",
                ].map((f) => (
                  <div key={f} className="flex items-start gap-2.5 text-[13px] text-black/60">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                    <span dangerouslySetInnerHTML={{ __html: f }} />
                  </div>
                ))}
              </div>

              <Link
                href="/login"
                className="mt-8 flex w-full items-center justify-center gap-2 rounded-full border border-black/[0.12] py-3 text-[14px] font-semibold text-black hover:bg-black/[0.04] transition-colors"
              >
                Gratis proberen
              </Link>
            </div>

            {/* Pro — highlighted */}
            <div className="relative rounded-2xl border border-black bg-black p-8 shadow-[0_12px_40px_-8px_rgba(0,0,0,0.30)] text-white">
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-amber-400 px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider text-black">
                Meest gekozen
              </span>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-white/40">Pro</p>
              <div className="mt-3 flex items-baseline gap-1.5">
                <span className="text-[44px] font-bold leading-none tracking-[-0.03em]">€245</span>
                <span className="text-[14px] text-white/40">/ mnd excl. btw</span>
              </div>
              <p className="mt-2 text-[13px] text-white/50">Middelgroot bedrijf · meerdere regio&apos;s</p>

              <div className="my-7 border-t border-white/[0.1]" />

              <div className="space-y-3">
                {[
                  "Leads in heel Nederland",
                  "Vroeg, Pijplijn &amp; Korte termijn tier",
                  "Contactgegevens eigenaar &amp; corporatie",
                  "Onbeperkt exporteren (CSV)",
                  "Real-time e-mailmeldingen",
                  "Filter op regio, type pand en bouwjaar",
                ].map((f) => (
                  <div key={f} className="flex items-start gap-2.5 text-[13px] text-white/70">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                    <span dangerouslySetInnerHTML={{ __html: f }} />
                  </div>
                ))}
              </div>

              <Link
                href="/login"
                className="mt-8 flex w-full items-center justify-center gap-2 rounded-full bg-white py-3 text-[14px] font-semibold text-black hover:bg-white/90 transition-colors"
              >
                Gratis proberen
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            {/* Premium */}
            <div className="rounded-2xl border border-black/[0.08] bg-white p-8 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-black/35">Premium</p>
              <div className="mt-3 flex items-baseline gap-1.5">
                <span className="text-[44px] font-bold leading-none tracking-[-0.03em]">€595</span>
                <span className="text-[14px] text-black/40">/ mnd excl. btw</span>
              </div>
              <p className="mt-2 text-[13px] text-black/45">Groot bedrijf · alle signalen</p>

              <div className="my-7 border-t border-black/[0.06]" />

              <div className="space-y-3">
                {[
                  "Alles uit Pro",
                  "Voorsignaal — aanvraagfase (vroegst)",
                  "Meerdere gebruikers",
                  "API-toegang",
                  "Prioriteit support",
                  "Maatwerk rapportages",
                ].map((f) => (
                  <div key={f} className="flex items-start gap-2.5 text-[13px] text-black/60">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                    {f}
                  </div>
                ))}
              </div>

              <Link
                href="/login"
                className="mt-8 flex w-full items-center justify-center gap-2 rounded-full border border-black/[0.12] py-3 text-[14px] font-semibold text-black hover:bg-black/[0.04] transition-colors"
              >
                Gratis proberen
              </Link>
            </div>

          </div>

          <p className="mt-8 text-center text-[13px] text-black/40">
            Geen creditcard vereist · Betalen via iDEAL · Opzegbaar per maand ·{" "}
            <a href="mailto:hallo@sloopradar.nl" className="text-black underline-offset-2 hover:underline">
              Contact voor Enterprise
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
            <span>© 2026 Sloopradar · een product van CircuBouw · Gemaakt in Nederland</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
