/* Layer client HTTP + hooks React (aucun fetch dans les composants d'affichage). */
import { useEffect, useState } from "react";
import type {
  AbattementBucket,
  ArchiveInfo,
  BoussoleReport,
  BoussoleRequest,
  CourComparatif,
  DecisionDetail,
  DecisionFilters,
  DecisionList,
  Facets,
  Benchmark,
  HealthStatus,
  KpiOverview,
  MotifRejet,
  NatureSucces,
  OccupationCalcResult,
  PCCorrelationPoint,
  PCDistribution,
  Piege,
  PipelineConfig,
  PipelineLog,
  PipelineState,
  PreuveSucces,
  RecompenseCalcResult,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error((detail as { detail?: string } | null)?.detail ?? `Erreur API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function toQuery(params: object): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params as Record<string, string | number | undefined>)) {
    if (v !== undefined && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

/** Hook générique : refetch quand `path` ou `refreshKey` change. */
export function useApi<T>(path: string | null, refreshKey = 0) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!path) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    request<T>(path)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, refreshKey]);

  return { data, loading, error };
}

/** Sondage périodique (moniteur du pipeline). */
export function usePolling<T>(path: string, intervalMs = 3000, refreshKey = 0) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return useApi<T>(path, tick + refreshKey);
}

/* ------------------------------------------------ Hooks métier */
export function useAnalytics(filters: DecisionFilters) {
  const { page: _p, page_size: _ps, ...statFilters } = filters;
  const qs = toQuery(statFilters);
  return {
    overview: useApi<KpiOverview>(`/api/stats/overview${qs}`),
    comparatif: useApi<CourComparatif[]>(`/api/stats/comparatif-cours${qs}`),
    pc: useApi<PCDistribution[]>(`/api/stats/distribution-pc${qs}`),
    abattements: useApi<AbattementBucket[]>(`/api/stats/abattement-distribution${qs}`),
    natures: useApi<NatureSucces[]>(`/api/stats/succes-par-nature${qs}`),
    scatter: useApi<PCCorrelationPoint[]>(`/api/stats/pc-correlation${qs}`),
    motifs: useApi<MotifRejet[]>(`/api/stats/top-motifs-rejet${qs}`),
    preuves: useApi<PreuveSucces[]>(`/api/stats/recompenses-par-preuve${qs}`),
  };
}

export function useFacets(refreshKey = 0) {
  return useApi<Facets>("/api/stats/facets", refreshKey);
}

export function useJurisprudence(filters: DecisionFilters, refreshKey = 0) {
  const path = `/api/decisions${toQuery(filters)}`;
  return useApi<DecisionList>(path, refreshKey);
}

export function useDecision(id: string | null) {
  return useApi<DecisionDetail>(id ? `/api/decisions/${id}` : null);
}

export async function postBoussole(req: BoussoleRequest): Promise<BoussoleReport> {
  return request<BoussoleReport>("/api/boussole", { method: "POST", body: JSON.stringify(req) });
}

/* ------------------------------------------------ Pipeline */
export function usePipelineState(refreshKey = 0) {
  return usePolling<PipelineState>("/api/pipeline/state", 2500, refreshKey);
}

export function usePipelineLogs(refreshKey = 0) {
  return usePolling<PipelineLog[]>("/api/pipeline/logs?limit=80", 3000, refreshKey);
}

export function usePipelineArchives(refreshKey = 0) {
  return usePolling<ArchiveInfo[]>("/api/pipeline/archives?limit=60", 6000, refreshKey);
}

export function usePipelineConfig(refreshKey = 0) {
  return useApi<PipelineConfig>("/api/pipeline/config", refreshKey);
}

export async function putPipelineConfig(cfg: PipelineConfig): Promise<PipelineConfig> {
  return request<PipelineConfig>("/api/pipeline/config", {
    method: "PUT",
    body: JSON.stringify(cfg),
  });
}

export async function postRetryFailed(): Promise<{ failed_decisions: number; flag_posed: boolean; note: string }> {
  return request("/api/pipeline/retry-failed", { method: "POST", body: "{}" });
}

export function useBenchmark(refreshKey = 0) {
  return usePolling<Benchmark>("/api/pipeline/benchmark", 8000, refreshKey);
}

export function usePieges() {
  return useApi<Piege[]>("/api/stats/pieges");
}

export function useHealth() {
  return usePolling<HealthStatus>("/api/health", 30000);
}

export async function postOccupationCalc(req: {
  juridiction: string;
  valeur_locative_mensuelle: number;
  date_debut: string;
  date_fin: string;
  quote_part_autres_pct: number;
}): Promise<OccupationCalcResult> {
  return request<OccupationCalcResult>("/api/calculateur/occupation", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function postRecompenseCalc(req: {
  valeur_bien_avant_travaux: number;
  valeur_bien_actuelle: number;
  montant_travaux: number;
  nature: "amelioration" | "entretien";
}): Promise<RecompenseCalcResult> {
  return request<RecompenseCalcResult>("/api/calculateur/recompense", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function postPipelineControl(action: "pause" | "resume" | "stop"): Promise<PipelineState> {
  return request<PipelineState>("/api/pipeline/control", {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

/* ------------------------------------------------ Export de la sélection */
export function exportUrl(filters: DecisionFilters, format: "csv" | "json"): string {
  const { page: _p, page_size: _ps, ...statFilters } = filters;
  return `${API_BASE}/api/decisions/export${toQuery({ ...statFilters, format })}`;
}
