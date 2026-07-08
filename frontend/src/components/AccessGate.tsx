import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getAppConfig } from "@/lib/api";
import { isHostedApi, setAccessPassword, clearAccessPassword, getAccessPassword } from "@/lib/auth";

type AccessGateProps = {
  children: React.ReactNode;
};

export function AccessGate({ children }: AccessGateProps) {
  const [unlocked, setUnlocked] = useState(!isHostedApi());
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isHostedApi() || !getAccessPassword()) return;
    getAppConfig()
      .then(() => setUnlocked(true))
      .catch(() => clearAccessPassword());
  }, []);

  if (unlocked) return children;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setAccessPassword(password);
    try {
      await getAppConfig();
      setUnlocked(true);
    } catch {
      clearAccessPassword();
      setError("Invalid access password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mesh-gradient flex min-h-svh items-center justify-center px-6">
      <form
        onSubmit={submit}
        className="w-full max-w-md space-y-4 rounded-xl border border-border bg-card p-8 shadow-lg"
      >
        <div className="space-y-1">
          <h1 className="text-xl font-black tracking-tighter text-primary">OCE</h1>
          <p className="text-sm text-muted-foreground">
            Enter the demo access password to connect to the hosted API.
          </p>
        </div>
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Access password"
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={busy || !password}>
          {busy ? "Connecting…" : "Enter"}
        </Button>
      </form>
    </div>
  );
}
