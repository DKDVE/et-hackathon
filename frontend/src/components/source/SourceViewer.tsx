import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import { ChevronLeft, ChevronRight, FileText, Wrench, X } from "lucide-react";

import {
  fileUrl,
  getChunkSource,
  getWorkOrderSource,
  type ChunkSource,
  type WorkOrderSource,
} from "@/lib/api";

// pdf.js worker (bundled by Vite). Configured once at module load.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

type SourceContextValue = { open: (citationId: string) => void };
const SourceContext = createContext<SourceContextValue | null>(null);

export function useSourceViewer(): SourceContextValue {
  const ctx = useContext(SourceContext);
  if (!ctx) throw new Error("useSourceViewer must be used within <SourceProvider>");
  return ctx;
}

export function SourceProvider({ children }: { children: ReactNode }) {
  const [citation, setCitation] = useState<string | null>(null);
  const open = useCallback((citationId: string) => setCitation(citationId), []);
  return (
    <SourceContext.Provider value={{ open }}>
      {children}
      {citation && <SourceModal citation={citation} onClose={() => setCitation(null)} />}
    </SourceContext.Provider>
  );
}

function SourceModal({ citation, onClose }: { citation: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const isChunk = citation.startsWith("CH-");
  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-primary">
            {isChunk ? <FileText className="size-4" /> : <Wrench className="size-4" />}
            <span>{isChunk ? "Document Source" : "Work Order"} · {citation}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Close"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          {isChunk ? (
            <ChunkPdfView chunkId={Number(citation.slice(3))} />
          ) : (
            <WorkOrderView woNumber={citation} />
          )}
        </div>
      </div>
    </div>
  );
}

function ChunkPdfView({ chunkId }: { chunkId: number }) {
  const [src, setSrc] = useState<ChunkSource | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [numPages, setNumPages] = useState(0);

  useEffect(() => {
    getChunkSource(chunkId)
      .then((s) => {
        setSrc(s);
        setPage(s.page); // open AT the cited page
      })
      .catch(() => setError("Could not load source document."));
  }, [chunkId]);

  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;
  if (!src) return <div className="p-6 text-sm text-muted-foreground">Loading source…</div>;

  return (
    <div className="flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 bg-card/60 px-5 py-3 text-xs">
        <div className="min-w-0">
          <div className="truncate font-semibold text-foreground">{src.document_title}</div>
          {src.section_ref && (
            <div className="mt-0.5 text-muted-foreground">
              Section <span className="text-primary">{src.section_ref}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 tabular-nums text-muted-foreground">
          <button
            type="button"
            className="rounded p-1 hover:text-foreground disabled:opacity-30"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <ChevronLeft className="size-4" />
          </button>
          <span>
            Page {page}
            {numPages ? ` / ${numPages}` : ""} · cited p{src.page}
          </span>
          <button
            type="button"
            className="rounded p-1 hover:text-foreground disabled:opacity-30"
            onClick={() => setPage((p) => (numPages ? Math.min(numPages, p + 1) : p + 1))}
            disabled={numPages > 0 && page >= numPages}
            aria-label="Next page"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>
      <div className="flex justify-center bg-neutral-900/40 p-4">
        <Document
          file={fileUrl(src.file_url)}
          onLoadSuccess={({ numPages: n }) => setNumPages(n)}
          loading={<div className="p-8 text-sm text-muted-foreground">Rendering PDF…</div>}
          error={<div className="p-8 text-sm text-destructive">Failed to render PDF.</div>}
        >
          <Page
            pageNumber={page}
            width={620}
            renderTextLayer={false}
            renderAnnotationLayer={false}
          />
        </Document>
      </div>
    </div>
  );
}

function WorkOrderView({ woNumber }: { woNumber: string }) {
  const [wo, setWo] = useState<WorkOrderSource | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getWorkOrderSource(woNumber)
      .then(setWo)
      .catch(() => setError("Could not load work order."));
  }, [woNumber]);

  if (error) return <div className="p-6 text-sm text-destructive">{error}</div>;
  if (!wo) return <div className="p-6 text-sm text-muted-foreground">Loading work order…</div>;

  const rows: [string, string][] = [
    ["Asset", `${wo.asset_tag} · ${wo.asset_name}`],
    ["Opened", wo.opened_on ?? "—"],
    ["Closed", wo.closed_on ?? "—"],
    ["Downtime", wo.downtime_hours != null ? `${wo.downtime_hours} h` : "—"],
    ["Failure mode", wo.failure_mode_name ?? wo.failure_mode_code ?? "unclassified"],
  ];

  return (
    <div className="space-y-5 p-6">
      <div className="grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 border-b border-border/40 py-1.5 text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className="text-right font-medium">{value}</span>
          </div>
        ))}
      </div>
      <div>
        <div className="mb-1 text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Description
        </div>
        <p className="text-sm leading-relaxed">{wo.raw_description}</p>
      </div>
      {wo.actions_taken && (
        <div>
          <div className="mb-1 text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Actions Taken
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">{wo.actions_taken}</p>
        </div>
      )}
    </div>
  );
}
