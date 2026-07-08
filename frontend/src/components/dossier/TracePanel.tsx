import { Activity } from "lucide-react";

import {
  CostRollupCards,
  TraceRunTable,
  formatUsd,
} from "@/components/ops/TraceRunTable";
import type { ReasoningRunsResponse } from "@/lib/api";

function TraceHeader() {
  return (
    <div className="mb-5 flex items-center gap-2 text-primary">
      <Activity className="size-4" />
      <h2 className="text-xs font-bold uppercase tracking-widest">Reasoning Trace</h2>
    </div>
  );
}

export function TracePanel({ trace }: { trace: ReasoningRunsResponse }) {
  if (trace.runs.length === 0) {
    return (
      <section className="rounded-lg border border-border bg-card/40 p-6">
        <TraceHeader />
        <p className="text-sm text-muted-foreground">
          No reasoning runs — deterministic dossier.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-card/40 p-6">
      <TraceHeader />
      {trace.replayed_from_cache && (
        <p className="mb-4 text-xs text-amber-500/90">
          Replayed from cache — rows reflect the original live reasoning run.
        </p>
      )}
      <TraceRunTable runs={trace.runs} />
      <div className="mt-4 flex flex-wrap gap-6 text-sm">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Total latency
          </div>
          <div className="tabular-nums">{trace.total_latency_ms} ms</div>
        </div>
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Total tokens
          </div>
          <div className="tabular-nums">
            {trace.total_prompt_tokens + trace.total_completion_tokens}
          </div>
        </div>
        <div>
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Est. cost
          </div>
          <div className="font-semibold text-primary tabular-nums">
            {formatUsd(trace.estimated_cost_usd)}
          </div>
        </div>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">{trace.cost_footnote}</p>
    </section>
  );
}

export { CostRollupCards, TraceRunTable };
