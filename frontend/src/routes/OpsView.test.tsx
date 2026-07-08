import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";

import { TraceRunTable } from "@/components/ops/TraceRunTable";
import { OpsView } from "@/routes/OpsView";

const runsFixture = [
  {
    id: 1,
    node: "analysis",
    model: "anthropic/claude-sonnet-4.6",
    prompt_version: "analysis-v4",
    started_at: "2026-07-08T12:00:00Z",
    latency_ms: 4200,
    prompt_tokens: 8000,
    completion_tokens: 400,
    status: "repaired",
    dossier_id: 5,
    event_id: 12,
  },
];

describe("TraceRunTable", () => {
  it("highlights repaired status", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <TraceRunTable runs={runsFixture} showDossierLink />
      </MemoryRouter>,
    );
    expect(html).toContain("repaired");
    expect(html).toContain("text-amber-500");
    expect(html).toContain("/events/12");
  });

  it("shows empty state guidance", () => {
    const html = renderToStaticMarkup(<TraceRunTable runs={[]} />);
    expect(html).toContain("No reasoning runs yet");
  });
});

describe("OpsView tabs", () => {
  it("renders three tab labels from static shell", () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <OpsView />
      </MemoryRouter>,
    );
    expect(html).toContain("Runs");
    expect(html).toContain("Evals");
    expect(html).toContain("Guardrails");
    expect(html).toContain("Read-only AI ops");
  });
});
