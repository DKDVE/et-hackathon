import { GitBranch } from "lucide-react";

import type { SisterIncident } from "@/lib/api";
import { EvidenceChip } from "./EvidenceChip";
import { SectionLabel } from "./SectionLabel";

export function SimilarIncidents({ incidents }: { incidents: SisterIncident[] }) {
  return (
    <section>
      <SectionLabel icon={GitBranch} label="Similar Incidents" />
      {incidents.length === 0 ? (
        <p className="rounded border border-dashed border-border bg-card/40 p-4 text-sm text-muted-foreground">
          No sister-asset incidents for this symptom.
        </p>
      ) : (
        <div className="space-y-3">
          {incidents.map((si) => (
            <div key={si.wo_number} className="rounded border border-border bg-card/50 p-4">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold tabular-nums">{si.asset_tag}</span>
                <span className="text-xs text-muted-foreground">{si.asset_name}</span>
                <EvidenceChip citation={si.citation_id} />
                {si.failure_mode_code && (
                  <span className="text-xs text-muted-foreground">
                    {si.failure_mode_code.replace(/_/g, " ")}
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground">{si.raw_description}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
