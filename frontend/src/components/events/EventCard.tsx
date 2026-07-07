import { Link } from "react-router-dom";
import { Clock, Cog } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  criticalityAccentClass,
  criticalityBadgeClass,
  type Criticality,
} from "@/lib/criticality";

export type EventCardData = {
  id: string;
  tag: string;
  symptom: string;
  criticality: Criticality;
  timeAgo: string;
  unit: string;
  status: string;
  statusDot: "open" | "assigned" | "reviewed";
  actionLabel: string;
  href?: string;
};

const statusDotClass = {
  open: "bg-primary",
  assigned: "bg-emerald-500",
  reviewed: "bg-muted-foreground",
} as const;

export function EventCard({ event }: { event: EventCardData }) {
  const body = (
    <div
      className={cn(
        "group relative flex flex-col gap-6 overflow-hidden rounded-xl border border-border/50 bg-card/40 p-5 transition-all",
        "hover:border-border hover:bg-card/60 lg:flex-row lg:items-center",
        event.href && "cursor-pointer",
      )}
    >
      <div
        className={cn(
          "absolute top-0 bottom-0 left-0 w-1",
          criticalityAccentClass(event.criticality),
        )}
      />
      <div className="shrink-0 lg:w-32">
        <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          Asset Tag
        </div>
        <div className="text-lg font-bold tabular-nums">{event.tag}</div>
      </div>
      <div className="hidden h-10 w-px bg-border lg:block" />
      <div className="grow">
        <div className="mb-1 flex flex-wrap items-center gap-3">
          <span className="text-lg font-medium">{event.symptom}</span>
          <span className={criticalityBadgeClass(event.criticality)}>
            CRITICALITY {event.criticality}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Clock className="size-3.5" />
            <span className="tabular-nums text-foreground/80">{event.timeAgo}</span>
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
            <span className={cn("size-1.5 rounded-full", statusDotClass[event.statusDot])} />
            <span
              className={cn(
                "text-sm font-semibold",
                event.statusDot === "reviewed" && "text-muted-foreground",
              )}
            >
              {event.status}
            </span>
          </div>
        </div>
        <span className="rounded border border-border bg-background px-4 py-2 text-sm font-semibold text-muted-foreground">
          {event.actionLabel}
        </span>
      </div>
    </div>
  );

  if (event.href) {
    return <Link to={event.href}>{body}</Link>;
  }
  return body;
}
