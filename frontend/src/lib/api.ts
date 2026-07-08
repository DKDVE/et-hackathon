import type { components } from "./api-types";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type EventSummary = components["schemas"]["EventSummary"];
export type DossierResponse = components["schemas"]["DossierResponse"];
export type SharedContext = components["schemas"]["SharedContext"];
export type AssetProfile = components["schemas"]["AssetProfile"];
export type ChunkRecord = components["schemas"]["ChunkRecord"];
export type WorkOrderRecord = components["schemas"]["WorkOrderRecord"];
export type SisterIncident = components["schemas"]["SisterIncident"];
export type PatternStat = components["schemas"]["PatternStat"];
export type ChunkSource = components["schemas"]["ChunkSource"];
export type WorkOrderSource = components["schemas"]["WorkOrderSource"];
export type AssetSummary = components["schemas"]["AssetSummary"];
export type DegradedInfo = components["schemas"]["DegradedInfo"];
export type ChatResponse = components["schemas"]["ChatResponse"];
export type ChatTurn = components["schemas"]["ChatTurn"];
export type AppConfig = components["schemas"]["AppConfig"];

export type ReasoningRunRow = {
  id: number;
  node: string;
  model: string;
  prompt_version: string;
  started_at: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  status: string;
};

export type ReasoningRunsResponse = {
  runs: ReasoningRunRow[];
  replayed_from_cache: boolean;
  total_latency_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  estimated_cost_usd: number;
  cost_footnote: string;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw new ApiError(`API error: ${response.statusText}`, response.status);
  }
  return response.json() as Promise<T>;
}

export type HealthResponse = { status: string; db: string };

export const getHealth = () => apiFetch<HealthResponse>("/health");

export const listEvents = (status?: string) =>
  apiFetch<EventSummary[]>(`/api/events${status ? `?status=${status}` : ""}`);

export const getEvent = (id: number | string) =>
  apiFetch<EventSummary>(`/api/events/${id}`);

export const createDossier = (eventId: number | string) =>
  apiFetch<DossierResponse>(`/api/events/${eventId}/dossier`, { method: "POST" });

export const getDossier = (dossierId: number | string) =>
  apiFetch<DossierResponse>(`/api/dossiers/${dossierId}`);

export const getDossierRuns = (dossierId: number | string) =>
  apiFetch<ReasoningRunsResponse>(`/api/dossiers/${dossierId}/runs`);

export const getAppConfig = () => apiFetch<AppConfig>("/api/config");

export type OpsRunRow = {
  id: number;
  dossier_id: number;
  event_id: number;
  node: string;
  model: string;
  prompt_version: string;
  started_at: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  status: string;
};

export type OpsCostsResponse = {
  total_estimated_cost_usd: number;
  today_estimated_cost_usd: number;
  by_model: Record<string, { prompt_tokens: number; completion_tokens: number; estimated_cost_usd: number }>;
  by_day: Record<string, { prompt_tokens: number; completion_tokens: number; estimated_cost_usd: number }>;
  cost_footnote: string;
};

export type EvalRunRow = {
  id: number;
  suite: string;
  started_at: string;
  finished_at: string;
  git_ref: string;
  prompt_versions: Record<string, string>;
  status: string;
  metrics: Record<string, number | string>;
  detail?: Record<string, unknown> | null;
};

export type EvalRunsResponse = {
  history: EvalRunRow[];
  latest_by_suite: Record<string, EvalRunRow | null>;
};

export type GuardrailDossierRow = {
  dossier_id: number;
  event_id: number;
  completed_at: string | null;
  stats: Record<string, number>;
};

export type GuardrailsResponse = {
  fleet_totals: Record<string, number>;
  not_recorded_count: number;
  dossiers: GuardrailDossierRow[];
};

export const getOpsRuns = (query = "") =>
  apiFetch<{ runs: OpsRunRow[]; limit: number; offset: number }>(`/api/ops/runs${query}`);

export const getOpsCosts = () => apiFetch<OpsCostsResponse>("/api/ops/costs");

export const getOpsEvals = () => apiFetch<EvalRunsResponse>("/api/ops/evals");

export const getOpsGuardrails = () => apiFetch<GuardrailsResponse>("/api/ops/guardrails");

export const chatDossierRaw = (
  dossierId: number | string,
  question: string,
  history: ChatTurn[] = [],
) =>
  fetch(`${API_URL}/api/dossiers/${dossierId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });

export const chatDossier = (
  dossierId: number | string,
  question: string,
  history: ChatTurn[] = [],
) =>
  apiFetch<ChatResponse>(`/api/dossiers/${dossierId}/chat`, {
    method: "POST",
    body: JSON.stringify({ question, history }),
  });

export const getChunkSource = (chunkId: number | string) =>
  apiFetch<ChunkSource>(`/api/sources/chunk/${chunkId}`);

export const getWorkOrderSource = (woNumber: string) =>
  apiFetch<WorkOrderSource>(`/api/sources/wo/${woNumber}`);

export const listAssets = () => apiFetch<AssetSummary[]>("/api/assets");

export type MemoryOverview = {
  asset_count: number;
  document_count: number;
  chunk_count: number;
  work_order_count: number;
  wo_auto_classified: number;
  wo_unclassified: number;
  wo_human_reviewed: number;
  taxonomy_size: number;
};

export type MemoryAssetRow = {
  asset_id: number;
  tag: string;
  name: string;
  asset_class: string;
  manual_available: boolean;
  sop_count: number;
  wo_count: number;
  last_inspection_date: string | null;
  classified_ratio: number;
  coverage_tier: "Good" | "Partial" | "Thin";
};

export type MemoryDocumentRow = {
  document_id: number;
  title: string;
  doc_type: string;
  owner_asset_tag: string | null;
  owner_class: string | null;
  chunk_count: number;
  ocr_page_count: number;
  file_url: string;
};

export type TaxonomyModeRow = {
  mode_id: number;
  code: string;
  name: string;
  auto_wo_count: number;
  human_override_count: number;
  mean_normalization_score: number | null;
};

export type TaxonomyFamilyGroup = {
  family: string;
  modes: TaxonomyModeRow[];
};

export type ReviewQueueRow = {
  wo_id: number;
  wo_number: string;
  asset_tag: string;
  raw_description: string;
  auto_failure_mode_code: string | null;
  auto_failure_mode_family: string | null;
  normalization_score: number | null;
  candidates: { mode_id: number; code: string; name: string; score: number }[];
};

export const getMemoryOverview = () => apiFetch<MemoryOverview>("/api/memory/overview");

export const getMemoryAssets = () =>
  apiFetch<{ assets: MemoryAssetRow[]; coverage_footnote: string }>("/api/memory/assets");

export const getMemoryDocuments = () => apiFetch<MemoryDocumentRow[]>("/api/memory/documents");

export const getMemoryTaxonomy = () => apiFetch<TaxonomyFamilyGroup[]>("/api/memory/taxonomy");

export const getMemoryReviewQueue = () => apiFetch<ReviewQueueRow[]>("/api/memory/review-queue");

export const submitReviewVerdict = (
  woId: number,
  body: { verdict: string; failure_mode_id?: number | null },
) =>
  apiFetch(`/api/memory/review/${woId}`, {
    method: "POST",
    body: JSON.stringify(body),
  });

/** Absolute URL for a rendered PDF served by the backend (react-pdf source). */
export const fileUrl = (relativeUrl: string) => `${API_URL}${relativeUrl}`;
