import { LoginForm } from "./login-form";
import { Building2 } from "lucide-react";

export const metadata = { title: "Inloggen — Sloopradar" };

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm space-y-8">
        <div className="flex flex-col items-center gap-2">
          <Building2 className="h-8 w-8 text-accent" strokeWidth={1.75} />
          <h1 className="text-xl font-semibold tracking-tight">Sloopradar</h1>
          <p className="text-sm text-muted-foreground">
            Log in met uw e-mailadres
          </p>
        </div>
        <LoginForm />
      </div>
    </div>
  );
}
