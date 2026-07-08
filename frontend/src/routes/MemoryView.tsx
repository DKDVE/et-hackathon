import { Fragment, useCallback, useEffect, useMemo, useState } from "react";

import { SourceProvider } from "@/components/source/SourceViewer";
import { PidReferenceBlock } from "@/components/dossier/PidReferenceBlock";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getMemoryAssets,
  getMemoryDocuments,
  getMemoryOverview,
  getMemoryReviewQueue,
  getMemoryTaxonomy,
  submitReviewVerdict,
  fileUrl,
  type MemoryAssetRow,
  type MemoryDocumentRow,
  type MemoryOverview,
  type ReviewQueueRow,
  type TaxonomyFamilyGroup,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "overview" | "assets" | "documents" | "taxonomy" | "review";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "assets", label: "Assets" },
  { id: "documents", label: "Documents" },
  { id: "taxonomy", label: "Taxonomy" },
  { id: "review", label: "Review Queue" },
];

function tierBadgeClass(tier: string) {
  if (tier === "Good") return "bg-emerald-500/15 text-emerald-500 border-emerald-500/30";
  if (tier === "Partial") return "bg-amber-500/15 text-amber-500 border-amber-500/30";
  return "bg-muted text-muted-foreground border-border";
}

function ScoreBar({ score }: { score: number | null }) {
  const pct = score != null ? Math.min(100, Math.max(0, score * 100)) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-primary transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs text-muted-foreground">
        {score != null ? score.toFixed(3) : "—"}
      </span>
    </div>
  );
}

