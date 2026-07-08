import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";

import { MemoryView } from "@/routes/MemoryView";

vi.mock("@/lib/api", () => ({
  getMemoryOverview: () =>
    Promise.resolve({
      asset_count: 40,
      document_count: 60,
      chunk_count: 200,
      work_order_count: 500,
      wo_auto_classified: 440,
      wo_unclassified: 60,
      wo_human_reviewed: 0,
      taxonomy_size: 25,
    }),
  getMemoryAssets: () =>
    Promise.resolve({
      assets: [
        {
          asset_id: 1,
          tag: "P-3401",
          name: "Charge Pump",
          asset_class: "CP200",
          manual_available: true,
          sop_count: 2,
          wo_count: 20,
          last_inspection_date: "2025-01-01",
          classified_ratio: 0.85,
          coverage_tier: "Good",
        },
      ],
      coverage_footnote: "Good: OEM manual on class + ≥1 SOP + ≥5 WOs + ≥70% classified.",
    }),
  getMemoryDocuments: () =>
    Promise.resolve([
      {
        document_id: 1,
        title: "OEM Manual",
        doc_type: "oem_manual",
        owner_asset_tag: null,
        owner_class: "CP200",
        chunk_count: 42,
        ocr_page_count: 10,
        file_url: "/api/sources/file/1",
      },
    ]),
  getMemoryTaxonomy: () =>
    Promise.resolve([
      {
        family: "seal",
        modes: [
          {
            mode_id: 1,
            code: "mechanical_seal_leakage",
            name: "Mechanical seal leakage",
            auto_wo_count: 12,
            human_override_count: 0,
            mean_normalization_score: 0.72,
          },
        ],
      },
    ]),
  getMemoryReviewQueue: () =>
    Promise.resolve([
      {
        wo_id: 99,
        wo_number: "WO-2024-0001",
        asset_tag: "P-1001",
        raw_description: "Pump noisy",
        auto_failure_mode_code: "bearing_failure",
        auto_failure_mode_family: "bearing",
        normalization_score: 0.56,
        candidates: [
          { mode_id: 1, code: "bearing_failure", name: "Bearing failure", score: 0.56 },
        ],
      },
    ]),
  submitReviewVerdict: () => Promise.resolve({}),
}));

describe("MemoryView tabs", () => {
  it("renders five tab labels from fixture shell", async () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <MemoryView />
      </MemoryRouter>,
    );
    expect(html).toContain("Overview");
    expect(html).toContain("Assets");
    expect(html).toContain("Documents");
    expect(html).toContain("Taxonomy");
    expect(html).toContain("Review Queue");
    expect(html).toContain("Operational Memory");
  });
});
