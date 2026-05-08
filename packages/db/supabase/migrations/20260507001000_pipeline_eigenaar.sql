-- Voeg eigenaar kolommen toe aan pipeline_signals
ALTER TABLE pipeline_signals
  ADD COLUMN IF NOT EXISTS eigenaar_type text DEFAULT 'onbekend',
  ADD COLUMN IF NOT EXISTS eigenaar_naam text;

-- Voeg ook eigenaar toe aan pipeline_projects voor snelle weergave in dashboard
ALTER TABLE pipeline_projects
  ADD COLUMN IF NOT EXISTS eigenaar_type text DEFAULT 'onbekend',
  ADD COLUMN IF NOT EXISTS eigenaar_naam text;
