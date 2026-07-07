import { Lock, Sparkles } from "lucide-react";

import type { DegradedInfo } from "@/lib/api";

/**
 * The AI-dependent sections (Safety Notes, Probable Causes, Recommended Actions,
 * chat) collapse into a single honest row when the stream ends
 * degraded{reasoning_disabled}. Never fake content, never a blank gap (P3/P5).
 */
export function LockedReasoning({ degraded }: { degraded: DegradedInfo | null }) {
  const reasonLabel: Record<string, string> = {
    reasoning_disabled: "Reasoning layer: not enabled",
    llm_failure: "Reasoning layer: unavailable (LLM failure)",
    node_failure: "Reasoning layer: unavailable (node failure)",
  };
  const label = degraded ? reasonLabel[degraded.reason] ?? "Reasoning layer: not enabled" : null;

  if (!degraded) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-primary/20 bg-primary/5 px-5 py-3">
        <Sparkles className="size-4 shrink-0 animate-pulse text-primary" />
        <span className="text-sm font-medium text-primary">Assembling context…</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-card/40 px-5 py-3">
      <Lock className="size-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0">
        <span className="text-sm font-semibold text-muted-foreground">{label}</span>
        <span className="ml-2 text-xs text-muted-foreground/70">
          Safety notes, probable causes, recommended actions and chat activate with the
          reasoning layer.
        </span>
      </div>
    </div>
  );
}
