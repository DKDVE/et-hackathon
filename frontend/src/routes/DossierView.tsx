import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FileText, MessageSquare } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { DossierBreadcrumb } from "@/components/layout/DossierBreadcrumb";
import { ChatDrawer } from "@/components/dossier/ChatDrawer";
import { DossierHero } from "@/components/dossier/DossierHero";
import { AssetProfileCard } from "@/components/dossier/AssetProfileCard";
import { ExtractCards } from "@/components/dossier/ExtractCards";
import { FailureTimeline } from "@/components/dossier/FailureTimeline";
import { LockedReasoning } from "@/components/dossier/LockedReasoning";
import { ReasoningSections } from "@/components/dossier/ReasoningSections";
import { PatternPanel } from "@/components/dossier/PatternPanel";
import { SimilarIncidents } from "@/components/dossier/SimilarIncidents";
import { TracePanel } from "@/components/dossier/TracePanel";
import { SourceProvider } from "@/components/source/SourceViewer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  createDossier,
  getAppConfig,
  getDossierRuns,
  type AppConfig,
  type DossierResponse,
  type ReasoningRunsResponse,
} from "@/lib/api";
import { isContextReady, useDossierStream } from "@/lib/dossierStream";

type DossierTab = "dossier" | "trace";

export function DossierView() {
  const { id } = useParams<{ id: string }>();
  const eventId = id ?? "—";

  const [dossierId, setDossierId] = useState<number | null>(null);
  const [initial, setInitial] = useState<DossierResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [tab, setTab] = useState<DossierTab>("dossier");
  const [trace, setTrace] = useState<ReasoningRunsResponse | null>(null);

  useEffect(() => {
    getAppConfig().then(setConfig).catch(() => {
      /* ponytail: panel falls back to default cost */
    });
  }, []);

  // POST the dossier (idempotent) to assemble it, then stream it.
  useEffect(() => {
    if (id == null) return;
    let cancelled = false;
    createDossier(id)
      .then((d) => {
        if (cancelled) return;
        setInitial(d);
        setDossierId(d.dossier_id);
      })
      .catch(() => !cancelled && setError("Could not assemble the dossier."));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const stream = useDossierStream(dossierId);
  const dossier = isContextReady(stream) ? stream.dossier : initial;
  const degraded = stream.degraded ?? dossier?.degraded ?? null;
  const ctx = dossier?.context ?? null;
  const reasoningEnabled = dossier?.reasoning_enabled ?? false;
  const reasoningPending =
    reasoningEnabled && !degraded && stream.analysis == null && stream.validated == null;
  const isComplete = dossier?.status === "complete" && dossier.sections != null;
  const showTraceTab =
    isComplete && (trace != null && (trace.runs.length > 0 || !reasoningEnabled));

  useEffect(() => {
    if (dossierId == null || !isComplete) return;
    let cancelled = false;
    getDossierRuns(dossierId)
      .then((t) => !cancelled && setTrace(t))
      .catch(() => {
        /* ponytail: trace tab stays hidden on fetch failure */
      });
    return () => {
      cancelled = true;
    };
  }, [dossierId, isComplete]);

  return (
    <SourceProvider>
      <AppShell breadcrumb={<DossierBreadcrumb eventId={eventId} />}>
        <DossierHero context={ctx} degraded={degraded} />

        {error && (
          <div className="rounded border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {!ctx && !error && (
          <div className="py-24 text-center text-sm text-muted-foreground">
            Assembling operational context…
          </div>
        )}

        {ctx && (
          <div className="grid grid-cols-1 gap-10 pb-16 lg:grid-cols-12">
            <div className="flex flex-col gap-10 lg:col-span-8">
              <div className="flex flex-wrap items-center gap-3 no-print">
                {showTraceTab && (
                  <div className="flex gap-2">
                    {(
                      [
                        ["dossier", "Dossier"],
                        ["trace", "Trace"],
                      ] as const
                    ).map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setTab(value)}
                        className={cn(
                          "rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-all",
                          tab === value
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-muted-foreground hover:text-foreground",
                        )}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                )}
                {isComplete && id && (
                  <Link
                    to={`/events/${id}/report`}
                    className="inline-flex h-8 items-center rounded-md border border-border bg-background px-3 text-sm font-medium hover:bg-muted"
                  >
                    <FileText className="mr-2 size-4" />
                    Open report
                  </Link>
                )}
                {isComplete && dossierId != null && (
                  <Button variant="outline" size="sm" onClick={() => setChatOpen(true)}>
                    <MessageSquare className="mr-2 size-4" />
                    Ask about this dossier
                  </Button>
                )}
              </div>

              {tab === "trace" && trace ? (
                <TracePanel trace={trace} />
              ) : (
                <>
                  {reasoningEnabled ? (
                    <>
                      {reasoningPending && <LockedReasoning degraded={null} />}
                      <ReasoningSections stream={stream} degraded={degraded} />
                    </>
                  ) : (
                    <LockedReasoning degraded={degraded} />
                  )}
                  <PatternPanel patterns={ctx.pattern_stats} config={config} />
                  <FailureTimeline history={ctx.failure_history} />
                  <SimilarIncidents incidents={ctx.sister_incidents} />
                </>
              )}
            </div>
            <aside className="flex flex-col gap-8 lg:col-span-4">
              <AssetProfileCard profile={ctx.asset_profile} />
              <ExtractCards title="Manual Extracts" chunks={ctx.manual_chunks} />
              <ExtractCards title="SOP Extracts" chunks={ctx.sop_chunks} />
              <ExtractCards title="Report Extracts" chunks={ctx.report_chunks} />
            </aside>
          </div>
        )}

        {dossierId != null && isComplete && (
          <ChatDrawer dossierId={dossierId} open={chatOpen} onClose={() => setChatOpen(false)} />
        )}
      </AppShell>
    </SourceProvider>
  );
}