function OverviewTab({ data }: { data: MemoryOverview | null }) {
  if (!data) {
    return <p className="text-sm text-muted-foreground">Loading overview…</p>;
  }
  const cards = [
    { label: "Assets", value: data.asset_count },
    { label: "Documents", value: data.document_count },
    { label: "Chunks", value: data.chunk_count },
    { label: "Work Orders", value: data.work_order_count },
    { label: "Taxonomy modes", value: data.taxonomy_size },
  ];
  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((c) => (
          <div key={c.label} className="rounded-lg border border-border bg-card p-4">
            <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
              {c.label}
            </div>
            <div className="mt-1 text-2xl font-black tabular-nums text-primary">{c.value}</div>
          </div>
        ))}
      </div>
      <div className="rounded-lg border border-border bg-card p-6">
        <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">
          Work order classification
        </h3>
        <p className="mt-2 text-xs text-muted-foreground">
          {data.wo_failure_classified} failure records · {data.wo_routine_closures} routine
          closures · {data.wo_unclassified} unclassified · {data.wo_human_reviewed} human-reviewed
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-4">
          <div>
            <div className="text-2xl font-bold tabular-nums">{data.wo_failure_classified}</div>
            <div className="text-xs text-muted-foreground">Failure classified</div>
          </div>
          <div>
            <div className="text-2xl font-bold tabular-nums">{data.wo_routine_closures}</div>
            <div className="text-xs text-muted-foreground">Routine closures</div>
          </div>
          <div>
            <div className="text-2xl font-bold tabular-nums">{data.wo_unclassified}</div>
            <div className="text-xs text-muted-foreground">Unclassified</div>
          </div>
          <div>
            <div className="text-2xl font-bold tabular-nums">{data.wo_human_reviewed}</div>
            <div className="text-xs text-muted-foreground">Human-reviewed</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function AssetsTab({
  assets,
  footnote,
}: {
  assets: MemoryAssetRow[];
  footnote: string;
}) {
  const [expanded, setExpanded] = useState<number | null>(null);
  if (!assets.length) {
    return <p className="text-sm text-muted-foreground">No assets in memory layer.</p>;
  }
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">* {footnote}</p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[10px] uppercase tracking-widest text-muted-foreground">
              <th className="p-3">Tag</th>
              <th className="p-3">Class</th>
              <th className="p-3">Tier</th>
              <th className="p-3">WOs</th>
              <th className="p-3">Classified</th>
              <th className="p-3">Manual</th>
              <th className="p-3">SOPs</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <Fragment key={a.asset_id}>
                <tr
                  className="cursor-pointer border-b border-border/50 hover:bg-muted/30"
                  onClick={() => setExpanded(expanded === a.asset_id ? null : a.asset_id)}
                >
                  <td className="p-3 font-mono font-medium">{a.tag}</td>
                  <td className="p-3">{a.asset_class}</td>
                  <td className="p-3">
                    <Badge variant="outline" className={tierBadgeClass(a.coverage_tier)}>
                      {a.coverage_tier}
                    </Badge>
                  </td>
                  <td className="p-3 tabular-nums">{a.wo_count}</td>
                  <td className="p-3 tabular-nums">{(a.classified_ratio * 100).toFixed(0)}%</td>
                  <td className="p-3">{a.manual_available ? "✓" : "—"}</td>
                  <td className="p-3 tabular-nums">{a.sop_count}</td>
                </tr>
                {expanded === a.asset_id && (
                  <tr className="bg-muted/20">
                    <td colSpan={7} className="p-4 text-xs text-muted-foreground">
                      <strong>{a.name}</strong> · Last WO closed:{" "}
                      {a.last_inspection_date ?? "—"}
                      <div className="mt-3 max-w-xs">
                        <PidReferenceBlock assetId={a.asset_id} />
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DocumentsTab({ docs, onOpenFile }: { docs: MemoryDocumentRow[]; onOpenFile: (url: string) => void }) {
  if (!docs.length) {
    return <p className="text-sm text-muted-foreground">No documents ingested yet.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-[10px] uppercase tracking-widest text-muted-foreground">
            <th className="p-3">Title</th>
            <th className="p-3">Type</th>
            <th className="p-3">Owner</th>
            <th className="p-3">Chunks</th>
            <th className="p-3">Pages</th>
            <th className="p-3">File</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((d) => (
            <tr key={d.document_id} className="border-b border-border/50">
              <td className="p-3">{d.title}</td>
              <td className="p-3 font-mono text-xs">{d.doc_type}</td>
              <td className="p-3 text-xs">
                {d.owner_asset_tag ?? d.owner_class ?? "—"}
              </td>
              <td className="p-3 tabular-nums">{d.chunk_count}</td>
              <td className="p-3 tabular-nums">{d.ocr_page_count}</td>
              <td className="p-3">
                <button
                  type="button"
                  className="text-xs font-medium text-primary hover:underline"
                  onClick={() => onOpenFile(d.file_url)}
                >
                  Open PDF
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TaxonomyTab({ groups }: { groups: TaxonomyFamilyGroup[] }) {
  if (!groups.length) {
    return <p className="text-sm text-muted-foreground">Taxonomy not loaded.</p>;
  }
  return (
    <div className="space-y-6">
      {groups.map((g) => (
        <div key={g.family} className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-bold uppercase tracking-widest text-primary">{g.family}</h3>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-widest text-muted-foreground">
                <th className="pb-2">Mode</th>
                <th className="pb-2">Auto WOs</th>
                <th className="pb-2">Human overrides</th>
                <th className="pb-2">Mean score</th>
              </tr>
            </thead>
            <tbody>
              {g.modes.map((m) => (
                <tr key={m.mode_id} className="border-t border-border/40">
                  <td className="py-2">
                    <span className="font-mono text-xs">{m.code}</span>
                    <span className="ml-2 text-muted-foreground">{m.name}</span>
                  </td>
                  <td className="py-2 tabular-nums">{m.auto_wo_count}</td>
                  <td className="py-2 tabular-nums">{m.human_override_count}</td>
                  <td className="py-2 font-mono text-xs">
                    {m.mean_normalization_score?.toFixed(3) ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function ReviewQueueTab({
  queue,
  allModes,
  onVerdict,
}: {
  queue: ReviewQueueRow[];
  allModes: { mode_id: number; code: string; name: string }[];
  onVerdict: (woId: number, verdict: string, modeId?: number) => void;
}) {
  const [pickerFor, setPickerFor] = useState<number | null>(null);
  const [search, setSearch] = useState("");

  const filteredModes = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return allModes;
    return allModes.filter(
      (m) => m.code.toLowerCase().includes(q) || m.name.toLowerCase().includes(q),
    );
  }, [allModes, search]);

  if (!queue.length) {
    return (
      <p className="text-sm text-muted-foreground">
        Review queue empty — no unclassified or low-margin work orders need eyes.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {queue.map((row) => (
        <div key={row.wo_id} className="rounded-lg border border-border bg-card p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="font-mono text-sm font-bold">{row.wo_number}</div>
              <div className="text-xs text-muted-foreground">{row.asset_tag}</div>
              <p className="mt-2 max-w-2xl text-sm">{row.raw_description}</p>
            </div>
            <div className="text-right text-xs">
              <div className="text-muted-foreground">Auto suggestion</div>
              <div className="font-mono">{row.auto_failure_mode_code ?? "unclassified"}</div>
              {row.auto_failure_mode_family && (
                <div className="text-muted-foreground">{row.auto_failure_mode_family}</div>
              )}
              <div className="mt-2">
                <ScoreBar score={row.normalization_score} />
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={row.auto_failure_mode_code == null}
              onClick={() => onVerdict(row.wo_id, "confirmed")}
            >
              Confirm
            </Button>
            <Button size="sm" variant="outline" onClick={() => setPickerFor(pickerFor === row.wo_id ? null : row.wo_id)}>
              Correct
            </Button>
            <Button size="sm" variant="ghost" onClick={() => onVerdict(row.wo_id, "unclassifiable")}>
              Unclassifiable
            </Button>
          </div>
          {pickerFor === row.wo_id && (
            <div className="mt-4 rounded border border-border bg-muted/20 p-3">
              <Input
                placeholder="Search modes…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="mb-2"
              />
              <div className="max-h-40 space-y-1 overflow-y-auto">
                {row.candidates.map((c) => (
                  <button
                    key={c.mode_id}
                    type="button"
                    className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-muted"
                    onClick={() => {
                      onVerdict(row.wo_id, "corrected", c.mode_id);
                      setPickerFor(null);
                    }}
                  >
                    <span className="font-mono">{c.code}</span>
                    <span className="ml-2 text-muted-foreground">{c.score.toFixed(3)}</span>
                  </button>
                ))}
                {search && filteredModes.map((m) => (
                  <button
                    key={`full-${m.mode_id}`}
                    type="button"
                    className="block w-full rounded px-2 py-1 text-left text-xs hover:bg-muted"
                    onClick={() => {
                      onVerdict(row.wo_id, "corrected", m.mode_id);
                      setPickerFor(null);
                    }}
                  >
                    <span className="font-mono">{m.code}</span> {m.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function MemoryView() {
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<MemoryOverview | null>(null);
  const [assets, setAssets] = useState<MemoryAssetRow[]>([]);
  const [footnote, setFootnote] = useState("");
  const [documents, setDocuments] = useState<MemoryDocumentRow[]>([]);
  const [taxonomy, setTaxonomy] = useState<TaxonomyFamilyGroup[]>([]);
  const [queue, setQueue] = useState<ReviewQueueRow[]>([]);

  const load = useCallback(() => {
    getMemoryOverview().then(setOverview).catch(() => setOverview(null));
    getMemoryAssets().then((r) => {
      setAssets(r.assets);
      setFootnote(r.coverage_footnote);
    });
    getMemoryDocuments().then(setDocuments).catch(() => setDocuments([]));
    getMemoryTaxonomy().then(setTaxonomy).catch(() => setTaxonomy([]));
    getMemoryReviewQueue().then(setQueue).catch(() => setQueue([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const allModes = useMemo(
    () => taxonomy.flatMap((g) => g.modes.map((m) => ({ mode_id: m.mode_id, code: m.code, name: m.name }))),
    [taxonomy],
  );

  const handleVerdict = async (woId: number, verdict: string, modeId?: number) => {
    await submitReviewVerdict(woId, { verdict, failure_mode_id: modeId ?? null });
    setQueue((prev) => prev.filter((r) => r.wo_id !== woId));
    getMemoryOverview().then(setOverview);
  };

  const openPdf = (url: string) => {
    window.open(fileUrl(url), "_blank");
  };

  const queueCount = queue.length;

  return (
    <SourceProvider>
      <AppShell>
        <PageHeader
          title="Operational Memory"
          subtitle="Knowledge health — what the system knows, what it ingested, where it needs judgment"
        />
        <div className="mb-6 flex flex-wrap gap-2 border-b border-border pb-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "px-3 py-1.5 text-sm font-medium transition-colors",
                tab === t.id
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {t.label}
              {t.id === "review" && queueCount > 0 && (
                <span className="ml-1.5 rounded-full bg-primary/20 px-1.5 text-xs tabular-nums text-primary">
                  {queueCount}
                </span>
              )}
            </button>
          ))}
        </div>
        {tab === "overview" && <OverviewTab data={overview} />}
        {tab === "assets" && <AssetsTab assets={assets} footnote={footnote} />}
        {tab === "documents" && <DocumentsTab docs={documents} onOpenFile={openPdf} />}
        {tab === "taxonomy" && <TaxonomyTab groups={taxonomy} />}
        {tab === "review" && (
          <ReviewQueueTab queue={queue} allModes={allModes} onVerdict={handleVerdict} />
        )}
      </AppShell>
    </SourceProvider>
  );
}
