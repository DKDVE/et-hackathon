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
import { SourceProvider } from "@/components/source/SourceViewer";
import { Button } from "@/components/ui/button";
import { createDossier, getAppConfig, type AppConfig, type DossierResponse } from "@/lib/api";
import { isContextReady, useDossierStream } from "@/lib/dossierStream";

export function DossierView() {
  const { id } = useParams<{ id: string }>();
  const eventId = id ?? "—";

  const [dossierId, setDossierId] = useState<number | null>(null);
  const [initial, setInitial] = useState<DossierResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

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
              <div className="flex flex-wrap gap-3 no-print">
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
