import { NextRequest, NextResponse } from "next/server";

const BAG_WFS =
  "https://service.pdok.nl/lv/bag/wfs/v2_0?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&OUTPUTFORMAT=application/json&count=10";

const LABEL_MAP: Record<string, string> = {
  woonfunctie:        "wonen",
  kantoorfunctie:     "kantoor",
  winkelfunctie:      "winkel",
  industriefunctie:   "industrie",
  logiesfunctie:      "logies",
  gezondheidsfunctie: "gezondheidszorg",
  onderwijsfunctie:   "onderwijs",
  bijeenkomstfunctie: "bijeenkomst",
  sportfunctie:       "sport",
  celfunctie:         "detentie",
  overige:            "overige",
};

function inferZin(doelen: string[], oppTotaal: number | null): string | null {
  const uniq = [...new Set(doelen.map((d) => d.toLowerCase().trim()))];
  const labels = uniq.map((d) => {
    for (const [key, val] of Object.entries(LABEL_MAP)) {
      if (d.includes(key)) return val;
    }
    return d;
  }).filter((v, i, a) => a.indexOf(v) === i); // dedup labels

  const isWoon = uniq.some((d) => d.includes("woon"));
  const isBedrijf = uniq.some((d) =>
    d.includes("kantoor") || d.includes("winkel") ||
    d.includes("industrie") || d.includes("logies") || d.includes("gezondheid")
  );
  const isMaatschappelijk = uniq.some((d) =>
    d.includes("onderwijs") || d.includes("bijeenkomst") ||
    d.includes("sport") || d.includes("cel")
  );
  const isGemengd = labels.length > 1;

  if (isGemengd && isWoon && isBedrijf) {
    return `Gemengd gebruik (${labels.join(" + ")}) — vermoedelijk zakelijk of institutioneel eigendom.`;
  }
  if (isBedrijf) {
    return `Bedrijfsmatig gebruik (${labels.join(", ")}) — vermoedelijk zakelijk of institutioneel eigendom.`;
  }
  if (isMaatschappelijk) {
    return `Maatschappelijk gebruik (${labels.join(", ")}) — vermoedelijk gemeente, stichting of overheidsinstantie.`;
  }
  if (isWoon) {
    if (oppTotaal && oppTotaal > 800) {
      return `Woongebouw, ${oppTotaal.toLocaleString("nl-NL")} m² totaal — vermoedelijk woningcorporatie of meerdere eenheden.`;
    }
    return `Woonbestemming — vermoedelijk particulier eigendom.`;
  }
  return null;
}

export async function GET(req: NextRequest) {
  const bagPandId = req.nextUrl.searchParams.get("bag_pand_id")?.trim();
  if (!bagPandId) {
    return NextResponse.json({ zin: null }, { status: 400 });
  }

  try {
    const url =
      `${BAG_WFS}&TYPENAMES=bag:verblijfsobject` +
      `&CQL_FILTER=pandidentificatie='${encodeURIComponent(bagPandId)}'`;

    const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return NextResponse.json({ zin: null });

    const json = await res.json();
    const features: Array<{ properties: Record<string, unknown> }> =
      json?.features ?? [];

    const doelen: string[] = [];
    let oppTotaal = 0;

    for (const f of features) {
      const p = f.properties;
      const g = p?.gebruiksdoel;
      if (Array.isArray(g)) doelen.push(...g.map(String));
      else if (typeof g === "string") doelen.push(g);
      const opp = Number(p?.oppervlakte ?? 0);
      if (!isNaN(opp)) oppTotaal += opp;
    }

    const zin = inferZin(doelen, oppTotaal > 0 ? oppTotaal : null);
    return NextResponse.json(
      { zin },
      { headers: { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=3600" } }
    );
  } catch {
    return NextResponse.json({ zin: null });
  }
}
