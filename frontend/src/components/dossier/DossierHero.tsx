import { CheckCircle2, Loader2 } from "lucide-react";

import type { DegradedInfo, SharedContext } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

const SYMPTOM_LABEL: Record<string, string> = {
  seal_leak: "Seal Leak",
  vibration: "Elevated Vibration",
  overheating: "Overheating",
  pressure_anomaly: "Pressure Anomaly",
  abnormal_noise: "Abnormal Noise",
  trip: "Trip",
  low_flow: "Low Flow",
  other: "General Review",
};

export function DossierHero({
  context,
  degraded,
}: {
  context: SharedContext | null;
  degraded: DegradedInfo | null;
}) {
  const asset = context?.asset_profile;
  const event = context?.event;
  const symptom = event ? SYMPTOM_LABEL[event.symptom_category] ?? event.symptom_category : "";

  return (
    <section className="-mx-6 mb-10 border-y border-border bg-card/50">
      <div className="mx-auto flex max-w-[90rem] flex-col items-start justify-between gap-4 px-6 py-8 md:flex-row md:items-end">
        <div>
          <h1 className="mb-2 text-3xl font-semibold tracking-tight">
            {asset ? `Asset ${asset.tag} · ${symptom}` : "Assembling dossier…"}
          </h1>
          {asset && event && (
            <div className="flex flex-wrap items-center gap-3">
              <Badge className="bg-primary/20 text-[10px] font-bold uppercase tracking-wider text-primary">
                Criticality {event.criticality}
              </Badge>
              <span className="border-l border-border pl-3 text-sm text-muted-foreground">
                {asset.asset_class} · {asset.plant} · {asset.unit}
              </span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3 rounded border border-border bg-card px-4 py-3">
          {context ? (
            <>
              <CheckCircle2 className="size-4 text-emerald-500" />
              <span className="text-sm font-medium text-emerald-500">
                {degraded ? "Context ready · reasoning off" : "Context ready"}
              </span>
            </>
          ) : (
            <>
              <Loader2 className="size-4 animate-spin text-primary" />
              <span className="text-sm font-medium text-primary">Assembling…</span>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
