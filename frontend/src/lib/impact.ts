/** Format downtime impact in Indian numbering (Cr / L). */
export function formatInrImpact(amountInr: number): string {
  if (amountInr >= 10_000_000) {
    return `₹${(amountInr / 10_000_000).toFixed(1)}Cr`;
  }
  if (amountInr >= 100_000) {
    return `₹${(amountInr / 100_000).toFixed(1)}L`;
  }
  return `₹${Math.round(amountInr).toLocaleString("en-IN")}`;
}

export function downtimeImpactInr(hours: number, costPerHour: number): number {
  return hours * costPerHour;
}
