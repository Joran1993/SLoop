import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free";

// In-process cache: overleeft serverless cold-starts niet, maar CDN s-maxage wel.
const cache = new Map<string, { data: unknown; expires: number }>();

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

function anonymizeStraat(adres: string): string {
  // "Kamphofstraat 14" → "████hofstraat" (strip nummer, mask eerste 4 chars)
  const straat = adres.split(/\s+\d/)[0].trim();
  return "████" + straat.slice(4);
}

function revealIndex(ip: string): number {
  return ip.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 3;
}

async function geocode(q: string): Promise<{ lat: number; lng: number } | null> {
  // Probeer postcode-type eerst, val terug op vrije zoekopdracht
  for (const fq of ["type:postcode", ""]) {
    const params = new URLSearchParams({ q, rows: "1", fl: "centroide_ll" });
    if (fq) params.set("fq", fq);
    try {
      const res = await fetch(`${PDOK_URL}?${params}`);
      if (!res.ok) continue;
      const json = await res.json();
      const doc = json?.response?.docs?.[0];
      const centroide: string = doc?.centroide_ll ?? "";
      const m = centroide.match(/POINT\(([\d.]+)\s+([\d.]+)\)/);
      if (m) return { lng: parseFloat(m[1]), lat: parseFloat(m[2]) };
    } catch {
      continue;
    }
  }
  return null;
}

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q")?.trim() ?? "";
  const radius = Math.min(100, Math.max(5, Number(req.nextUrl.searchParams.get("radius") ?? "25")));

  if (!q) {
    return NextResponse.json({ error: "q vereist" }, { status: 400 });
  }

  const cacheKey = `${q.toLowerCase()}|${radius}`;
  const hit = cache.get(cacheKey);
  if (hit && hit.expires > Date.now()) {
    return NextResponse.json(hit.data, {
      headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=300" },
    });
  }

  const coords = await geocode(q);
  if (!coords) {
    return NextResponse.json(
      { error: "Postcode of plaatsnaam niet herkend. Probeer een Nederlandse postcode (4 cijfers + letters) of plaatsnaam." },
      { status: 404 }
    );
  }

  const { data, error } = await supabase.rpc("get_preview_leads", {
    p_lat: coords.lat,
    p_lng: coords.lng,
    p_radius_km: radius,
  });

  if (error) {
    return NextResponse.json({ error: "Ophalen mislukt" }, { status: 502 });
  }

  // Anonimiseer: toon 1 volledig adres, 2 gemaskeerd
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim()
    ?? req.headers.get("x-real-ip")
    ?? "0";
  const idx = revealIndex(ip);

  const samples = ((data?.samples ?? []) as Array<{
    adres: string; plaats: string; opp_m2: number; dagen: number; tier: string;
  }>).map((s, i) => ({
    adres:    i === idx % Math.max(1, data.samples?.length ?? 1) ? s.adres : anonymizeStraat(s.adres),
    volledig: i === idx % Math.max(1, data.samples?.length ?? 1),
    plaats:   s.plaats,
    opp_m2:   s.opp_m2,
    dagen:    s.dagen,
    tier:     s.tier,
  }));

  const result = { ...data, samples };
  cache.set(cacheKey, { data: result, expires: Date.now() + 3_600_000 });

  return NextResponse.json(result, {
    headers: { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=300" },
  });
}
