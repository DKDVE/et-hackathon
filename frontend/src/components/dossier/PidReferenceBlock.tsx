import { useEffect, useState } from "react";

import { useSourceViewer } from "@/components/source/SourceViewer";
import { fileUrl, getPidDrawings, type PidDrawingSource } from "@/lib/api";

export function PidReferenceBlock({ assetId }: { assetId: number }) {
  const { openReference } = useSourceViewer();
  const [drawings, setDrawings] = useState<PidDrawingSource[]>([]);

  useEffect(() => {
    getPidDrawings(assetId)
      .then(setDrawings)
      .catch(() => setDrawings([]));
  }, [assetId]);

  if (!drawings.length) return null;

  return (
    <div className="space-y-2">
      {drawings.map((d) => (
        <button
          key={d.document_id}
          type="button"
          className="block w-full overflow-hidden rounded border border-border bg-muted/30 text-left transition hover:border-primary/40"
          onClick={() => openReference(d.document_id, d.title)}
        >
          <img
            src={fileUrl(d.file_url)}
            alt={d.title}
            className="h-28 w-full object-cover object-left-top"
          />
          <span className="block px-2 py-1 text-[10px] uppercase tracking-widest text-muted-foreground">
            Reference drawing
          </span>
        </button>
      ))}
    </div>
  );
}
