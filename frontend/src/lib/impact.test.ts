import { describe, expect, it } from "vitest";

import { downtimeImpactInr, formatInrImpact } from "./impact";

describe("impact", () => {
  it("formats crores and lakhs", () => {
    expect(formatInrImpact(44_595_000)).toBe("₹4.5Cr");
    expect(formatInrImpact(18_450_000)).toBe("₹1.8Cr");
    expect(formatInrImpact(450_000)).toBe("₹4.5L");
  });

  it("computes downtime impact", () => {
    expect(downtimeImpactInr(99.1, 450_000)).toBeCloseTo(44_595_000, 0);
    expect(downtimeImpactInr(41, 450_000)).toBe(18_450_000);
  });
});
