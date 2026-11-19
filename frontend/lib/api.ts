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
  DecisionListItem,
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
  TendancePoint,
  PensionStats,
  DemandesAnnexesStats,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

/* ── Fallback statique : si l'API ne répond pas, bascule silencieuse sur /data/*.json ── */
export type ApiSource = "live" | "snapshot" | "unknown";
let apiSource: ApiSource = "unknown";
export function getApiSource(): ApiSource {
  return apiSource;
}
function setApiSource(s: ApiSource) {
  if (apiSource !== s) {
    apiSource = s;
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("api-source", { detail: s }));
    }
  }
}

const FALLBACK_MAP: [RegExp, string][] = [
  [/^\/api\/stats\/overview\b/, "/data/stats_globales.json"],
  [/^\/api\/stats\/comparatif-cours\b/, "/data/stats_par_cour.json"],
  [/^\/api\/stats\/tendances\b/, "/data/tendances.json"],
  [/^\/api\/stats\/distribution-pc\b/, "/data/distribution_pc.json"],
  [/^\/api\/stats\/abattement-distribution\b/, "/data/abattements.json"],
  [/^\/api\/stats\/succes-par-nature\b/, "/data/natures.json"],
  [/^\/api\/stats\/pc-correlation\b/, "/data/scatter.json"],
  [/^\/api\/stats\/top-motifs-rejet\b/, "/data/motifs.json"],
  [/^\/api\/stats\/recompenses-par-preuve\b/, "/data/preuves.json"],
  [/^\/api\/stats\/pieges\b/, "/data/pieges_top10.json"],
  [/^\/api\/stats\/facets\b/, "/data/facets.json"],
  [/^\/api\/health\b/, "/data/health.json"],
  [/^\/api\/demo\/count\b/, "/data/health.json"],
  [/^\/api\/decisions\b/, "/data/decisions_index.json"],
];

type SnapshotDecision = DecisionListItem & {
  resume_pedagogique?: string | null;
  bien_immobilier_principal?: boolean | null;
  pc_demandee?: boolean | null;
  pc_forme?: string | null;
  article_700_montant?: number | null;
  partage_depens?: string | null;
  delai_procedure_mois?: number | null;
  conseil_pratique?: string | null;
  recompenses?: Array<{
    id: number; categorie: string | null; demandeur: string | null;
    montant_reclame: number | null; montant_accorde: number | null;
    statut: string | null; preuve_type: string | null;
    preuve_clef_retenue: string | null; motif_echec: string | null;
    regle_calcul: string | null; preuves: string[];
  }>;
};

function filterDecisionsSnapshot(items: SnapshotDecision[], sp: URLSearchParams): DecisionList {
  const g = (k: string) => sp.get(k) ?? "";
  let out = items;
  const v = g("juridiction"); if (v) out = out.filter((d) => d.juridiction === v);
  const y = g("annee"); if (y) out = out.filter((d) => (d.date_decision ?? "").startsWith(y));
  const rg = g("regime"); if (rg) out = out.filter((d) => d.regime_matrimonial === rg);
  const tp = g("type_procedure"); if (tp) out = out.filter((d) => d.type_procedure === tp);
  const nat = g("nature_reclamation"); if (nat) out = out.filter((d) => (d.recompenses ?? []).some((r) => r.categorie === nat));
  const is = g("issue"); if (is) out = out.filter((d) => (d.recompenses ?? []).some((r) => r.statut === is));
  const hi = g("has_immo"); if (hi) out = out.filter((d) => String(d.bien_immobilier_principal) === hi);
  if (g("montant_min")) out = out.filter((d) => (d.occupation_montant_total ?? d.pc_montant_capital ?? 0) >= Number(g("montant_min")));
  if (g("montant_max")) out = out.filter((d) => (d.occupation_montant_total ?? d.pc_montant_capital ?? Number.MAX_SAFE_INTEGER) <= Number(g("montant_max")));
  const qq = g("q").toLowerCase();
  if (qq) {
    out = out.filter((d) =>
      `${d.resume_3_lignes ?? ""} ${d.resume_pedagogique ?? ""} ${d.juridiction ?? ""} ${d.numero_rg ?? ""}`
        .toLowerCase()
        .includes(qq),
    );
  }
  const total = out.length;
  const page = Math.max(1, Number(g("page") || 1));
  const ps = Math.max(1, Number(g("page_size") || 10));
  return { total, page, page_size: ps, items: out.slice((page - 1) * ps, page * ps) };
}

async function fetchFallback(path: string): Promise<unknown | null> {
  for (const [re, file] of FALLBACK_MAP) {
    if (re.test(path)) {
      try {
        const res = await fetch(file);
        if (!res.ok) return null;
        const data = (await res.json()) as unknown;
        setApiSource("snapshot");
        return data;
      } catch {
        return null;
      }
    }
  }
  return null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error((detail as { detail?: string } | null)?.detail ?? `Erreur API ${res.status}`);
    }
    setApiSource("live");
    return (await res.json()) as T;
  } catch (err) {
    // Repli statique : la source de données pré-agrégée (frontend/public/data/)
    const fb = (await fetchFallback(path)) as unknown;
    if (fb === null) throw err;
    if (Array.isArray(fb) && /^\/api\/decisions(\?|$)/.test(path)) {
      const qs = path.split("?")[1] ?? "";
      return filterDecisionsSnapshot(fb as SnapshotDecision[], new URLSearchParams(qs)) as T;
    }
    if (!Array.isArray(fb) && /^\/api\/decisions\/.+$/.test(path)) {
      const id = decodeURIComponent(path.split("/").pop() ?? "");
      const item = (fb as SnapshotDecision[]).find((d) => d.id === id);
      if (item) return item as T;
      throw new Error("Décision introuvable dans le snapshot");
    }
    return fb as T;
  }
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
    tendances: useApi<TendancePoint[]>(`/api/stats/tendances${qs}`),
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

export function usePension() {
  return useApi<PensionStats>("/api/stats/pension");
}

export function useDemandesAnnexes() {
  return useApi<DemandesAnnexesStats>("/api/stats/demandes-annexes");
}

export function useHealth() {
  return usePolling<HealthStatus>("/api/health", 30000);
}

export async function postSimulateurDiagnostic(req: unknown): Promise<unknown> {
  return request("/api/simulateur/diagnostic", { method: "POST", body: JSON.stringify(req) });
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
