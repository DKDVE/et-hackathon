import { AlertTriangle, FileText, ListChecks, Sparkles } from "lucide-react";

import { EvidenceChip } from "@/components/dossier/EvidenceChip";
import { SectionLabel } from "@/components/dossier/SectionLabel";
import type { DegradedInfo } from "@/lib/api";
import type { DossierState } from "@/lib/dossierStream";
import { cn } from "@/lib/utils";

type Cause = {
  statement: string;
  mechanism_explanation?: string;
  asset_specific_notes?: string | null;
  evidence_ids?: string[];
  grounding?: "evidenced" | "hypothesis";
  strength_tier?: string | null;
  claim_ref?: string;
};

type SafetyNote = { text: string; evidence_ids?: string[]; grounding?: string };
type Action = {
  text: string;
  rationale?: string;
  evidence_ids?: string[];
  sop_refs?: string[];
  grounding?: string;
};

function isCached(payload: unknown): boolean {
  return Boolean(payload && typeof payload === "object" && (payload as { cached?: boolean }).cached);
}

function mergeCauses(stream: DossierState): Cause[] {
  const validated = stream.validated as { probable_causes?: Cause[] } | null;
  const analysis = stream.analysis as { probable_causes?: Cause[] } | null;
  if (validated?.probable_causes?.length) return validated.probable_causes;
  return analysis?.probable_causes ?? [];
}

function mergeSafety(stream: DossierState): SafetyNote[] {
  const validated = stream.validated as { safety_notes?: SafetyNote[] } | null;
  const rec = stream.recommendation as { safety_notes?: SafetyNote[] } | null;
  if (validated?.safety_notes?.length) return validated.safety_notes;
  return rec?.safety_notes ?? [];
}

function mergeActions(stream: DossierState): Action[] {
  const validated = stream.validated as { actions?: Action[] } | null;
  const rec = stream.recommendation as { actions?: Action[] } | null;
  if (validated?.actions?.length) return validated.actions;
  return rec?.actions ?? [];
}

function StrengthBadge({ tier }: { tier?: string | null }) {
  if (!tier) return null;
  const colors: Record<string, string> = {
    Strong: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
    Moderate: "border-amber-500/40 bg-amber-500/10 text-amber-400",
    Weak: "border-slate-500/40 bg-slate-500/10 text-slate-400",
  };
  return (
    <span
      className={cn(
        "rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
        colors[tier] ?? colors.Weak,
      )}
    >
      {tier}
    </span>
  );
}

function ClaimCard({
  children,
  grounding,
  className,
}: {
  children: React.ReactNode;
  grounding?: string;
  className?: string;
}) {
  const hypothesis = grounding === "hypothesis";
  return (
    <div
      className={cn(
        "rounded-lg border bg-card/50 p-4 transition-all duration-300",
        hypothesis ? "border-dashed border-muted-foreground/40" : "border-border",
        className,
      )}
    >
      {hypothesis && (
        <span className="mb-2 inline-block text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Hypothesis
        </span>
      )}
      {children}
    </div>
  );
}

/**
 * Progressive AI sections: provisional analysis/recommendation refine into
 * validated payloads without flashing away (M6 Task 5).
 */
export function ReasoningSections({
  stream,
  degraded,
}: {
  stream: DossierState;
  degraded: DegradedInfo | null;
}) {
  if (degraded) return null;

  const hasReasoning =
    stream.analysis != null || stream.recommendation != null || stream.validated != null;
  if (!hasReasoning) return null;

  const causes = mergeCauses(stream);
  const safety = mergeSafety(stream);
  const actions = mergeActions(stream);
  const cached =
    isCached(stream.analysis) || isCached(stream.recommendation) || isCached(stream.validated);

  return (
    <div className="flex flex-col gap-8">
      {cached && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Sparkles className="size-3.5 text-primary" />
          Cached reasoning replay
        </div>
      )}

      {safety.length > 0 && (
        <section>
          <SectionLabel icon={AlertTriangle} label="Safety Notes" />
          <div className="mt-3 flex flex-col gap-3">
            {safety.map((n, i) => (
              <div
                key={n.text.slice(0, 24) + i}
                className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100"
              >
                <p>{n.text}</p>
                {n.evidence_ids && n.evidence_ids.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {n.evidence_ids.map((id) => (
                      <EvidenceChip key={id} citation={id} />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {causes.length > 0 && (
        <section>
          <SectionLabel icon={FileText} label="Probable Causes" />
          <div className="mt-3 flex flex-col gap-3">
            {causes.map((c, i) => (
              <ClaimCard key={c.claim_ref ?? i} grounding={c.grounding}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-foreground">{c.statement}</h3>
                  <StrengthBadge tier={c.strength_tier} />
                </div>
                {c.mechanism_explanation && (
                  <p className="mt-2 text-sm text-muted-foreground">{c.mechanism_explanation}</p>
                )}
                {c.asset_specific_notes && (
                  <p className="mt-1 text-xs text-muted-foreground/80">{c.asset_specific_notes}</p>
                )}
                {c.evidence_ids && c.evidence_ids.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {c.evidence_ids.map((id) => (
                      <EvidenceChip key={id} citation={id} />
                    ))}
                  </div>
                )}
              </ClaimCard>
            ))}
          </div>
        </section>
      )}

      {actions.length > 0 && (
        <section>
          <SectionLabel icon={ListChecks} label="Recommended Actions" />
          <div className="mt-3 flex flex-col gap-3">
            {actions.map((a, i) => (
              <ClaimCard key={a.text.slice(0, 24) + i} grounding={a.grounding}>
                <p className="text-sm font-medium text-foreground">{a.text}</p>
                {a.rationale && (
                  <p className="mt-1 text-sm text-muted-foreground">{a.rationale}</p>
                )}
                {a.evidence_ids && a.evidence_ids.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {a.evidence_ids.map((id) => (
                      <EvidenceChip key={id} citation={id} />
                    ))}
                  </div>
                )}
                {a.sop_refs && a.sop_refs.length > 0 && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    SOP: {a.sop_refs.join("; ")}
                  </p>
                )}
              </ClaimCard>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
