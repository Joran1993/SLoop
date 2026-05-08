import Link from "next/link";
import { Building2, MapPin, Bell, Download, ChevronRight } from "lucide-react";

const features = [
  {
    icon: MapPin,
    title: "Sloopkansen in kaart",
    desc: "Wij monitoren dagelijks duizenden gemeentebladen en detecteren sloopmeldingen voordat uw concurrenten ze zien.",
  },
  {
    icon: Bell,
    title: "Automatische meldingen",
    desc: "Stel filters in op provincie, oppervlakte of score. Ontvang dagelijks of wekelijks nieuwe kansen direct in uw inbox.",
  },
  {
    icon: Download,
    title: "CSV-export voor Pro",
    desc: "Exporteer gefilterde leads direct naar uw eigen CRM of Excel. Geen handmatig zoeken meer.",
  },
];

const pricing = [
  {
    name: "Starter",
    price: "Gratis",
    period: "",
    description: "Verken sloopkansen in één provincie.",
    features: [
      "1 provincie",
      "5 leads per dag",
      "Kaartweergave",
      "Score-indicatie",
    ],
    cta: "Gratis starten",
    href: "/login",
    highlight: false,
  },
  {
    name: "Pro",
    price: "€149",
    period: "/ maand",
    description: "Heel Nederland, onbeperkt leads, export.",
    features: [
      "Heel Nederland",
      "Onbeperkte leads",
      "CSV-export",
      "10 meldingen",
      "Prioriteit support",
    ],
    cta: "Pro starten",
    href: "/login",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Op maat",
    period: "",
    description: "Custom scoring, API-toegang, teamaccounts.",
    features: [
      "Alles van Pro",
      "Custom scoreweights",
      "API-toegang",
      "Onbeperkte meldingen",
      "Dedicated support",
    ],
    cta: "Contact opnemen",
    href: "mailto:hallo@sloopradar.nl",
    highlight: false,
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Nav */}
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-accent" strokeWidth={2} />
            <span className="font-semibold text-sm tracking-tight">
              Sloopradar
            </span>
          </div>
          <Link
            href="/login"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Inloggen
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto max-w-5xl px-4 py-20 text-center">
          <h1 className="text-4xl font-bold tracking-tight leading-tight sm:text-5xl">
            Sloopkansen vinden
            <br />
            voordat de concurrentie ze ziet
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base text-muted-foreground">
            Sloopradar detecteert dagelijks nieuwe sloopmeldingen via publieke
            bronnen en scoort ze op asbestrisico, omvang en circulair potentieel.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/login"
              className="inline-flex items-center rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Gratis starten
            </Link>
            <Link
              href="#pricing"
              className="inline-flex items-center rounded-md border border-border px-5 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Bekijk prijzen
            </Link>
          </div>
        </section>

        {/* Features */}
        <section className="border-y border-border bg-muted/30">
          <div className="mx-auto max-w-5xl px-4 py-16">
            <div className="grid gap-8 sm:grid-cols-3">
              {features.map(({ icon: Icon, title, desc }) => (
                <div key={title} className="space-y-2">
                  <div className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-accent/20 text-accent">
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                  </div>
                  <h3 className="text-sm font-semibold">{title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="mx-auto max-w-5xl px-4 py-20">
          <h2 className="text-center text-2xl font-bold tracking-tight">
            Eenvoudige prijzen
          </h2>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            Start gratis. Upgrade wanneer u klaar bent.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {pricing.map((plan) => (
              <div
                key={plan.name}
                className={`relative rounded-xl border p-6 space-y-4 ${
                  plan.highlight
                    ? "border-foreground/20 bg-foreground text-background shadow-lg"
                    : "border-border bg-card"
                }`}
              >
                {plan.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-accent px-3 py-0.5 text-xs font-semibold text-accent-foreground">
                    Meest gekozen
                  </span>
                )}
                <div>
                  <p
                    className={`text-xs font-semibold uppercase tracking-wider ${
                      plan.highlight
                        ? "text-background/60"
                        : "text-muted-foreground"
                    }`}
                  >
                    {plan.name}
                  </p>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="text-2xl font-bold">{plan.price}</span>
                    {plan.period && (
                      <span
                        className={`text-sm ${
                          plan.highlight
                            ? "text-background/60"
                            : "text-muted-foreground"
                        }`}
                      >
                        {plan.period}
                      </span>
                    )}
                  </div>
                  <p
                    className={`mt-1 text-sm ${
                      plan.highlight
                        ? "text-background/70"
                        : "text-muted-foreground"
                    }`}
                  >
                    {plan.description}
                  </p>
                </div>
                <ul className="space-y-1.5">
                  {plan.features.map((f) => (
                    <li
                      key={f}
                      className={`flex items-center gap-2 text-sm ${
                        plan.highlight ? "text-background/80" : ""
                      }`}
                    >
                      <span
                        className={`h-1 w-1 rounded-full shrink-0 ${
                          plan.highlight ? "bg-background/40" : "bg-foreground/30"
                        }`}
                      />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.href}
                  className={`block text-center rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                    plan.highlight
                      ? "bg-background text-foreground hover:bg-background/90"
                      : "bg-primary text-primary-foreground hover:bg-primary/90"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto max-w-5xl px-4 py-6 flex items-center justify-between text-xs text-muted-foreground">
          <span>© 2026 Sloopradar</span>
          <span>Gemaakt in Nederland</span>
        </div>
      </footer>
    </div>
  );
}
