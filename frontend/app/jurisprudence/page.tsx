"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DecisionFiltersBar } from "@/components/jurisprudence/filters";
import { DecisionTable } from "@/components/jurisprudence/decision-table";
import { DecisionDetailDialog } from "@/components/jurisprudence/decision-detail-dialog";
import { useJurisprudence } from "@/lib/api";
import type { DecisionFilters } from "@/lib/types";

function JurisprudenceContent() {
  const searchParams = useSearchParams();
  const [filters, setFilters] = useState<DecisionFilters>({});
  const [page, setPage] = useState(1);
  const [openId, setOpenId] = useState<string | null>(searchParams.get("id"));

  const { data, loading, error } = useJurisprudence({ page_size: 10, ...filters, page });

  function applyFilters(f: DecisionFilters) {
    setFilters(f);
    setPage(1);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="mx-auto max-w-7xl space-y-4 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold">Explorer la jurisprudence</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Filtres combinés en temps réel — cliquez sur une ligne pour ouvrir la fiche décisionnelle.
        </p>
      </div>

      <DecisionFiltersBar filters={filters} onChange={applyFilters} total={data?.total} />

      {error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          API indisponible : {error}. Lancez le backend (uvicorn) puis rechargez.
        </p>
      )}

      <Card>
        <CardContent className="p-0">
          <DecisionTable items={data?.items ?? []} loading={loading} onOpen={setOpenId} />
        </CardContent>
      </Card>

      {data && data.total > 0 && (
        <div className="flex items-center justify-center gap-3 text-sm">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            <ChevronLeft className="h-4 w-4" /> Précédent
          </Button>
          <span className="text-muted-foreground">
            Page {page} / {totalPages} — {data.total.toLocaleString("fr-FR")} décisions
          </span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
            Suivant <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      <DecisionDetailDialog id={openId} onClose={() => setOpenId(null)} />
    </div>
  );
}

/* Suspense requis par next build pour useSearchParams (lien « décision jumelle »). */
export default function JurisprudencePage() {
  return (
    <Suspense fallback={null}>
      <JurisprudenceContent />
    </Suspense>
  );
}
