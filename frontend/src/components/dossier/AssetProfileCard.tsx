import type { AssetProfile } from "@/lib/api";
import { PidReferenceBlock } from "@/components/dossier/PidReferenceBlock";
import { Card, CardContent } from "@/components/ui/card";

export function AssetProfileCard({ profile }: { profile: AssetProfile }) {
  const fields: [string, string | number][] = [
    ["Asset Tag", profile.tag],
    ["Name", profile.name],
    ["Class", profile.asset_class],
    ["Manufacturer", profile.manufacturer],
    ["Model", profile.model],
    ["Plant", profile.plant],
    ["Unit", profile.unit],
    ["Area", profile.area],
    ["Service Duty", profile.service_duty],
  ];
  return (
    <Card className="overflow-hidden border-border">
      <div className="border-b border-border bg-card/80 px-6 py-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          Asset Profile
        </h3>
      </div>
      <CardContent className="space-y-0 p-6">
        {fields.map(([label, value], i) => (
          <div
            key={label}
            className={`flex items-center justify-between gap-4 py-2 text-sm ${
              i < fields.length - 1 ? "border-b border-border/50" : ""
            }`}
          >
            <span className="shrink-0 text-muted-foreground">{label}</span>
            <span className="text-right font-medium">{value}</span>
          </div>
        ))}
        <div className="flex items-center justify-between border-t border-border/50 py-2 pt-3 text-sm">
          <span className="text-muted-foreground">Criticality</span>
          <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
            {profile.criticality}
          </span>
        </div>
        <div className="pt-4">
          <PidReferenceBlock assetId={profile.asset_id} />
        </div>
      </CardContent>
    </Card>
  );
}
