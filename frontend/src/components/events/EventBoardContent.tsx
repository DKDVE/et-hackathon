import { useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { listAssets, listEvents, type EventSummary } from "@/lib/api";
import {
  defaultFilters,
  distinctUnits,
  filterEvents,
  type EventBoardFilters,
} from "@/lib/eventFilters";
import { EventCard } from "./EventCard";
import { EventFiltersSidebar } from "./EventFiltersSidebar";

const POLL_MS = 5000;

export function EventBoardContent() {
  const [allEvents, setAllEvents] = useState<EventSummary[]>([]);
  const [units, setUnits] = useState<string[]>([]);
  const [filters, setFilters] = useState<EventBoardFilters | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    listAssets()
      .then((assets) => {
        const unitList = distinctUnits(assets);
        setUnits(unitList);
        setFilters((prev) => prev ?? defaultFilters(unitList));
      })
      .catch(() => {
        /* ponytail: board still works; unit filter stays empty until assets load */
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      listEvents()
        .then((e) => {
          if (cancelled) return;
          setAllEvents(e);
          setError(null);
          setLoaded(true);
        })
        .catch(() => !cancelled && setError("Could not reach the API."));
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  const events = useMemo(() => {
    if (!filters) return allEvents;
    return filterEvents(allEvents, filters);
  }, [allEvents, filters]);

  const filtersReady = filters != null && units.length > 0;

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      {filtersReady && (
        <EventFiltersSidebar units={units} filters={filters} onChange={setFilters} />
      )}
      <div className="w-full min-w-0 flex-1">
        <div className="mb-8 flex flex-wrap items-center gap-3">
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

        {loaded && allEvents.length === 0 && !error && (
          <div className="rounded border border-dashed border-border bg-card/40 p-10 text-center text-sm text-muted-foreground">
            No events yet. Fire one with{" "}
            <code className="text-primary">python scripts/simulate_event.py</code>.
          </div>
        )}

        {loaded && allEvents.length > 0 && events.length === 0 && !error && (
          <div className="rounded border border-dashed border-border bg-card/40 p-10 text-center text-sm text-muted-foreground">
            No events match filters.
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
