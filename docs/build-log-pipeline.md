# Build Log — Sloopradar Pijplijn-uitbreiding Fase A

Datum: 2026-05-07  
Model: Claude Sonnet 4.6

---

## Wat is gebouwd

### Database (migration 20260507000700_pipeline.sql) ✅
- `pipeline_signals` — centrale signaaltabel voor alle 7 bronnen
- `pipeline_projects` — gederiveerde sloopprojecten per pand/cluster
- `pipeline_project_signals` — koppeltabel signalen ↔ projecten
- `pipeline_predictions_log` — auditlog voor toekomstig ML-model
- `customer_feedback` — klantfeedback op pipeline-projecten
- RLS policies: alleen betalende users mogen lezen
- View `pipeline_projects_api` met WGS84-coördinaten
- Migration gepusht: ✅

### Adapter-laag (`apps/worker/src/sources/pipeline/`) ✅
- `base.py` — `PipelineSourceAdapter` ABC, `RawSignal`, `ParsedSignal` dataclasses, `geojson_to_ewkt()`
- `ruimtelijkeplannen_adapter.py` — Bron 1 (PDOK WFS + RP REST fallback)
  - **Status:** API offline — PDOK WFS `service.pdok.nl/kadaster/plannen/wfs/v1_0` geeft 404
  - Ruimtelijkeplannen.nl REST API v3 retourneert HTML i.p.v. JSON
  - Adapter is klaar maar wacht op werkend endpoint (Fase B fix)
- `koop_sloopmelding_adapter.py` — Bron 1b (eigen sloop_leads DB)
  - Leest 513 verrijkte leads uit Supabase
  - Converteert GeoJSON Point (EPSG:28992) → EWKT
  - Geeft signaaltype `sloopmelding` met sterkte `high`
- `kadaster_stub.py` — Bron 2 stub (KADASTER_ENABLED=false)

### Predictor v1 (`apps/worker/src/predictor/rules.py`) ✅
- Regelgebaseerd model: gewogen som → tanh-squash → sloop_kans (0–1)
- Diversiteitsbonus voor meerdere signaaltypes op zelfde pand
- Horizon-berekening: kortste min, langste max van alle signalen
- Configureerbaar via `config/predictor_rules.yaml`

### Clusterer (`apps/worker/src/clusterer/clusterer.py`) ✅
- Strategie 1: groepeer op `bag_pand_id` (meest nauwkeurig)
- Strategie 2: ruimtelijke clustering op 200m radius (RD New euclidisch)
- Strategie 3: solo-cluster voor signalen zonder geometrie/pand

### Pipeline runner (`apps/worker/src/pipelines/pipeline_runner.py`) ✅
- Orkestreert: adapter → DB upsert → clusterer → predictor → DB insert
- Laadt ook bestaande DB-signalen voor clustervorming
- Links signals ↔ projects via `pipeline_project_signals`

### CLI inspect tool (`apps/worker/src/cli/inspect.py`) ✅
- `python -m src.cli.inspect postcode 1053KS` — postcode-inspectie
- `python -m src.cli.inspect top 30` — top-N projecten op sloop_kans
- `python -m src.cli.inspect top --gemeente Amsterdam` — per gemeente

---

## Resultaten eerste run (90 dagen)

| Metric | Waarde |
|--------|--------|
| Adapter | `koop_sloopmelding` |
| Lookback | 90 dagen |
| Raw signalen | 513 |
| Parsed signalen | 513 |
| Clusters | 490 |
| Projecten opgeslagen (kans ≥ 10%) | **490** |
| Doel | 200+ ✅ |

### Top-5 projecten
| Rang | Gemeente | Adres | Kans | Horizon |
|------|----------|-------|------|---------|
| 1 | Haarlem | Vondelweg 364A-RD | 99% | 1–6m |
| 2 | Amsterdam | Van Limburg Stirumstraat 22N | 99% | 1–6m |
| 3 | Huizen | Van Limburg Stirumstraat 1 | 94% | 1–6m |
| 4 | Moerdijk | Zuidelijke Randweg 4-W | 83% | 1–6m |
| 5 | Oldambt | Burgemeester Schönfeldplein 2A | 83% | 1–6m |

---

## Bekende issues / openstaand

1. **Ruimtelijkeplannen WFS offline** — `service.pdok.nl/kadaster/plannen/wfs/v1_0` geeft 404. Dit lijkt een migratieprobleem van PDOK. Workaround: `koop_sloopmelding_adapter` als Bron 1b. Correcte URL onderzoeken in Fase B.

2. **pipeline_projects heeft geen UNIQUE op bag_pand_id** — Herhaald draaien van de pipeline creëert duplicaten. Fix: nieuwe migration met `ALTER TABLE pipeline_projects ADD CONSTRAINT uq_pand UNIQUE (bag_pand_id)`.

3. **Alleen 1 signaaltype** — Alle 490 projecten hebben slechts 1 signaal (`sloopmelding`). Diversiteitsbonus werkt pas zodra er meerdere bronnen zijn (Fase B/C). Kansen liggen nu voornamelijk op 53% of 83%/99% (seed-data heeft andere scoring).

4. **Kadaster adapter** — Uitgeschakeld via `KADASTER_ENABLED=false`. Activeer zodra API-key beschikbaar is.

---

## Volgende stap: STOP voor inspectie

Joran kan nu inspecteren:
```bash
cd apps/worker
poetry run python -m src.cli.inspect top 30
poetry run python -m src.cli.inspect top 30 --gemeente Amsterdam
poetry run python -m src.cli.inspect postcode 3032AK
```

Na akkoord → Fase B: 4 extra adapters + PDOK WFS endpoint fix.
