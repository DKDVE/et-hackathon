import type { ElementType } from "react";
import {
  BarChart3,
  Brain,
  ChevronUp,
  ClipboardList,
  FileText,
  GitBranch,
  History,
  MessageSquare,
  Shield,
} from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function SectionLabel({ icon: Icon, label }: { icon: ElementType; label: string }) {
  return (
    <div className="mb-6 flex items-center gap-2">
      <Icon className="size-4 text-muted-foreground" />
      <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
        {label}
      </h2>
    </div>
  );
}

function SkeletonLines({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton
          key={i}
          className="h-4"
          style={{ width: `${Math.max(60, 100 - i * 8)}%` }}
        />
      ))}
    </div>
  );
}

export function DossierMainColumn() {
  return (
    <div className="flex flex-col gap-10 lg:col-span-8">
      <section>
        <div className="rounded-r border-l-4 border-primary bg-card p-6">
          <div className="mb-4 flex items-center gap-2 text-primary">
            <Shield className="size-4" />
            <h2 className="text-xs font-bold uppercase tracking-widest">Safety Notes</h2>
          </div>
          <p className="mb-4 text-sm font-medium text-muted-foreground italic">
            Awaiting reasoning...
          </p>
          <SkeletonLines count={3} />
        </div>
      </section>

      <section>
        <SectionLabel icon={Brain} label="Probable Causes" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="rounded border border-dashed border-border bg-card/50 p-4 transition-colors hover:border-muted-foreground"
            >
              <Skeleton className="mb-4 h-3 w-1/2" />
              <SkeletonLines count={3} />
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionLabel icon={ClipboardList} label="Recommended Actions" />
        <div className="space-y-4">
          {["01", "02", "03"].map((num) => (
            <div
              key={num}
              className="flex items-start gap-4 rounded border border-border bg-card/50 p-4"
            >
              <div className="flex size-8 shrink-0 items-center justify-center rounded bg-muted text-xs font-bold text-muted-foreground">
                {num}
              </div>
              <div className="min-w-0 grow space-y-2">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-3 w-full" />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <SectionLabel icon={History} label="Failure History" />
        <div className="relative ml-3 space-y-8 border-l border-border pl-8">
          {[1, 2, 3].map((n) => (
            <div key={n} className="relative">
              <div className="absolute -left-[2.35rem] top-0 size-4 rounded-full border-2 border-border bg-card" />
              <Skeleton className="mb-2 h-4 w-48" />
              <Skeleton className="h-3 w-5/6" />
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        <section>
          <SectionLabel icon={GitBranch} label="Similar Incidents" />
          <div className="space-y-4">
            {[1, 2].map((n) => (
              <div
                key={n}
                className="flex gap-4 rounded border border-border bg-card p-4"
              >
                <Skeleton className="size-12 shrink-0 rounded" />
                <div className="min-w-0 grow space-y-2 pt-1">
                  <Skeleton className="h-3 w-2/3" />
                  <Skeleton className="h-2 w-full" />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="flex flex-col justify-between rounded border border-border bg-primary/5 p-6">
          <div>
            <div className="mb-6 flex items-center gap-2 text-muted-foreground">
              <BarChart3 className="size-4" />
              <h2 className="text-xs font-bold uppercase tracking-widest">
                Cross-asset pattern reveal
              </h2>
            </div>
            <div className="mb-4 grid grid-cols-3 gap-4">
              {["Count", "Months", "Downtime"].map((label) => (
                <div key={label} className="text-center">
                  <Skeleton className="mx-auto mb-2 h-6 w-full" />
                  <span className="text-[10px] font-bold uppercase text-muted-foreground">
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="flex h-24 items-center justify-center rounded border border-border bg-card/50">
            <BarChart3 className="size-10 text-muted-foreground/40" />
          </div>
        </section>
      </div>
    </div>
  );
}

export function DossierSidebar() {
  const profileFields = [
    ["Asset Tag", "P-3401"],
    ["Class", "Centrifugal Pump"],
    ["Plant", "Houston SE"],
    ["Unit", "Ethylene-1"],
    ["Criticality", "A"],
  ] as const;

  return (
    <aside className="flex flex-col gap-10 lg:col-span-4">
      <Card className="overflow-hidden border-border">
        <div className="border-b border-border bg-card/80 px-6 py-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Asset Profile
          </h3>
        </div>
        <CardContent className="space-y-0 p-6">
          {profileFields.map(([label, value], i) => (
            <div
              key={label}
              className={`flex items-center justify-between py-2 text-sm ${
                i < profileFields.length - 1 ? "border-b border-border/50" : ""
              }`}
            >
              <span className="text-muted-foreground">{label}</span>
              {label === "Criticality" ? (
                <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                  {value}
                </span>
              ) : (
                <span className="font-medium tabular-nums">{value}</span>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <div>
        <div className="mb-2 flex items-center gap-2">
          <FileText className="size-4 text-muted-foreground" />
          <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
            Document Extracts
          </h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="group flex cursor-pointer items-center gap-3 rounded border border-border bg-card/50 p-3 transition-colors hover:border-muted-foreground"
            >
              <FileText className="size-4 text-muted-foreground group-hover:text-primary" />
              <Skeleton className="h-3 grow" style={{ width: `${80 - n * 10}%` }} />
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}

export function DossierChatDrawer() {
  return (
    <div className="fixed right-0 bottom-0 z-40 w-full px-4 md:right-8 md:w-80 md:px-0">
      <button
        type="button"
        disabled
        className="flex w-full items-center justify-between rounded-t-xl bg-primary px-6 py-4 text-primary-foreground shadow-2xl transition-all hover:bg-primary/90 disabled:opacity-90"
      >
        <div className="flex items-center gap-3">
          <MessageSquare className="size-5" />
          <span className="text-sm font-bold tracking-tight">Ask about this dossier</span>
        </div>
        <ChevronUp className="size-5" />
      </button>
    </div>
  );
}
