import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

export async function POST(req: NextRequest) {
  const { adres, gemeente, postcode, bag_pand_id } = await req.json();

  if (!adres && !bag_pand_id) {
    return NextResponse.json({ error: "Onvoldoende gegevens" }, { status: 400 });
  }

  const locatie = [adres, postcode, gemeente].filter(Boolean).join(", ");
  const gemeenteNaam = (gemeente ?? "").trim();
  const straatHuisnummer = (adres ?? "").trim();
  const pc = (postcode ?? "").trim();

  const prompt = `Bepaal de eigenaar van: ${locatie}${bag_pand_id ? ` (BAG ID: ${bag_pand_id})` : ""}.

Gebruik deze zoekopdrachten exact zo, in volgorde:
1. "${straatHuisnummer}" "${pc}" sloop
2. "${straatHuisnummer}" site:${gemeenteNaam.toLowerCase().replace(/\s+/g, "")}.nl
3. site:officielebekendmakingen.nl "${straatHuisnummer}" "${pc}"
4. "${straatHuisnummer}" "${gemeenteNaam}" woningcorporatie
5. Welke corporaties zijn actief in ${gemeenteNaam}? Zoek dan: [corporatienaam] "${pc}"
6. "${straatHuisnummer}" "${gemeenteNaam}" vastgoed OR gemeente OR stichting

OUTPUT-REGELS (strikt):
- Particulier woonhuis → antwoord uitsluitend: WOONHUIS
- Eigenaar gevonden → maximaal 1 zin. Noem naam + bron. Geen inleiding.
- Niet gevonden maar redelijke gok mogelijk → maximaal 1 zin met "vermoedelijk" + onderbouwing.
- Echt niets → maximaal 1 zin: wat je WEL weet (bijv. welk type pand, welke corporaties actief zijn).
- Geef NOOIT een uitgebreide verontschuldiging of lijst met suggesties.`;

  try {
    const response = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 150,
      tools: [
        {
          type: "web_search_20250305" as const,
          name: "web_search",
          max_uses: 6,
        },
      ],
      messages: [{ role: "user", content: prompt }],
    });

    const tekst = response.content
      .filter((b) => b.type === "text")
      .map((b) => (b as { type: "text"; text: string }).text)
      .join(" ")
      .trim();

    return NextResponse.json({ tekst: tekst || null });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Onbekende fout";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
