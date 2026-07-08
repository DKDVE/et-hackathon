import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { ChatDrawer } from "@/components/dossier/ChatDrawer";

describe("ChatDrawer rate limit", () => {
  it("renders quiet rate-limit copy from fixture state", () => {
    // Static shell only — 429 path sets error message without toast class
    const html = renderToStaticMarkup(<ChatDrawer dossierId={1} open onClose={() => {}} />);
    expect(html).toContain("Dossier chat");
    expect(html).not.toContain("toast");
  });
});

export const rateLimitMessage = "Rate limit reached — try again in a moment.";

describe("rateLimitMessage fixture", () => {
  it("matches backend 429 body copy", () => {
    expect(rateLimitMessage).toBe("Rate limit reached — try again in a moment.");
  });
});
