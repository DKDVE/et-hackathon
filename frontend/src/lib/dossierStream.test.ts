import { describe, expect, it, vi } from "vitest";

import {
  SSE_EVENTS,
  type SseEvent,
  dossierReducer,
  initialDossierState,
  subscribeDossier,
} from "./dossierStream";

describe("dossierReducer", () => {
  it("handles the full SSE vocabulary, including analysis and validated", () => {
    const frames: SseEvent[] = [
      { name: "context_ready", data: { dossier_id: 1, context: { asset_profile: { tag: "P-3401" } } } },
      { name: "analysis", data: { probable_causes: [{ statement: "seal wear" }] } },
      { name: "recommendation", data: { actions: [{ text: "replace cartridge" }] } },
      { name: "validated", data: { grounding: "evidenced" } },
      { name: "report_complete", data: { ok: true } },
    ];
    const state = frames.reduce(dossierReducer, initialDossierState);
    expect(state.phase).toBe("report_complete");
    expect((state.dossier as any).dossier_id).toBe(1);
    expect((state.analysis as any).probable_causes[0].statement).toBe("seal wear");
    expect((state.recommendation as any).actions[0].text).toBe("replace cartridge");
    expect((state.validated as any).grounding).toBe("evidenced");
    expect(state.report).toEqual({ ok: true });
  });

  it("degraded{reasoning_disabled} sets the degraded phase", () => {
    const state = dossierReducer(initialDossierState, {
      name: "degraded",
      data: { reason: "reasoning_disabled", deterministic_available: true },
    });
    expect(state.phase).toBe("degraded");
    expect(state.degraded?.reason).toBe("reasoning_disabled");
  });

  it("M5 sequence: context_ready then degraded", () => {
    let state = dossierReducer(initialDossierState, {
      name: "context_ready",
      data: { dossier_id: 7, context: {} },
    });
    state = dossierReducer(state, {
      name: "degraded",
      data: { reason: "reasoning_disabled", deterministic_available: true },
    });
    expect(state.dossier).not.toBeNull();
    expect(state.phase).toBe("degraded");
  });
});

/** Minimal EventSource mock: records listeners and lets the test emit frames. */
class MockEventSource {
  url: string;
  listeners: Record<string, (ev: MessageEvent) => void> = {};
  onerror: (() => void) | null = null;
  closed = false;
  constructor(url: string) {
    this.url = url;
  }
  addEventListener(name: string, cb: (ev: MessageEvent) => void) {
    this.listeners[name] = cb;
  }
  emit(name: string, data: unknown) {
    this.listeners[name]?.({ data: JSON.stringify(data) } as MessageEvent);
  }
  fail() {
    this.onerror?.();
  }
  close() {
    this.closed = true;
  }
}

describe("subscribeDossier", () => {
  it("registers every event type and forwards parsed frames", () => {
    let created: MockEventSource | null = null;
    const Impl = class extends MockEventSource {
      constructor(url: string) {
        super(url);
        created = this;
      }
    } as unknown as new (url: string) => EventSource;

    const received: SseEvent[] = [];
    const stop = subscribeDossier(42, (e) => received.push(e), () => {}, Impl);

    const es = created as unknown as MockEventSource;
    expect(es.url).toContain("/api/dossiers/42/stream");
    for (const name of SSE_EVENTS) expect(es.listeners[name]).toBeDefined();

    es.emit("context_ready", { dossier_id: 42 });
    es.emit("analysis", { probable_causes: [] });
    es.emit("validated", { grounding: "hypothesis" });
    expect(received.map((r) => r.name)).toEqual(["context_ready", "analysis", "validated"]);
    expect((received[0].data as any).dossier_id).toBe(42);

    stop();
    expect(es.closed).toBe(true);
  });

  it("invokes onError (polling fallback) on transport failure", () => {
    let created: MockEventSource | null = null;
    const Impl = class extends MockEventSource {
      constructor(url: string) {
        super(url);
        created = this;
      }
    } as unknown as new (url: string) => EventSource;

    const onError = vi.fn();
    subscribeDossier(1, () => {}, onError, Impl);
    (created as unknown as MockEventSource).fail();
    expect(onError).toHaveBeenCalledOnce();
  });
});
