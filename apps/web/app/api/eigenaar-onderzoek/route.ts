import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

export async function POST(req: NextRequest) {
  const { adres, gemeente, postcode, bag_pand_id } = await req.json();

  if (!adres && !bag_pand_id) {
    return NextResponse.json({ error: "Onvoldoende gegevens" }, { status: 400 });
  }

  const locatie = [adres, postcode, gemeente].filter(Boolean).join(", ");
  const gemeenteNaam = (gemeente ?? locatie.split(",").pop()?.trim() ?? "").trim();
  const straatHuisnummer = adres?.trim() ?? locatie.split(",")[0]?.trim() ?? locatie;

  const prompt = `Bepaal wie de eigenaar is van: ${locatie}${bag_pand_id ? ` (BAG ID: ${bag_pand_id})` : ""}.

Doorloop deze zoekvolgorde en stop zodra je een antwoord hebt:

1. Zoek op: "${straatHuisnummer}" "${gemeenteNaam}" sloopvergunning — de aanvraag of vergunning vermeldt vaak de aanvrager/eigenaar bij naam.
2. Zoek op: "${straatHuisnummer}" "${gemeenteNaam}" eigenaar corporatie — controleer of een woningcorporatie dit adres in haar portefeuille heeft.
3. Zoek welke woningcorporaties actief zijn in ${gemeenteNaam || "deze gemeente"} (bijv. Acantus, Woonzorg, Lefier, Wonen Emmen, etc.) en zoek vervolgens "[corporatienaam] ${straatHuisnummer}".
4. Zoek op: "${straatHuisnummer}" "${gemeenteNaam}" sloop renovatie nieuwbouw — nieuwsberichten, bewonersberichten of projectpagina's noemen dikwijls de opdrachtgever.
5. Zoek op: site:officielebekendmakingen.nl "${straatHuisnummer}" — de publicatietekst bevat soms de naam van de aanvrager.
6. Zoek op: "${straatHuisnummer}" "${gemeenteNaam}" vastgoed bv nv stichting gemeente.

REGELS:
- Geef nooit op na één mislukte zoekopdracht. Probeer alle stappen.
- Als het een gewoon woonhuis van een particulier blijkt: stuur ALLEEN "WOONHUIS" terug.
- Anders: maximaal 2 zinnen. Noem de eigenaar bij naam als je die vindt. Zeg wat je bron was (bijv. "Uit de sloopvergunningaanvraag" of "Acantus beheert dit complex"). Begin direct met de inhoud.`;

  try {
    const response = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 300,
      tools: [
        {
          type: "web_search_20250305" as const,
          name: "web_search",
          max_uses: 6,
        },
      ],
      messages: [{ role: "user", content: prompt }],
    });

    // Extraheer de tekst uit het laatste text-blok
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
