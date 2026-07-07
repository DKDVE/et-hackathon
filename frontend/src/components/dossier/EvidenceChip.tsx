import { FileText, Wrench } from "lucide-react";

import { cn } from "@/lib/utils";
import { useSourceViewer } from "@/components/source/SourceViewer";

/**
 * A clickable evidence citation (`WO-…` or `CH-…`) that opens the SourceViewer
 * to the exact work order or the cited PDF page. The evidence contract spine
 * (TDD §4) made visible.
 */
export function EvidenceChip({ citation, label }: { citation: string; label?: string }) {
  const { open } = useSourceViewer();
  const isWo = citation.startsWith("WO-");
  const Icon = isWo ? Wrench : FileText;
  return (
    <button
      type="button"
      onClick={() => open(citation)}
      className={cn(
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-semibold tabular-nums transition-colors",
        "border-primary/30 bg-primary/10 text-primary hover:bg-primary/20",
      )}
      title={`Open source ${citation}`}
    >
      <Icon className="size-3" />
      {label ?? citation}
    </button>
  );
}
