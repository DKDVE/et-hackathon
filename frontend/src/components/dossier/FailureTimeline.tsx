import { History } from "lucide-react";

import type { WorkOrderRecord } from "@/lib/api";
import { EvidenceChip } from "./EvidenceChip";
import { SectionLabel } from "./SectionLabel";

export function FailureTimeline({ history }: { history: WorkOrderRecord[] }) {
  return (
    <section>
      <SectionLabel icon={History} label="Failure History" />
      {history.length === 0 ? (
        <p className="rounded border border-dashed border-border bg-card/40 p-4 text-sm text-muted-foreground">
          No prior failures recorded for this asset.
        </p>
      ) : (
        <div className="relative ml-3 space-y-6 border-l border-border pl-8">
          {history.map((wo) => (
            <div key={wo.wo_number} className="relative">
              <div className="absolute -left-[2.35rem] top-1 size-4 rounded-full border-2 border-primary/40 bg-card" />
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold tabular-nums">{wo.opened_on}</span>
                <EvidenceChip citation={wo.citation_id} />
                {wo.failure_mode_code && (
                  <span className="text-xs text-muted-foreground">
                    {wo.failure_mode_code.replace(/_/g, " ")}
                  </span>
                )}
                {wo.downtime_hours != null && (
                  <span className="text-xs tabular-nums text-muted-foreground">
                    · {wo.downtime_hours}h downtime
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground">{wo.raw_description}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
