import { describe, expect, it } from "vitest";

import {
  ALL_CRITICALITIES,
  ALL_STATUSES,
  defaultFilters,
  filterEvents,
  type EventBoardFilters,
} from "./eventFilters";
import type { EventSummary } from "./api";

const baseEvent = (overrides: Partial<EventSummary> = {}): EventSummary =>
  ({
    id: 1,
    asset_tag: "P-3401",
    asset_name: "Pump",
    plant: "MT",
    unit: "Unit 300 — Specialty Esters",
    source: "simulated",
    symptom_category: "seal_leak",
    note: null,
    criticality: "A",
    status: "open",
    occurred_at: "2026-07-08T10:00:00Z",
    created_at: "2026-07-08T10:00:00Z",
    dossier_id: null,
    ...overrides,
  }) as EventSummary;

describe("eventFilters", () => {
  const units = [
    "Unit 100 — Solvent Recovery",
    "Unit 300 — Specialty Esters",
  ];

  it("default filters pass all events", () => {
    const events = [
      baseEvent(),
      baseEvent({ id: 2, criticality: "B", status: "closed", unit: units[0] }),
    ];
    expect(filterEvents(events, defaultFilters(units))).toHaveLength(2);
  });

  it("filters by criticality, status, and unit together", () => {
    const events = [
      baseEvent({ id: 1, criticality: "A", status: "open", unit: units[1] }),
      baseEvent({ id: 2, criticality: "B", status: "open", unit: units[1] }),
      baseEvent({ id: 3, criticality: "A", status: "closed", unit: units[0] }),
    ];
    const filters: EventBoardFilters = {
      criticalities: new Set(["A"]),
      statuses: new Set(["open"]),
      units: new Set([units[1]]),
    };
    expect(filterEvents(events, filters)).toEqual([events[0]]);
  });

  it("survives poll refresh — filter state applied to new fetch", () => {
    const filters = defaultFilters(units);
    const poll1 = [baseEvent({ id: 1 })];
    const poll2 = [baseEvent({ id: 1 }), baseEvent({ id: 2, criticality: "C" })];
    expect(filterEvents(poll1, filters)).toHaveLength(1);
    expect(filterEvents(poll2, filters)).toHaveLength(2);

    const strict: EventBoardFilters = {
      ...filters,
      criticalities: new Set(["A"]),
    };
    expect(filterEvents(poll2, strict)).toHaveLength(1);
  });

  it("exposes full default dimensions", () => {
    const filters = defaultFilters(units);
    expect(filters.criticalities.size).toBe(ALL_CRITICALITIES.length);
    expect(filters.statuses.size).toBe(ALL_STATUSES.length);
    expect(filters.units.size).toBe(units.length);
  });
});
