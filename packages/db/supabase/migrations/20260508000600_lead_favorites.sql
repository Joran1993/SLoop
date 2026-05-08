-- Opgeslagen leads (favorieten) per gebruiker

CREATE TABLE IF NOT EXISTS public.lead_favorites (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  lead_id    uuid NOT NULL REFERENCES public.sloop_leads(id) ON DELETE CASCADE,
  note       text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, lead_id)
);

ALTER TABLE public.lead_favorites ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own favorites"
  ON public.lead_favorites FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_lead_favorites_user_id ON public.lead_favorites(user_id);
CREATE INDEX idx_lead_favorites_lead_id ON public.lead_favorites(lead_id);
