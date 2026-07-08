import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EvidenceChip } from "@/components/dossier/EvidenceChip";
import { PatternPanel } from "@/components/dossier/PatternPanel";
import { SourceProvider } from "@/components/source/SourceViewer";
import {
  createDossier,
  ensureExecutiveSummary,
  getAppConfig,
  type AppConfig,
  type DossierResponse,
  type SharedContext,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Cause = {
  statement: string;
  mechanism_explanation?: string;
  evidence_ids?: string[];
  grounding?: string;
  strength_tier?: string | null;
};

type SafetyNote = { text: string; evidence_ids?: string[] };
type Action = { text: string; rationale?: string; evidence_ids?: string[] };

const SYMPTOM_LABEL: Record<string, string> = {
  seal_leak: "Seal Leak",
  vibration: "Elevated Vibration",
  overheating: "Overheating",
};

function collectCitedIds(ctx: SharedContext, sections: Record<string, unknown> | null): string[] {
  const ids = new Set<string>();
  if (!sections) return [];
  for (const key of ["probable_causes", "safety_notes", "actions"] as const) {
    for (const item of (sections[key] as { evidence_ids?: string[] }[]) ?? []) {
      for (const id of item.evidence_ids ?? []) ids.add(id);
    }
  }
  const pool = new Set(ctx.evidence_pool);
  return [...ids].filter((id) => pool.has(id)).sort();
}

function chunkMeta(ctx: SharedContext, citationId: string): { title: string; page: number; section: string | null } | null {
  const all = [...ctx.manual_chunks, ...ctx.sop_chunks, ...ctx.report_chunks];
  const hit = all.find((c) => c.citation_id === citationId);
  if (!hit) return null;
  const kind = ctx.manual_chunks.some((c) => c.citation_id === citationId)
    ? "Manual"
    : ctx.sop_chunks.some((c) => c.citation_id === citationId)
      ? "SOP"
      : "Report";
  return { title: kind, page: hit.page, section: hit.section_ref };
}

/**
 * FR-10 — print-friendly incident report from persisted sections (D-019).
 * Zero LLM calls; browser print is the shareable artifact.
 */
export function ReportView() {
  const { id } = useParams<{ id: string }>();
  const [dossier, setDossier] = useState<DossierResponse | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id == null) return;
    let cancelled = false;
    Promise.all([createDossier(id), getAppConfig()])
      .then(async ([d, c]) => {
        if (cancelled) return;
        let dossier = d;
        const secs = d.sections as Record<string, unknown> | null;
        if (d.sections && !secs?.executive_summary) {
          try {
            dossier = await ensureExecutiveSummary(d.dossier_id);
          } catch {
            /* graceful absence — facts block still renders */
          }
        }
        if (!cancelled) {
          setDossier(dossier);
          setConfig(c);
        }
      })
      .catch(() => !cancelled && setError("Could not load report."));
    return () => {
      cancelled = true;
    };
  }, [id]);

  const ctx = dossier?.context ?? null;
  const sections = (dossier?.sections ?? null) as Record<string, unknown> | null;
  const causes = (sections?.probable_causes as Cause[]) ?? [];
  const safety = (sections?.safety_notes as SafetyNote[]) ?? [];
  const actions = (sections?.actions as Action[]) ?? [];

  if (error) {
    return (
      <div className="report-root p-8 text-destructive">{error}</div>
    );
  }

  if (!ctx || !sections) {
    return (
      <div className="report-root p-8 text-muted-foreground">Loading report…</div>
    );
  }

  const cited = collectCitedIds(ctx, sections);
  const event = ctx.event;
  const asset = ctx.asset_profile;
  const executiveSummary =
    typeof sections.executive_summary === "string" ? sections.executive_summary : null;

  return (
    <SourceProvider>
      <div className="report-root min-h-screen bg-white text-slate-900 print:bg-white">
        <style>{`
          @media print {
            .no-print { display: none !important; }
            .report-root { font-size: 11pt; }
          }
        `}</style>

        <header className="border-b border-slate-200 px-8 py-6 print:px-0">
          <div className="no-print mb-4 flex gap-3">
            <Link to={`/events/${id}`} className="text-sm text-slate-600 underline">
              ← Back to dossier
            </Link>
            <button
              type="button"
              onClick={() => window.print()}
              className="rounded border border-slate-300 px-3 py-1 text-sm"
            >
              Print report
            </button>
          </div>
          <h1 className="text-2xl font-bold">
            Incident Report — {asset.tag} · {SYMPTOM_LABEL[event.symptom_category] ?? event.symptom_category}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {asset.plant} / {asset.unit} / {asset.area} · Criticality {event.criticality} ·{" "}
            {new Date(event.occurred_at).toLocaleString()}
          </p>
        </header>

        <main className="mx-auto max-w-4xl space-y-8 px-8 py-8 print:px-0">
          {executiveSummary && (
            <section>
              <h2 className="mb-2 text-sm font-bold uppercase tracking-widest text-slate-500">
                AI summary of validated findings
              </h2>
              <p className="text-sm leading-relaxed text-slate-800">{executiveSummary}</p>
            </section>
          )}

          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
              Executive facts
            </h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Asset</dt>
                <dd className="font-medium">{asset.tag} — {asset.name}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Class</dt>
                <dd>{asset.asset_class}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Duty</dt>
                <dd>{asset.service_duty}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Operator note</dt>
                <dd>{event.note ?? "—"}</dd>
              </div>
            </dl>
          </section>

          {safety.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-amber-700">
                Safety notes
              </h2>
              <ul className="space-y-2">
                {safety.map((n, i) => (
                  <li key={i} className="rounded border border-amber-200 bg-amber-50 p-3 text-sm">
                    {n.text}
                    {n.evidence_ids && n.evidence_ids.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {n.evidence_ids.map((cid) => (
                          <EvidenceChip key={cid} citation={cid} />
                        ))}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {causes.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
                Probable causes
              </h2>
              <div className="space-y-3">
                {causes.map((c, i) => (
                  <div
                    key={i}
                    className={cn(
                      "rounded border p-3 text-sm",
                      c.grounding === "hypothesis" ? "border-dashed border-slate-400" : "border-slate-200",
                    )}
                  >
                    <div className="flex justify-between gap-2">
                      <strong>{c.statement}</strong>
                      {c.strength_tier && (
                        <span className="text-xs uppercase text-slate-500">{c.strength_tier}</span>
                      )}
                    </div>
                    {c.mechanism_explanation && (
                      <p className="mt-1 text-slate-600">{c.mechanism_explanation}</p>
                    )}
                    {c.evidence_ids && c.evidence_ids.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {c.evidence_ids.map((cid) => (
                          <EvidenceChip key={cid} citation={cid} />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {actions.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
                Recommended actions
              </h2>
              <ol className="list-decimal space-y-2 pl-5 text-sm">
                {actions.map((a, i) => (
                  <li key={i}>
                    <strong>{a.text}</strong>
                    {a.rationale && <span className="text-slate-600"> — {a.rationale}</span>}
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className="print:break-before-page">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
              Cross-asset patterns
            </h2>
            <PatternPanel patterns={ctx.pattern_stats} config={config} />
          </section>

          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-widest text-slate-500">
              Evidence appendix
            </h2>
            <ul className="space-y-2 text-sm">
              {cited.map((cid) => {
                if (cid.startsWith("CH-")) {
                  const meta = chunkMeta(ctx, cid);
                  return (
                    <li key={cid} className="border-b border-slate-100 pb-2">
                      <EvidenceChip citation={cid} />
                      {meta && (
                        <span className="ml-2 text-slate-600">
                          {meta.title} p{meta.page}
                          {meta.section ? ` · ${meta.section}` : ""}
                        </span>
                      )}
                    </li>
                  );
                }
                return (
                  <li key={cid} className="border-b border-slate-100 pb-2">
                    <EvidenceChip citation={cid} />
                    <span className="ml-2 text-slate-600">Work order record</span>
                  </li>
                );
              })}
            </ul>
          </section>
        </main>
      </div>
    </SourceProvider>
  );
}
