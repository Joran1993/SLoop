"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export function LoginForm() {
  const supabase = createClient();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"password" | "magic">("password");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (mode === "password") {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      setLoading(false);
      if (error) {
        setError(error.message);
      } else {
        router.push("/dashboard");
        router.refresh();
      }
    } else {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
      });
      setLoading(false);
      if (error) {
        setError(error.message);
      } else {
        setSent(true);
      }
    }
  }

  if (sent) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-center space-y-2">
        <p className="font-medium text-sm">Controleer uw inbox</p>
        <p className="text-sm text-muted-foreground">
          We hebben een inloglink gestuurd naar{" "}
          <span className="font-medium text-foreground">{email}</span>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-border bg-card p-6 space-y-4">
      <div className="space-y-1.5">
        <label htmlFor="email" className="text-sm font-medium leading-none">
          E-mailadres
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="u@bedrijf.nl"
          className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </div>

      {mode === "password" && (
        <div className="space-y-1.5">
          <label htmlFor="password" className="text-sm font-medium leading-none">
            Wachtwoord
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="inline-flex w-full items-center justify-center rounded-md bg-primary px-4 h-9 text-sm font-medium text-primary-foreground shadow transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
      >
        {loading ? "Bezig…" : mode === "password" ? "Inloggen" : "Stuur inloglink"}
      </button>

      <button
        type="button"
        onClick={() => { setMode(mode === "password" ? "magic" : "password"); setError(null); }}
        className="w-full text-center text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {mode === "password" ? "Inloggen via e-maillink" : "Inloggen met wachtwoord"}
      </button>
    </form>
  );
}
