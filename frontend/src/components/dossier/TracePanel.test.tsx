import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { TracePanel } from "@/components/dossier/TracePanel";
import type { ReasoningRunsResponse } from "@/lib/api";

const reasonedFixture: ReasoningRunsResponse = {
  runs: [
    {
      id: 1,
      node: "analysis",
      model: "anthropic/claude-sonnet-4.6",
      prompt_version: "analysis-v3",
      started_at: "2026-07-08T12:00:00Z",
      latency_ms: 4200,
      prompt_tokens: 8000,
      completion_tokens: 400,
      status: "ok",
    },
    {
      id: 2,
      node: "chat",
      model: "anthropic/claude-haiku-4.5",
      prompt_version: "chat-v1",
      started_at: "2026-07-08T12:01:00Z",
      latency_ms: 900,
      prompt_tokens: 1200,
      completion_tokens: 150,
      status: "ok",
    },
  ],
  replayed_from_cache: false,
  total_latency_ms: 5100,
  total_prompt_tokens: 9200,
  total_completion_tokens: 550,
  estimated_cost_usd: 0.0312,
  cost_footnote: "Estimated at configured per-model token rates (USD per 1M tokens).",
};

const deterministicFixture: ReasoningRunsResponse = {
  runs: [],
  replayed_from_cache: false,
  total_latency_ms: 0,
  total_prompt_tokens: 0,
  total_completion_tokens: 0,
  estimated_cost_usd: 0,
  cost_footnote: "Estimated at configured per-model token rates (USD per 1M tokens).",
};

describe("TracePanel", () => {
  it("renders per-node rows, totals, and cost footnote from fixture", () => {
    const html = renderToStaticMarkup(<TracePanel trace={reasonedFixture} />);
    expect(html).toContain("analysis");
    expect(html).toContain("chat");
    expect(html).toContain("5100 ms");
    expect(html).toContain("9750");
    expect(html).toContain("$0.03");
    expect(html).toContain("per-model token rates");
  });

  it("renders deterministic empty state", () => {
    const html = renderToStaticMarkup(<TracePanel trace={deterministicFixture} />);
    expect(html).toContain("No reasoning runs");
    expect(html).toContain("deterministic dossier");
  });

  it("shows cache replay note when flagged", () => {
    const html = renderToStaticMarkup(
      <TracePanel trace={{ ...reasonedFixture, replayed_from_cache: true }} />,
    );
    expect(html).toContain("Replayed from cache");
  });
});
