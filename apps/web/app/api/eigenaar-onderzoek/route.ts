import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

export async function POST(req: NextRequest) {
  const { adres, gemeente, postcode, bag_pand_id } = await req.json();

  if (!adres && !bag_pand_id) {
    return NextResponse.json({ error: "Onvoldoende gegevens" }, { status: 400 });
  }

  const locatie = [adres, postcode, gemeente].filter(Boolean).join(", ");
  const prompt = `Zoek op wie de eigenaar is van het pand op het adres: ${locatie}${bag_pand_id ? ` (BAG pand-ID: ${bag_pand_id})` : ""}.

Zoek naar: eigendomsregistratie, woningcorporatie, vastgoedbedrijf, gemeente of particulier eigenaar. Kijk ook naar recente nieuwsberichten, bestemmingsplan-documenten of openbare registers.

Geef je bevindingen terug als één alinea van maximaal 3 zinnen. Vermeld de naam van de eigenaar als je die vindt, anders je best educated guess op basis van wat je vindt. Begin direct met de inhoud, geen inleiding.`;

  try {
    const response = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 300,
      tools: [
        {
          type: "web_search_20250305" as const,
          name: "web_search",
          max_uses: 3,
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
