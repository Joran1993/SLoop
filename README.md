# Sloopradar — KOOP SRU Databron Validator

Twee scripts om sloop- en asbest-bekendmakingen op te halen via de publieke
KOOP SRU 2.0 API en te beoordelen als basis voor Sloopradar.

## Vereisten

- Python 3.9+
- `requests` en `lxml` (geen API-key nodig)

```bash
pip install requests lxml
```

## Gebruik

### 1. Bekendmakingen ophalen

```bash
# Afgelopen 7 dagen (default)
python sru_pull.py --out results.json

# Afgelopen 30 dagen
python sru_pull.py --days 30 --out results.json

# Kleinere pagina's (handig bij timeouts)
python sru_pull.py --days 14 --max-records 50 --out results.json
```

Opties:

| Optie | Default | Beschrijving |
|-------|---------|--------------|
| `--days N` | 7 | Terugkijkperiode in dagen |
| `--out FILE` | results.json | Output JSON-bestand |
| `--max-records N` | 100 | Records per pagina (max 100) |

### 2. Rapport genereren

```bash
# Naar stdout (handig voor quick-scan)
python inspect_results.py results.json

# Naar bestand
python inspect_results.py results.json --out rapport.md
```

## Output

### results.json

```json
{
  "samenvatting": {
    "totaal_publicaties": 142,
    "datumbereik": { "van": "2024-04-27", "tot": "2024-05-04" },
    "top_20_gemeenten": { "Amsterdam": 12, "Rotterdam": 8, ... },
    "per_trefwoord": { "asbest": 89, "sloopmelding": 61, ... },
    "publicaties_zonder_adres": 34,
    "opvallende_observaties": [...]
  },
  "publicaties": [
    {
      "identifier": "https://...",
      "titel": "Kennisgeving sloopmelding Kerkstraat 12",
      "publicatiedatum": "2024-05-01",
      "gemeente": "Gemeente Utrecht",
      "publicatietype": "Gemeenteblad",
      "snippet": "...",
      "matched_keywords": ["sloopmelding"],
      "has_address_hint": true
    }
  ]
}
```

### rapport.md

Bevat:
- Samenvattingstabel met adresdekkingsgraad
- Top 10 meest recente publicaties
- Distributie per gemeente en trefwoord
- 5 voorbeelden mét / 5 voorbeelden zonder adresinformatie
- Conclusie over bruikbaarheid voor BAG-koppeling

## Databron

- **Endpoint:** https://repository.overheid.nl/sru
- **Documentatie:** https://data.overheid.nl/dataset/officiele-bekendmakingen
- **Publiek, geen authenticatie vereist**

## Gezochte trefwoorden

`sloopmelding` · `sloopactiviteit` · `asbest` · `kennisgeving sloop` · `omgevingsvergunning sloop`

## Sloopradar propositie

```
SRU-publicatie → adresextractie → BAG lookup (bouwjaar)
                                        ↓
                          pand gebouwd vóór 1994?
                          → verhoogde asbestkans → lead voor saneerder
```
