import { Link } from "react-router-dom";
import { Clock, Cog } from "lucide-react";

import type { EventSummary } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  criticalityAccentClass,
  criticalityBadgeClass,
  type Criticality,
} from "@/lib/criticality";

const SYMPTOM_LABEL: Record<string, string> = {
  seal_leak: "Seal Leak",
  vibration: "Elevated Vibration",
  overheating: "Overheating",
  pressure_anomaly: "Pressure Anomaly",
  abnormal_noise: "Abnormal Noise",
  trip: "Trip",
  low_flow: "Low Flow",
  other: "General Review",
};

const statusDotClass: Record<string, string> = {
  open: "bg-primary",
  reviewed: "bg-muted-foreground",
  closed: "bg-emerald-500",
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.max(0, Math.floor(diffMs / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function EventCard({ event }: { event: EventSummary }) {
  const criticality = event.criticality as Criticality;
  const symptom = SYMPTOM_LABEL[event.symptom_category] ?? event.symptom_category;
  return (
    <Link to={`/events/${event.id}`}>
      <div
        className={cn(
          "group relative flex cursor-pointer flex-col gap-6 overflow-hidden rounded-xl border border-border/50 bg-card/40 p-5 transition-all",
          "hover:border-border hover:bg-card/60 lg:flex-row lg:items-center",
        )}
      >
        <div
          className={cn(
            "absolute top-0 bottom-0 left-0 w-1",
            criticalityAccentClass(criticality),
          )}
        />
        <div className="shrink-0 lg:w-32">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            Asset Tag
          </div>
          <div className="text-lg font-bold tabular-nums">{event.asset_tag}</div>
        </div>
        <div className="hidden h-10 w-px bg-border lg:block" />
        <div className="grow">
          <div className="mb-1 flex flex-wrap items-center gap-3">
            <span className="text-lg font-medium">{symptom}</span>
            <span className={criticalityBadgeClass(criticality)}>
              CRITICALITY {criticality}
            </span>
            <span className="rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              {event.source}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Clock className="size-3.5" />
              <span className="tabular-nums text-foreground/80">{timeAgo(event.created_at)}</span>
            </span>
            <span className="flex items-center gap-1.5">
              <Cog className="size-3.5" />
              {event.unit}
            </span>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between gap-6 lg:mt-0 lg:justify-end">
          <div className="hidden text-right sm:block">
            <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
              Status
            </div>
            <div className="flex items-center justify-end gap-2">
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  statusDotClass[event.status] ?? "bg-muted-foreground",
                )}
              />
              <span className="text-sm font-semibold capitalize">{event.status}</span>
            </div>
          </div>
          <span className="rounded border border-border bg-background px-4 py-2 text-sm font-semibold text-muted-foreground group-hover:border-primary/40 group-hover:text-primary">
            Open dossier
          </span>
        </div>
      </div>
    </Link>
  );
}
