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

export const getAppConfig = () => apiFetch<AppConfig>("/api/config");

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

/** Absolute URL for a rendered PDF served by the backend (react-pdf source). */
export const fileUrl = (relativeUrl: string) => `${API_URL}${relativeUrl}`;
