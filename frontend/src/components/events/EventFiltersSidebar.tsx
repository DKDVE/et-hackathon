import { cn } from "@/lib/utils";
import { criticalityBadgeClass, type Criticality } from "@/lib/criticality";
import {
  ALL_CRITICALITIES,
  ALL_STATUSES,
  toggleSet,
  type EventBoardFilters,
  type EventStatus,
} from "@/lib/eventFilters";

const criticalityFilters: { level: Criticality; label: string }[] = [
  { level: "A", label: "Critical" },
  { level: "B", label: "Warning" },
  { level: "C", label: "Advisory" },
];

const statusFilters: { value: EventStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "reviewed", label: "Reviewed" },
  { value: "closed", label: "Closed" },
];

type EventFiltersSidebarProps = {
  units: string[];
  filters: EventBoardFilters;
  onChange: (filters: EventBoardFilters) => void;
};

export function EventFiltersSidebar({ units, filters, onChange }: EventFiltersSidebarProps) {
  return (
    <aside className="w-full shrink-0 space-y-8 lg:w-64">
      <FilterGroup title="Criticality Level">
        {criticalityFilters.map(({ level, label }) => (
          <FilterCheckbox
            key={level}
            checked={filters.criticalities.has(level)}
            onChange={() =>
              onChange({
                ...filters,
                criticalities: toggleSet(filters.criticalities, level),
              })
            }
            label={
              <>
                <span className={cn("px-1.5 py-0.5", criticalityBadgeClass(level))}>
                  {level}
                </span>
                <span className="text-sm font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                  {label}
                </span>
              </>
            }
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Status">
        {statusFilters.map(({ value, label }) => (
          <FilterCheckbox
            key={value}
            checked={filters.statuses.has(value)}
            onChange={() =>
              onChange({
                ...filters,
                statuses: toggleSet(filters.statuses, value),
              })
            }
            label={
              <span className="text-sm font-medium capitalize text-muted-foreground transition-colors group-hover:text-foreground">
                {label}
              </span>
            }
          />
        ))}
      </FilterGroup>

      <FilterGroup title="Unit">
        {units.map((unit) => (
          <FilterCheckbox
            key={unit}
            checked={filters.units.has(unit)}
            onChange={() =>
              onChange({
                ...filters,
                units: toggleSet(filters.units, unit),
              })
            }
            label={
              <span className="text-sm font-medium text-muted-foreground transition-colors group-hover:text-foreground">
                {unit}
              </span>
            }
          />
        ))}
      </FilterGroup>
    </aside>
  );
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-muted-foreground">
        {title}
      </h3>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function FilterCheckbox({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: React.ReactNode;
}) {
  return (
    <label className="group flex cursor-pointer items-center gap-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="rounded border-border bg-card/50 text-primary focus:ring-primary focus:ring-offset-background"
      />
      <div className="flex items-center gap-2">{label}</div>
    </label>
  );
}

// ponytail: export for tests asserting default filter dimensions
export { ALL_CRITICALITIES, ALL_STATUSES };
