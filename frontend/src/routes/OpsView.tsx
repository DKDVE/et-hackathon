import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { CostRollupCards, TraceRunTable } from "@/components/ops/TraceRunTable";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  getOpsCosts,
  getOpsEvals,
  getOpsGuardrails,
  getOpsRuns,
  type EvalRunRow,
  type GuardrailsResponse,
  type OpsCostsResponse,
  type OpsRunRow,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "runs" | "evals" | "guardrails";

const TABS: { id: Tab; label: string }[] = [
  { id: "runs", label: "Runs" },
  { id: "evals", label: "Evals" },
  { id: "guardrails", label: "Guardrails" },
];

function suiteMetric(row: EvalRunRow): string {
  const m = row.metrics;
  switch (row.suite) {
    case "golden":
      return `${m.passed ?? 0} passed / ${m.failed ?? 0} failed`;
    case "normalization":
      return `acc ${((m.accuracy as number) * 100).toFixed(1)}%`;
    case "groundedness":
    case "prose_id":
      return `${m.violations ?? 0} violations`;
    case "timing":
      return `${m.t_analysis_s ?? "?"}s analysis`;
    default:
      return JSON.stringify(m);
  }
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider",
        status === "pass" && "bg-emerald-500/15 text-emerald-500",
        status === "warn" && "bg-amber-500/15 text-amber-500",
        status === "fail" && "bg-destructive/15 text-destructive",
      )}
    >
      {status}
    </span>
  );
}

