import { cn } from "@/lib/utils";
import { criticalityBadgeClass, type Criticality } from "@/lib/criticality";

const criticalityFilters: { level: Criticality; label: string }[] = [
  { level: "A", label: "Critical" },
  { level: "B", label: "Warning" },
  { level: "C", label: "Advisory" },
];

const unitFilters = ["Ethylene-1", "Ethylene-2", "Utilities", "Storage"] as const;

export function EventFiltersSidebar() {
  return (
    <aside className="w-full shrink-0 space-y-8 lg:w-64">
      <div>
        <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Criticality Level
        </h3>
        <div className="space-y-2">
          {criticalityFilters.map(({ level, label }) => (
            <label
              key={level}
              className="group flex cursor-pointer items-center gap-3"
            >
              <input
                type="checkbox"
                defaultChecked
                className="rounded border-border bg-card/50 text-primary focus:ring-primary focus:ring-offset-background"
              />
              <div className="flex items-center gap-2">
                <span className={cn("px-1.5 py-0.5", criticalityBadgeClass(level))}>
                  {level}
                </span>
                <span className="text-sm font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                  {label}
                </span>
              </div>
            </label>
          ))}
        </div>
      </div>
      <div>
        <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Unit
        </h3>
        <div className="space-y-2">
          {unitFilters.map((unit, i) => (
            <label key={unit} className="group flex cursor-pointer items-center gap-3">
              <input
                type="checkbox"
                defaultChecked={i < 2}
                className="rounded border-border bg-card/50 text-primary focus:ring-primary focus:ring-offset-background"
              />
              <span className="text-sm font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                {unit}
              </span>
            </label>
          ))}
        </div>
      </div>
    </aside>
  );
}
