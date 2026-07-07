import {
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Download,
  ExternalLink,
  Filter,
  Search,
  AlertTriangle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
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

type AssetRow = {
  tag: string;
  name: string;
  className: string;
  plantUnit: string;
  criticality: Criticality;
  status: string;
  statusTone: "error" | "primary" | "muted";
  highlight?: boolean;
};

// ponytail: static Stitch reference data until M2 seed + assets API
const MOCK_ASSETS: AssetRow[] = [
  {
    tag: "P-3401",
    name: "Main Feed Pump A",
    className: "Centrifugal Pump",
    plantUnit: "North Plant - Hydrocracker",
    criticality: "A",
    status: "High Vibration",
    statusTone: "error",
  },
  {
    tag: "P-3402",
    name: "Main Feed Pump B",
    className: "Centrifugal Pump",
    plantUnit: "North Plant - Hydrocracker",
    criticality: "A",
    status: "Normal",
    statusTone: "muted",
  },
  {
    tag: "E-1105",
    name: "Overhead Condenser",
    className: "Heat Exchanger",
    plantUnit: "South Plant - Distillation",
    criticality: "B",
    status: "Normal",
    statusTone: "muted",
  },
  {
    tag: "C-400",
    name: "Recycle Gas Compressor",
    className: "Centrifugal Compressor",
    plantUnit: "North Plant - Hydrocracker",
    criticality: "A",
    status: "Efficiency Drop",
    statusTone: "primary",
    highlight: true,
  },
  {
    tag: "V-201",
    name: "Flash Drum",
    className: "Pressure Vessel",
    plantUnit: "East Plant - Separation",
    criticality: "C",
    status: "Offline - Maint.",
    statusTone: "muted",
  },
];

const statusDotClass = {
  error: "bg-destructive",
  primary: "bg-primary",
  muted: "bg-emerald-500",
} as const;

const statusTextClass = {
  error: "text-destructive",
  primary: "text-primary",
  muted: "text-muted-foreground",
} as const;

export function AssetRegistryContent() {
  return (
    <>
      <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="flex flex-col gap-2 rounded border border-border bg-card p-4">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Total Monitored Assets
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-semibold tabular-nums">1,402</span>
            <span className="flex items-center text-xs font-medium text-emerald-500">
              <ArrowUp className="size-3.5" /> 12
            </span>
          </div>
        </div>
        <div className="flex flex-col gap-2 rounded border border-border bg-card p-4">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Active Process Units
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-semibold tabular-nums">48</span>
            <span className="text-xs text-muted-foreground">Across 3 Plants</span>
          </div>
        </div>
        <div className="flex flex-col gap-2 rounded border border-border bg-card p-4">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Criticality A Assets
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-semibold tabular-nums text-primary">156</span>
            <span className="flex items-center gap-1 text-xs font-medium text-destructive">
              <AlertTriangle className="size-3.5" /> 3 Attention Required
            </span>
          </div>
        </div>
      </div>

      <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div className="relative w-full sm:w-96">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="border-border bg-card pl-10"
            placeholder="Search by Tag, Name, or Class..."
          />
        </div>
        <div className="flex w-full gap-2 sm:w-auto">
          <Button variant="outline" size="sm" className="flex-1 gap-2 sm:flex-none">
            <Filter className="size-4" />
            Filter
          </Button>
          <Button variant="outline" size="sm" className="flex-1 gap-2 sm:flex-none">
            <Columns3 className="size-4" />
            Columns
          </Button>
          <Button variant="outline" size="sm" className="gap-2 border-primary/30 bg-primary/10 text-primary">
            <Download className="size-4" />
            Export
          </Button>
        </div>
      </div>

      <div className="overflow-hidden rounded border border-border bg-card">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-border bg-muted/30 hover:bg-muted/30">
                <TableHead className="text-xs font-medium uppercase text-muted-foreground">
                  Tag
                </TableHead>
                <TableHead className="text-xs font-medium uppercase text-muted-foreground">
                  Name
                </TableHead>
                <TableHead className="text-xs font-medium uppercase text-muted-foreground">
                  Class
                </TableHead>
                <TableHead className="text-xs font-medium uppercase text-muted-foreground">
                  Plant - Unit
                </TableHead>
                <TableHead className="text-xs font-medium uppercase text-muted-foreground">
                  Criticality
                </TableHead>
                <TableHead className="text-xs font-medium uppercase text-muted-foreground">
                  Status
                </TableHead>
                <TableHead className="text-right text-xs font-medium uppercase text-muted-foreground">
                  Actions
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {MOCK_ASSETS.map((asset) => (
                <TableRow
                  key={asset.tag}
                  className={cn(
                    "group border-border transition-colors hover:bg-muted/20",
                    asset.highlight && "border-l-2 border-l-primary",
                  )}
                >
                  <TableCell className="font-medium tabular-nums">{asset.tag}</TableCell>
                  <TableCell>{asset.name}</TableCell>
                  <TableCell className="text-muted-foreground">{asset.className}</TableCell>
                  <TableCell className="text-muted-foreground">{asset.plantUnit}</TableCell>
                  <TableCell>
                    <span
                      className={cn(
                        "inline-flex size-6 items-center justify-center rounded text-xs font-bold",
                        criticalityBadgeClass(asset.criticality),
                        asset.criticality === "A" &&
                          asset.statusTone !== "muted" &&
                          "shadow-[0_0_10px] shadow-primary/20",
                      )}
                    >
                      {asset.criticality}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          statusDotClass[asset.statusTone],
                        )}
                      />
                      <span className={cn("font-medium", statusTextClass[asset.statusTone])}>
                        {asset.status}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <button
                      type="button"
                      className="text-muted-foreground opacity-0 transition-all group-hover:opacity-100 hover:text-primary"
                      aria-label={`Open ${asset.tag}`}
                    >
                      <ExternalLink className="size-4" />
                    </button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="flex items-center justify-between border-t border-border bg-muted/20 p-4 text-sm text-muted-foreground">
          <span>Showing 1 to 5 of 1,402 entries</span>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="size-7" disabled>
              <ChevronLeft className="size-4" />
            </Button>
            <Button variant="secondary" size="icon" className="size-7 text-xs">
              1
            </Button>
            <Button variant="ghost" size="icon" className="size-7 text-xs">
              2
            </Button>
            <Button variant="ghost" size="icon" className="size-7 text-xs">
              3
            </Button>
            <span className="px-1">…</span>
            <Button variant="ghost" size="icon" className="size-7">
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