function RunsTab() {
  const [runs, setRuns] = useState<OpsRunRow[]>([]);
  const [costs, setCosts] = useState<OpsCostsResponse | null>(null);
  const [node, setNode] = useState("");
  const [model, setModel] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (node.trim()) params.set("node", node.trim());
    if (model.trim()) params.set("model", model.trim());
    const qs = params.toString();
    Promise.all([
      getOpsRuns(qs ? `?${qs}` : ""),
      getOpsCosts(),
    ])
      .then(([r, c]) => {
        setRuns(r.runs);
        setCosts(c);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      {costs && (
        <section className="rounded-lg border border-border bg-card/40 p-6">
          <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-primary">
            Cost roll-up
          </h3>
          <CostRollupCards
            todayUsd={costs.today_estimated_cost_usd}
            totalUsd={costs.total_estimated_cost_usd}
            byModel={costs.by_model}
            footnote={costs.cost_footnote}
          />
        </section>
      )}
      <section className="rounded-lg border border-border bg-card/40 p-6">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-[10px] font-bold uppercase text-muted-foreground">
              Node
            </label>
            <Input
              value={node}
              onChange={(e) => setNode(e.target.value)}
              placeholder="analysis"
              className="h-8 w-32"
            />
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-bold uppercase text-muted-foreground">
              Model
            </label>
            <Input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="claude-sonnet"
              className="h-8 w-48"
            />
          </div>
          <Button type="button" size="sm" onClick={load} disabled={loading}>
            Filter
          </Button>
        </div>
        <TraceRunTable runs={runs} showDossierLink />
      </section>
    </div>
  );
}

function EvalsTab() {
  const [history, setHistory] = useState<EvalRunRow[]>([]);
  const [latest, setLatest] = useState<Record<string, EvalRunRow | null>>({});
  const [selectedSuite, setSelectedSuite] = useState<string | null>(null);

  useEffect(() => {
    getOpsEvals().then((data) => {
      setHistory(data.history);
      setLatest(data.latest_by_suite);
    });
  }, []);

  const suiteHistory = useMemo(
    () =>
      selectedSuite
        ? history.filter((r) => r.suite === selectedSuite)
        : [],
    [history, selectedSuite],
  );

  const suites = Object.keys(latest);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {suites.map((suite) => {
          const row = latest[suite];
          return (
            <button
              key={suite}
              type="button"
              onClick={() => setSelectedSuite(suite)}
              className={cn(
                "rounded-lg border p-4 text-left transition-colors",
                selectedSuite === suite
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card/40 hover:border-primary/40",
              )}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-xs font-bold uppercase tracking-wider">{suite}</span>
                {row ? <StatusBadge status={row.status} /> : <span className="text-xs text-muted-foreground">—</span>}
              </div>
              {row ? (
                <p className="text-sm tabular-nums">{suiteMetric(row)}</p>
              ) : (
                <p className="text-sm text-muted-foreground">No runs — run make evals</p>
              )}
            </button>
          );
        })}
      </section>

      <section className="rounded-lg border border-border bg-card/40 p-6">
        <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-primary">
          {selectedSuite ? `${selectedSuite} history` : "Eval history"}
        </h3>
        {!selectedSuite && (
          <p className="text-sm text-muted-foreground">
            Select a suite card to see metric drift across git refs and prompt versions.
          </p>
        )}
        {selectedSuite && suiteHistory.length === 0 && (
          <p className="text-sm text-muted-foreground">No history for this suite yet.</p>
        )}
        {selectedSuite && suiteHistory.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[10px] uppercase text-muted-foreground">
                  <th className="py-2 pr-4">When</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2 pr-4">Git</th>
                  <th className="py-2 pr-4">Prompts</th>
                  <th className="py-2">Metric</th>
                </tr>
              </thead>
              <tbody>
                {suiteHistory.map((row) => (
                  <tr key={row.id} className="border-b border-border/50">
                    <td className="py-2 pr-4 tabular-nums text-xs">
                      {new Date(row.started_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs">{row.git_ref}</td>
                    <td className="py-2 pr-4 font-mono text-[10px] text-muted-foreground">
                      {Object.entries(row.prompt_versions)
                        .map(([k, v]) => `${k}:${v}`)
                        .join(" · ")}
                    </td>
                    <td className="py-2 tabular-nums">{suiteMetric(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function GuardrailsTab() {
  const [data, setData] = useState<GuardrailsResponse | null>(null);

  useEffect(() => {
    getOpsGuardrails().then(setData);
  }, []);

  if (!data) {
    return <p className="text-sm text-muted-foreground">Loading guardrail stats…</p>;
  }

  const t = data.fleet_totals;

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Structural guardrails — enforced in code, measured per dossier.
      </p>
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {(
          [
            ["Citations stripped (S1)", t.stage1_stripped_citations],
            ["Unsupported removed (S2)", t.stage2_unsupported_removed],
            ["Hypothesis claims", t.hypothesis_claims],
            ["Safety notes deleted", t.safety_notes_deleted],
            ["Chat citations stripped", t.chat_citations_stripped],
          ] as const
        ).map(([label, n]) => (
          <div key={label} className="rounded-lg border border-border bg-card/40 p-4">
            <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              {label}
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-primary">{n}</div>
          </div>
        ))}
      </section>
      {data.not_recorded_count > 0 && (
        <p className="text-xs text-muted-foreground">
          {data.not_recorded_count} completed dossier(s) with guardrail stats not recorded
          (pre-M11).
        </p>
      )}
      <section className="rounded-lg border border-border bg-card/40 p-6">
        <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-primary">
          Per dossier
        </h3>
        {data.dossiers.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No guardrail stats yet. Complete a reasoning dossier to populate measurements.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[10px] uppercase text-muted-foreground">
                  <th className="py-2 pr-4">Dossier</th>
                  <th className="py-2 pr-4">S1</th>
                  <th className="py-2 pr-4">S2</th>
                  <th className="py-2 pr-4">Hypothesis</th>
                  <th className="py-2 pr-4">Safety del.</th>
                  <th className="py-2">Chat strip</th>
                </tr>
              </thead>
              <tbody>
                {data.dossiers.map((d) => (
                  <tr key={d.dossier_id} className="border-b border-border/50">
                    <td className="py-2 pr-4">
                      <Link
                        to={`/events/${d.event_id}`}
                        className="font-medium text-primary hover:underline"
                      >
                        #{d.dossier_id}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 tabular-nums">{d.stats.stage1_stripped_citations}</td>
                    <td className="py-2 pr-4 tabular-nums">
                      {d.stats.stage2_unsupported_removed}
                    </td>
                    <td className="py-2 pr-4 tabular-nums">{d.stats.hypothesis_claims}</td>
                    <td className="py-2 pr-4 tabular-nums">{d.stats.safety_notes_deleted}</td>
                    <td className="py-2 tabular-nums">{d.stats.chat_citations_stripped}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export function OpsView() {
  const [tab, setTab] = useState<Tab>("runs");

  return (
    <AppShell>
      <PageHeader
        title="Operations"
        subtitle="Read-only AI ops — reasoning traces, eval history, structural guardrails."
      />
      <nav className="mb-8 flex gap-2 border-b border-border">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={cn(
              "border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-primary",
            )}
          >
            {label}
          </button>
        ))}
      </nav>
      {tab === "runs" && <RunsTab />}
      {tab === "evals" && <EvalsTab />}
      {tab === "guardrails" && <GuardrailsTab />}
    </AppShell>
  );
}
