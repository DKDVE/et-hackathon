import { Badge } from "@/components/ui/badge";

type DossierHeroProps = {
  assetTag?: string;
  symptom?: string;
};

export function DossierHero({ assetTag = "P-3401", symptom = "Elevated vibration" }: DossierHeroProps) {
  return (
    <section className="-mx-6 mb-10 border-y border-border bg-card/50">
      <div className="mx-auto flex max-w-[90rem] flex-col items-start justify-between gap-4 px-6 py-8 md:flex-row md:items-end">
        <div>
          <h1 className="mb-2 text-3xl font-semibold tracking-tight">
            Asset {assetTag} · {symptom}
          </h1>
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="bg-primary/20 text-[10px] font-bold uppercase tracking-wider text-primary">
              Criticality A
            </Badge>
            <span className="border-l border-border pl-3 text-sm text-muted-foreground">
              Centrifugal Pump · Compression Area
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded border border-border bg-card px-4 py-3">
          <div className="size-2 rounded-full bg-primary pulse-amber" />
          <span className="text-sm font-medium text-primary">Assembling dossier...</span>
        </div>
      </div>
    </section>
  );
}
