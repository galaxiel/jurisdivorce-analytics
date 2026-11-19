"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DecisionCard } from "@/components/analytics/decision-card";
import { FilterBar } from "@/components/analytics/filter-bar";
import { DecisionDetailDialog } from "@/components/jurisprudence/decision-detail-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { exportUrl, useFacets, useJurisprudence } from "@/lib/api";
import type { DecisionFilters } from "@/lib/types";

/* Vue 4 — Explorateur de Jurisprudence : recherche + filtres croisés + cartes. */
function DecisionsContent() {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<DecisionFilters>({ page: 1, page_size: 12 });
  const [openId, setOpenId] = useState<string | null>(searchParams.get("id"));

  const { data, loading, error } = useJurisprudence(filters);
  const facets = useFacets();

  function applyFilters(f: DecisionFilters) {
    setFilters({ ...f, page: 1, page_size: 12 });
  }

  function onExport(format: "csv" | "json") {
    window.open(exportUrl(filters, format), "_blank");
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="mx-auto max-w-7xl space-y-4 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold">Explorateur de Jurisprudence</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Recherche plein texte et filtres multicritères — cliquez sur une carte pour l&apos;analyse complète.
        </p>
      </div>

      <FilterBar filters={filters} onChange={applyFilters} facets={facets.data} onExport={onExport} compact />

      {error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          API indisponible : {error}. Lancez le backend (uvicorn) puis rechargez.
        </p>
      )}

      <p className="text-xs text-muted-foreground">
        {data ? `${data.total.toLocaleString("fr-FR")} décision(s) correspondante(s)` : "…"}
      </p>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(data?.items ?? []).map((item) => (
            <DecisionCard key={item.id} item={item} onOpen={setOpenId} />
          ))}
          {(data?.items ?? []).length === 0 && (
            <p className="col-span-full py-12 text-center text-muted-foreground">
              Aucune décision ne correspond à ces filtres.
            </p>
          )}
        </div>
      )}

      {data && data.total > 0 && (
        <div className="flex items-center justify-center gap-3 text-sm">
          <Button variant="outline" size="sm" disabled={filters.page! <= 1} onClick={() => setFilters({ ...filters, page: filters.page! - 1 })}>
            <ChevronLeft className="h-4 w-4" /> Précédent
          </Button>
          <span className="text-muted-foreground">
            Page {filters.page} / {totalPages} — {data.total.toLocaleString("fr-FR")} décisions
          </span>
          <Button variant="outline" size="sm" disabled={filters.page! >= totalPages} onClick={() => setFilters({ ...filters, page: filters.page! + 1 })}>
            Suivant <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      <DecisionDetailDialog id={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}

/* Suspense requis par next build pour useSearchParams (lien « décision jumelle »). */
export default function DecisionsPage() {
  return (
    <Suspense fallback={null}>
      <DecisionsContent />
    </Suspense>
  );
}
