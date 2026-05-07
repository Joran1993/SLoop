# Sloopradar — Build Log

## Fase 0 — Setup (07-05-2026)

### Gebouwd
- Monorepo opgezet met pnpm workspaces
- `apps/web`: Next.js 16 + TypeScript + Tailwind + shadcn/ui (button, table, card, badge, select, separator, dialog, sheet)
- `apps/api`: FastAPI + Poetry (Python 3.11), inclusief config, CORS middleware, slowapi rate-limiting skeleton
- `apps/worker`: Poetry project, bestaande `sru_pull.py` opgenomen als `src/sources/koop.py`
- `packages/shared-types`: TypeScript types (PlanTier, LeadFilters, etc.), klaar voor Supabase type-generatie
- `packages/db/supabase`: Supabase CLI geïnitialiseerd, migrations-map leeg (Fase 1)
- `.env.example` voor alle services
- GitHub Actions CI: web (lint+typecheck+build), api (ruff+mypy), worker (ruff+pytest)

### Beslissingen
- **Python 3.11** i.p.v. 3.12: 3.12 niet beschikbaar via Homebrew, 3.11 is productie-stabiel en volledig compatibel. Aanpassen als 3.12 nodig blijkt.
- **Next.js 16** i.p.v. 14: `create-next-app` installeert de nieuwste versie (16). App Router werkt identiek. Geen regressie.
- **Poetry geïnstalleerd via pip op Python 3.11** (officiële installer had SSL-probleem op dit systeem).

### Open vragen voor Joran (blokkeren Fase 1/5)
1. **Domein**: sloopradar.nl, bouwsignaal.nl, of onder cirqo.nl?
2. **Facturerende entiteit**: WWIZ B.V., CircuBouw, of andere?
3. **Mollie**: account al aangemaakt?
4. **BAG API-key**: al aangevraagd bij Kadaster? (aanvragen: kadaster.nl → BAG Individuele Bevragingen)
5. **AVG/privacy**: tonen we eigenaarsnamen bij particuliere panden? Voorstel: nee — alleen pand+adres.
6. **Pre-launch waitlist**: wil je al een landingspagina met email-capture vóór Fase 7?

### Openstaand na Fase 0
- Supabase remote project aanmaken (Joran doet dit zelf via supabase.com dashboard)
- Supabase lokaal opstarten: `supabase start` in `packages/db/`
- GitHub repo aanmaken + pushen (Joran)

---
