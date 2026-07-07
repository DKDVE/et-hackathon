import type { ElementType } from "react";

export function SectionLabel({ icon: Icon, label }: { icon: ElementType; label: string }) {
  return (
    <div className="mb-5 flex items-center gap-2">
      <Icon className="size-4 text-muted-foreground" />
      <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
        {label}
      </h2>
    </div>
  );
}
