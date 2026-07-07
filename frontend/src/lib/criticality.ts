import { cn } from "@/lib/utils";

export type Criticality = "A" | "B" | "C";

const badgeStyles: Record<Criticality, string> = {
  A: "border-destructive/20 bg-destructive/10 text-destructive",
  B: "border-primary/20 bg-primary/10 text-primary",
  C: "border-sky-500/20 bg-sky-500/10 text-sky-500",
};

const accentStyles: Record<Criticality, string> = {
  A: "bg-destructive",
  B: "bg-primary",
  C: "bg-sky-500",
};

export function criticalityBadgeClass(level: Criticality): string {
  return cn(
    "rounded px-2 py-0.5 text-[10px] font-black uppercase",
    badgeStyles[level],
  );
}

export function criticalityAccentClass(level: Criticality): string {
  return accentStyles[level];
}
