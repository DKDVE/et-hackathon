import { FileText } from "lucide-react";

import type { ChunkRecord } from "@/lib/api";
import { EvidenceChip } from "./EvidenceChip";

/**
 * Manual / SOP / Report extract cards. Each shows its section_ref + page and an
 * evidence chip that deep-links to the exact cited page in the SourceViewer.
 */
export function ExtractCards({
  title,
  chunks,
}: {
  title: string;
  chunks: ChunkRecord[];
}) {
  if (chunks.length === 0) return null;
  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <FileText className="size-4 text-muted-foreground" />
        <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          {title}
        </h3>
      </div>
      <div className="space-y-3">
        {chunks.map((c) => (
          <div key={c.chunk_id} className="rounded border border-border bg-card/50 p-3">
            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
              <span className="truncate text-xs font-semibold text-foreground">
                {c.section_ref ?? "—"}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  p{c.page}
                </span>
                <EvidenceChip citation={c.citation_id} />
              </div>
            </div>
            <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
              {c.content}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
