import { Link } from "react-router-dom";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type TraceRunRow = {
  id: number;
  node: string;
  model: string;
  prompt_version: string;
  started_at: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  status: string;
  dossier_id?: number;
  event_id?: number;
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function TraceRunTable({
  runs,
  showDossierLink = false,
}: {
  runs: TraceRunRow[];
  showDossierLink?: boolean;
}) {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No reasoning runs yet. Complete a dossier with reasoning enabled to populate this view.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            {showDossierLink && <TableHead>Dossier</TableHead>}
            <TableHead>Node</TableHead>
            <TableHead>Model</TableHead>
            <TableHead>Prompt</TableHead>
            <TableHead>Started</TableHead>
            <TableHead className="text-right">Latency</TableHead>
            <TableHead className="text-right">Tokens</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => (
            <TableRow key={run.id}>
              {showDossierLink && (
                <TableCell>
                  {run.event_id != null ? (
                    <Link
                      to={`/events/${run.event_id}`}
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      #{run.dossier_id}
                    </Link>
                  ) : (
                    "—"
                  )}
                </TableCell>
              )}
              <TableCell className="font-medium">{run.node}</TableCell>
              <TableCell className="max-w-[10rem] truncate text-xs text-muted-foreground">
                {run.model}
              </TableCell>
              <TableCell className="text-xs tabular-nums text-muted-foreground">
                {run.prompt_version}
              </TableCell>
              <TableCell className="text-xs tabular-nums">{formatTime(run.started_at)}</TableCell>
              <TableCell className="text-right text-xs tabular-nums">
                {run.latency_ms} ms
              </TableCell>
              <TableCell className="text-right text-xs tabular-nums">
                {run.prompt_tokens}+{run.completion_tokens}
              </TableCell>
              <TableCell
                className={cn(
                  "text-xs capitalize",
                  run.status === "repaired" && "font-semibold text-amber-500",
                )}
              >
                {run.status}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function formatUsd(amount: number): string {
  if (amount < 0.01) return "< $0.01";
  return `$${amount.toFixed(2)}`;
}

export function CostRollupCards({
  todayUsd,
  totalUsd,
  byModel,
  footnote,
}: {
  todayUsd: number;
  totalUsd: number;
  byModel: Record<string, { estimated_cost_usd?: number }>;
  footnote: string;
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-6 text-sm">
        <Stat label="Today (est.)" value={formatUsd(todayUsd)} emphasis />
        <Stat label="Total (est.)" value={formatUsd(totalUsd)} />
        {Object.entries(byModel).map(([model, bucket]) => (
          <Stat
            key={model}
            label={model.split("/").pop() ?? model}
            value={formatUsd(bucket.estimated_cost_usd ?? 0)}
          />
        ))}
      </div>
      <p className="text-[11px] text-muted-foreground">{footnote}</p>
    </div>
  );
}

function Stat({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className={emphasis ? "font-semibold text-primary tabular-nums" : "tabular-nums"}>
        {value}
      </div>
    </div>
  );
}
