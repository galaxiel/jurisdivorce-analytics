/* Layer client HTTP + hooks React (cahier des charges §5.2 : aucun fetch dans les composants d'affichage). */
import { useEffect, useState } from "react";
import type {
  BoussoleReport,
  BoussoleRequest,
  CourComparatif,
  DecisionDetail,
  DecisionFilters,
  DecisionList,
  KpiOverview,
  MotifRejet,
  PCDistribution,
  PreuveSucces,
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

/** Hook générique : refetch automatique quand `path` change. */
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

/* ------------------------------------------------ Hooks métier */
export function useAnalytics() {
  return {
    overview: useApi<KpiOverview>("/api/stats/overview"),
    comparatif: useApi<CourComparatif[]>("/api/stats/comparatif-cours"),
    pc: useApi<PCDistribution[]>("/api/stats/distribution-pc"),
    motifs: useApi<MotifRejet[]>("/api/stats/top-motifs-rejet"),
    preuves: useApi<PreuveSucces[]>("/api/stats/recompenses-par-preuve"),
  };
}

export function useJurisprudence(filters: DecisionFilters & { page?: number; page_size?: number }, refreshKey = 0) {
  const path = `/api/decisions${toQuery(filters)}`;
  return useApi<DecisionList>(path, refreshKey);
}

export function useDecision(id: string | null) {
  return useApi<DecisionDetail>(id ? `/api/decisions/${id}` : null);
}

export async function postBoussole(req: BoussoleRequest): Promise<BoussoleReport> {
  return request<BoussoleReport>("/api/boussole", { method: "POST", body: JSON.stringify(req) });
}
