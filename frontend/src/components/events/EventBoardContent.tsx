import { useEffect, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { listEvents, type EventSummary } from "@/lib/api";
import { EventCard } from "./EventCard";
import { EventFiltersSidebar } from "./EventFiltersSidebar";

const FILTERS = [
  { label: "All", value: undefined },
  { label: "Open", value: "open" },
  { label: "Reviewed", value: "reviewed" },
  { label: "Closed", value: "closed" },
] as const;

const POLL_MS = 5000;

export function EventBoardContent() {
  const [active, setActive] = useState<(typeof FILTERS)[number]>(FILTERS[0]);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      listEvents(active.value)
        .then((e) => {
          if (cancelled) return;
          setEvents(e);
          setError(null);
          setLoaded(true);
        })
        .catch(() => !cancelled && setError("Could not reach the API."));
    load();
    const timer = setInterval(load, POLL_MS); // auto-refresh (Task 5)
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [active]);

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      <EventFiltersSidebar />
      <div className="w-full min-w-0 flex-1">
        <div className="mb-8 flex flex-wrap items-center gap-3">
          {FILTERS.map((filter) => (
            <button
              key={filter.label}
              type="button"
              onClick={() => setActive(filter)}
              className={cn(
                "rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-all",
                active.label === filter.label
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground",
              )}
            >
              {filter.label}
            </button>
          ))}
          <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            <RefreshCw className="size-3 animate-spin [animation-duration:3s]" />
            Live · {POLL_MS / 1000}s
          </span>
          <div className="ml-auto">
            <Button variant="outline" size="sm" className="gap-2" disabled>
              <Plus className="size-4" />
              Manual Log
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {loaded && events.length === 0 && !error && (
          <div className="rounded border border-dashed border-border bg-card/40 p-10 text-center text-sm text-muted-foreground">
            No {active.value ?? ""} events. Fire one with{" "}
            <code className="text-primary">python scripts/simulate_event.py</code>.
          </div>
        )}

        <div className="space-y-4">
          {events.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </div>
    </div>
  );
}
