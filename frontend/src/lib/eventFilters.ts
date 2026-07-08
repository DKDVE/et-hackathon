import type { EventSummary } from "./api";

export type EventStatus = "open" | "reviewed" | "closed";
export type Criticality = "A" | "B" | "C";

export type EventBoardFilters = {
  criticalities: Set<Criticality>;
  statuses: Set<EventStatus>;
  units: Set<string>;
};

export const ALL_CRITICALITIES: Criticality[] = ["A", "B", "C"];
export const ALL_STATUSES: EventStatus[] = ["open", "reviewed", "closed"];

export function defaultFilters(units: string[]): EventBoardFilters {
  return {
    criticalities: new Set(ALL_CRITICALITIES),
    statuses: new Set(ALL_STATUSES),
    units: new Set(units),
  };
}

/** Client-side board filter; empty set in a dimension means "show none". */
export function filterEvents(
  events: EventSummary[],
  filters: EventBoardFilters,
): EventSummary[] {
  return events.filter(
    (e) =>
      filters.criticalities.has(e.criticality as Criticality) &&
      filters.statuses.has(e.status as EventStatus) &&
      filters.units.has(e.unit),
  );
}

export function distinctUnits(assets: { unit: string }[]): string[] {
  return [...new Set(assets.map((a) => a.unit))].sort();
}

export function toggleSet<T>(set: Set<T>, value: T): Set<T> {
  const next = new Set(set);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}
