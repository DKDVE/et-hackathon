import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { criticalityBadgeClass, type Criticality } from "@/lib/criticality";
import { listAssets, type AssetSummary } from "@/lib/api";

export function AssetRegistryContent() {
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAssets()
      .then(setAssets)
      .catch(() => setError("Could not reach the API."));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return assets;
    return assets.filter((a) =>
      [a.tag, a.name, a.asset_class, a.unit].some((f) => f.toLowerCase().includes(q)),
    );
  }, [assets, query]);

  const stats = useMemo(
    () => ({
      total: assets.length,
      units: new Set(assets.map((a) => a.unit)).size,
      critical: assets.filter((a) => a.criticality === "A").length,
    }),
    [assets],
  );

  return (
    <>
      <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard label="Total Assets" value={stats.total} />
        <StatCard label="Process Units" value={stats.units} />
        <StatCard label="Criticality A Assets" value={stats.critical} emphasis />
      </div>

      <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div className="relative w-full sm:w-96">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="border-border bg-card pl-10"
            placeholder="Search by Tag, Name, Class, or Unit…"
          />
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded border border-border bg-card">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border bg-muted/30 hover:bg-muted/30">
                {["Tag", "Name", "Class", "Plant · Unit", "Criticality", "Service Duty"].map(
                  (h) => (
                    <TableHead
                      key={h}
                      className="text-xs font-medium uppercase text-muted-foreground"
                    >
                      {h}
                    </TableHead>
                  ),
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((asset) => (
                <TableRow
                  key={asset.tag}
                  className="group border-border transition-colors hover:bg-muted/20"
                >
                  <TableCell className="font-medium tabular-nums">{asset.tag}</TableCell>
                  <TableCell>{asset.name}</TableCell>
                  <TableCell className="text-muted-foreground">{asset.asset_class}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {asset.plant} · {asset.unit}
                  </TableCell>
                  <TableCell>
                    <span
                      className={cn(
                        "inline-flex size-6 items-center justify-center rounded text-xs font-bold",
                        criticalityBadgeClass(asset.criticality as Criticality),
                      )}
                    >
                      {asset.criticality}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{asset.service_duty}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="border-t border-border bg-muted/20 p-4 text-sm text-muted-foreground">
          Showing {filtered.length} of {assets.length} assets
        </div>
      </div>
    </>
  );
}

function StatCard({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: number;
  emphasis?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 rounded border border-border bg-card p-4">
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className={cn("text-2xl font-semibold tabular-nums", emphasis && "text-primary")}>
        {value}
      </span>
    </div>
  );
}
