import { BarChart3 } from "lucide-react";

import type { AppConfig, PatternStat } from "@/lib/api";
import { downtimeImpactInr, formatInrImpact } from "@/lib/impact";
import { cn } from "@/lib/utils";

function humanizeMode(code: string): string {
  return code.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * FR-12 / D-018 / D-021 — cross-asset pattern reveal with ₹ impact.
 * Both rows render peer-level; verbatim phrasings are the vocabulary exhibit.
 */
export function PatternPanel({
  patterns,
  config,
}: {
  patterns: PatternStat[];
  config: AppConfig | null;
}) {
  const costPerHr = config?.downtime_cost_per_hour_inr ?? 450_000;
  const costLabel = config?.downtime_cost_label ?? "₹4.5L/hr";

  return (
    <section className="rounded-lg border border-primary/20 bg-primary/5 p-6">
      <div className="mb-5 flex items-center gap-2 text-primary">
        <BarChart3 className="size-4" />
        <h2 className="text-xs font-bold uppercase tracking-widest">
          Cross-Asset Pattern Reveal
        </h2>
      </div>
      {patterns.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No recurring failure pattern across sister assets for this symptom.
        </p>
      ) : (
        <div className="space-y-4">
          {patterns.map((p) => {
            const impact = downtimeImpactInr(p.total_downtime_hours, costPerHr);
            return (
              <div
                key={p.failure_mode}
                className="rounded-lg border border-primary/30 bg-card/60 p-5"
              >
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-base font-semibold">{humanizeMode(p.failure_mode)}</div>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {p.asset_tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-semibold tabular-nums text-muted-foreground"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-center sm:grid-cols-4">
                    <Stat value={p.occurrences} label="Occurrences" />
                    <Stat value={p.span_months} label="Months" />
                    <Stat value={`${p.total_downtime_hours}h`} label="Downtime" emphasis />
                    <Stat
                      value={`≈ ${formatInrImpact(impact)}`}
                      label="Est. impact"
                      emphasis
                    />
                  </div>
                </div>
                {p.distinct_phrasings.length > 0 && (
                  <div className="border-t border-border/50 pt-3">
                    <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                      Distinct field phrasings ({p.distinct_phrasings.length})
                    </div>
                    <ul className="space-y-1.5">
                      {p.distinct_phrasings.map((phrase) => (
                        <li
                          key={phrase}
                          className="border-l-2 border-primary/40 pl-3 text-sm italic text-foreground/90"
                        >
                          “{phrase}”
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })}
          <p className="text-[11px] text-muted-foreground">
            Estimated at configured downtime cost of {costLabel}
          </p>
        </div>
      )}
    </section>
  );
}

function Stat({
  value,
  label,
  emphasis,
}: {
  value: string | number;
  label: string;
  emphasis?: boolean;
}) {
  return (
    <div>
      <div className={cn("text-xl font-bold tabular-nums", emphasis && "text-primary")}>
        {value}
      </div>
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
    </div>
  );
}
