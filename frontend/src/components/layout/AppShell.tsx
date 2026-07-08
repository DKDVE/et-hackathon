import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { cn } from "@/lib/utils";
import { getHealth } from "@/lib/api";

const navItems = [
  { to: "/events", label: "Events" },
  { to: "/assets", label: "Assets" },
  { to: "/ops", label: "Operations" },
] as const;

type AppShellProps = {
  children: React.ReactNode;
  breadcrumb?: React.ReactNode;
};

export function AppShell({ children, breadcrumb }: AppShellProps) {
  const location = useLocation();
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  useEffect(() => {
    getHealth()
      .then((h) => setApiOk(h.db === "ok"))
      .catch(() => setApiOk(false));
  }, []);

  return (
    <div className="mesh-gradient flex min-h-svh flex-col selection:bg-primary/30">
      <header className="sticky top-0 z-50 border-b border-border bg-card">
        <div className="mx-auto flex h-16 w-full max-w-[90rem] items-center justify-between px-6">
          <div className="flex items-center gap-8">
            <Link to="/events" className="text-xl font-black tracking-tighter text-primary">
              OCE
            </Link>
            <nav className="hidden items-center gap-6 md:flex">
              {navItems.map(({ to, label }) => {
                const active = location.pathname.startsWith(to);
                return (
                  <Link
                    key={to}
                    to={to}
                    className={cn(
                      "pb-2 text-sm font-medium tracking-tight tabular-nums transition-colors",
                      active
                        ? "border-b-2 border-primary text-primary"
                        : "text-muted-foreground hover:text-primary",
                    )}
                  >
                    {label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <div
              className={cn(
                "flex items-center gap-2 rounded-full border px-2.5 py-1",
                apiOk
                  ? "border-emerald-500/20 bg-emerald-500/10"
                  : "border-destructive/20 bg-destructive/10",
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  apiOk ? "animate-pulse bg-emerald-500" : "bg-destructive",
                )}
              />
              <span
                className={cn(
                  "text-[10px] font-bold uppercase tracking-widest",
                  apiOk ? "text-emerald-500" : "text-destructive",
                )}
              >
                {apiOk === null ? "…" : apiOk ? "API Connected" : "API Offline"}
              </span>
            </div>
          </div>
        </div>
      </header>

      {breadcrumb}

      <main className="mx-auto w-full max-w-[90rem] flex-1 px-6 py-10">{children}</main>

      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-[20%] -right-[10%] h-[60%] w-[60%] rounded-full bg-primary/5 blur-[120px]" />
        <div className="absolute -bottom-[10%] -left-[10%] h-[40%] w-[40%] rounded-full bg-muted/20 blur-[100px]" />
      </div>

      <footer className="mt-auto border-t border-border bg-card">
        <div className="mx-auto flex w-full max-w-[90rem] flex-col items-center justify-between gap-4 px-6 py-8 text-[10px] font-bold uppercase tracking-widest text-muted-foreground md:flex-row">
          <div>Meridian Specialty Chemicals · Unit 3</div>
          <div className="flex flex-wrap justify-center gap-6">
            <span>Facility: Houston Southeast Plant</span>
            <span>Meridian Specialty Chemicals</span>
          </div>
          <div>© 2026 OCE — Industrial Decision Intelligence</div>
        </div>
      </footer>
    </div>
  );
}
