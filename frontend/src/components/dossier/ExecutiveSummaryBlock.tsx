import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

export function ExecutiveSummaryBlock({ summary }: { summary: string | null | undefined }) {
  const [open, setOpen] = useState(false);
  if (!summary) return null;

  return (
    <div className="rounded-lg border border-border bg-card/60">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          AI summary of validated findings
        </span>
        <ChevronDown
          className={cn("size-4 shrink-0 text-muted-foreground transition", open && "rotate-180")}
        />
      </button>
      {open && (
        <p className="border-t border-border/50 px-4 py-3 text-sm leading-relaxed text-foreground/90">
          {summary}
        </p>
      )}
    </div>
  );
}
