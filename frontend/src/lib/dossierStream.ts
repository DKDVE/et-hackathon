import { useEffect, useReducer } from "react";

import { API_URL, getDossier, type DegradedInfo, type DossierResponse } from "./api";
import { withAccessQuery } from "./auth";

/**
 * The FULL SSE event vocabulary (TDD §7). The frontend implements all six now
 * so the M6 reasoning layer streams in without any frontend change; M5's server
 * only ever emits the deterministic subset (`context_ready` → `degraded`).
 */
export const SSE_EVENTS = [
  "context_ready",
  "analysis",
  "recommendation",
  "validated",
  "report_complete",
  "degraded",
] as const;

export type SseEventName = (typeof SSE_EVENTS)[number];

export type StreamPhase =
  | "connecting"
  | "context_ready"
  | "analyzing"
  | "recommending"
  | "validated"
  | "report_complete"
  | "degraded"
  | "error";

export type DossierState = {
  phase: StreamPhase;
  dossier: DossierResponse | null;
  // M6 reasoning slots — typed loosely until the reasoning schemas land.
  analysis: unknown | null;
  recommendation: unknown | null;
  validated: unknown | null;
  report: unknown | null;
  degraded: DegradedInfo | null;
};

export const initialDossierState: DossierState = {
  phase: "connecting",
  dossier: null,
  analysis: null,
  recommendation: null,
  validated: null,
  report: null,
  degraded: null,
};

export type SseEvent = { name: SseEventName; data: unknown };

/**
 * Pure reducer: fold one SSE event into dossier state. Handling every event
 * type — including `analysis`/`validated` — lives here so it is unit-testable
 * without a browser (acceptance criterion 2).
 */
export function dossierReducer(state: DossierState, event: SseEvent): DossierState {
  switch (event.name) {
    case "context_ready":
      return { ...state, phase: "context_ready", dossier: event.data as DossierResponse };
    case "analysis":
      return { ...state, phase: "analyzing", analysis: event.data };
    case "recommendation":
      return { ...state, phase: "recommending", recommendation: event.data };
    case "validated":
      return { ...state, phase: "validated", validated: event.data };
    case "report_complete": {
      const payload = event.data as DossierResponse | null;
      return {
        ...state,
        phase: "report_complete",
        report: event.data,
        dossier: payload?.dossier_id != null ? payload : state.dossier,
      };
    }
    case "degraded":
      return { ...state, phase: "degraded", degraded: event.data as DegradedInfo };
    default:
      return state;
  }
}

type EventSourceCtor = new (url: string) => EventSource;

/**
 * Wire an EventSource to a dossier stream, forwarding each named SSE frame to
 * `onEvent`. `onError` fires on transport failure (client falls back to polling,
 * TDD §12). The EventSource constructor is injectable for tests (EventSource
 * mock). Returns a cleanup function.
 */
export function subscribeDossier(
  dossierId: number | string,
  onEvent: (event: SseEvent) => void,
  onError: () => void,
  EventSourceImpl: EventSourceCtor = globalThis.EventSource,
): () => void {
  const es = new EventSourceImpl(withAccessQuery(`${API_URL}/api/dossiers/${dossierId}/stream`));
  for (const name of SSE_EVENTS) {
    es.addEventListener(name, (ev) => {
      const message = ev as MessageEvent;
      let data: unknown = null;
      try {
        data = message.data ? JSON.parse(message.data) : null;
      } catch {
        data = null;
      }
      onEvent({ name, data });
    });
  }
  es.onerror = () => {
    es.close();
    onError();
  };
  return () => es.close();
}

const TERMINAL: StreamPhase[] = ["degraded", "report_complete"];

/**
 * Subscribe to a dossier's SSE stream; on disconnect, fall back to polling
 * `GET /api/dossiers/{id}` every 5s until a terminal phase (TDD §12).
 */
export function useDossierStream(dossierId: number | string | null): DossierState {
  const [state, dispatch] = useReducer(dossierReducer, initialDossierState);

  useEffect(() => {
    if (dossierId == null) return;
    let cancelled = false;
    let poll: ReturnType<typeof setInterval> | null = null;

    const pollOnce = async () => {
      try {
        const dossier = await getDossier(dossierId);
        if (cancelled) return;
        dispatch({ name: "context_ready", data: dossier });
        if (dossier.degraded) dispatch({ name: "degraded", data: dossier.degraded });
        if (dossier.degraded && poll) {
          clearInterval(poll);
          poll = null;
        }
      } catch {
        /* keep polling */
      }
    };

    const startPolling = () => {
      if (poll || cancelled) return;
      void pollOnce();
      poll = setInterval(pollOnce, 5000);
    };

    const stop = subscribeDossier(
      dossierId,
      (event) => !cancelled && dispatch(event),
      startPolling,
    );

    return () => {
      cancelled = true;
      if (poll) clearInterval(poll);
      stop();
    };
  }, [dossierId]);

  return state;
}

/** True once the deterministic dossier is available (progressive render, P5). */
export const isContextReady = (s: DossierState): boolean =>
  s.dossier?.context != null;

/** True when the stream ended degraded (M5: reasoning layer not enabled). */
export const isDegraded = (s: DossierState): boolean => s.phase === "degraded";

export const isTerminal = (s: DossierState): boolean => TERMINAL.includes(s.phase);
