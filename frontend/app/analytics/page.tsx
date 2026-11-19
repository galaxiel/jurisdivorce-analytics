"use client";

import { useState } from "react";
import { exportUrl, useAnalytics, useDemandesAnnexes, useFacets, usePension } from "@/lib/api";
import { FilterBar } from "@/components/analytics/filter-bar";
import { KpiCard } from "@/components/analytics/kpi-card";
import { PensionTab } from "@/components/analytics/pension-tab";
import { AbattementDistributionChart } from "@/components/charts/abattement-distribution";
import { BarComparatif } from "@/components/charts/bar-comparatif";
import { MotifsRejetChart } from "@/components/charts/motifs-rejet";
import { NatureSuccessChart } from "@/components/charts/nature-success";
import { PCDistributionChart } from "@/components/charts/pc-distribution";
import { PCScatterChart } from "@/components/charts/pc-scatter";
import { ProofSuccessChart } from "@/components/charts/proof-success";
import { TendancesChart } from "@/components/charts/tendances";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { DecisionFilters } from "@/lib/types";
import { cn, formatEur, formatPct } from "@/lib/utils";

/* Vue 1 — Cockpit Global : KPIs réactifs aux filtres + analytics avancés (onglets). */
export default function AnalyticsPage() {
  const [filters, setFilters] = useState<DecisionFilters>({});
  const [onglet, setOnglet] = useState<"patrimoine" | "pension">("patrimoine");
  const facets = useFacets();
  const { overview, comparatif, pc, abattements, natures, scatter, motifs, preuves, tendances } = useAnalytics(filters);
  const pensionStats = usePension();
  const demandesStats = useDemandesAnnexes();

  function onExport(format: "csv" | "json") {
    window.open(exportUrl(filters, format), "_blank");
  }

  return (
    <div className="mx-auto max-w-7xl space-y-5 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold">Cockpit Global</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {overview.data
            ? `${overview.data.total_decisions.toLocaleString("fr-FR")} décisions · ${overview.data.nb_juridictions} juridictions${overview.data.periode ? ` · ${overview.data.periode}` : ""}`
            : "Chargement des statistiques…"}
        </p>
      </div>

      <FilterBar filters={filters} onChange={setFilters} facets={facets.data} onExport={onExport} />

      {overview.error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          API indisponible : {overview.error}. Lancez le backend (uvicorn) puis rechargez.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard label="Arrêts analysés (sélection)" value={overview.data?.total_decisions.toLocaleString("fr-FR") ?? "—"} />
        <KpiCard label="Succès global des réclamations financières" value={formatPct(overview.data?.taux_succes_recompenses_pct)} tone="success" />
        <KpiCard label="Médiane prestation compensatoire" value={formatEur(overview.data?.pc_capital_median)} />
        <KpiCard label="Abattement moyen indemnité d'occupation" value={formatPct(overview.data?.abattement_moyen_pct)} />
        <KpiCard label="Article 700 moyen" value={formatEur(overview.data?.article_700_moyen)} tone="neutral" />
        <KpiCard label="Rejets sans factures nominatives" value={formatPct(overview.data?.taux_echec_sans_factures_pct)} tone="destructive" />
      </div>

      <div className="flex gap-2">
        {[
          { key: "patrimoine" as const, label: "Patrimoine & PC" },
          { key: "pension" as const, label: "Pension & demandes annexes" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setOnglet(t.key)}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
              onglet === t.key
                ? "border-primary bg-primary/10 text-primary"
                : "bg-card text-muted-foreground hover:bg-secondary",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {onglet === "pension" && <PensionTab pension={pensionStats} demandesAnnexes={demandesStats} />}

      {onglet === "patrimoine" && (
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Comparateur inter-Cours d&apos;appel</CardTitle>
            <CardDescription>
              Indemnité d&apos;occupation mensuelle moyenne et abattement moyen accordé.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {comparatif.loading ? <Skeleton className="h-80 w-full" /> : <BarComparatif data={comparatif.data ?? []} />}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Tendances par année</CardTitle>
            <CardDescription>
              PC médiane, abattement médian et taux de succès — l&apos;évolution de la pratique judiciaire.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {tendances.loading ? <Skeleton className="h-80 w-full" /> : <TendancesChart data={tendances.data ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Distribution des abattements d&apos;occupation</CardTitle>
            <CardDescription>Précarité : 15 %, 20 %, 30 %… où se situe votre cour ?</CardDescription>
          </CardHeader>
          <CardContent>
            {abattements.loading ? <Skeleton className="h-72 w-full" /> : <AbattementDistributionChart data={abattements.data ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Succès par nature de réclamation</CardTitle>
            <CardDescription>Montant réclamé vs obtenu et taux d&apos;acceptation.</CardDescription>
          </CardHeader>
          <CardContent>
            {natures.loading ? <Skeleton className="h-80 w-full" /> : <NatureSuccessChart data={natures.data ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Corrélation PC : durée du mariage &amp; écart de revenus</CardTitle>
            <CardDescription>Chaque point est une prestation compensatoire accordée.</CardDescription>
          </CardHeader>
          <CardContent>
            {scatter.loading ? <Skeleton className="h-80 w-full" /> : <PCScatterChart data={scatter.data ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Distribution des prestations compensatoires</CardTitle>
            <CardDescription>Selon la durée du mariage.</CardDescription>
          </CardHeader>
          <CardContent>
            {pc.loading ? <Skeleton className="h-80 w-full" /> : <PCDistributionChart data={pc.data ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Top 5 des motifs de rejet</CardTitle>
            <CardDescription>Créances entre époux &amp; récompenses rejetées.</CardDescription>
          </CardHeader>
          <CardContent>
            {motifs.loading ? <Skeleton className="h-72 w-full" /> : <MotifsRejetChart data={motifs.data ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Taux de succès selon la preuve possédée</CardTitle>
            <CardDescription>La facture nominative change tout.</CardDescription>
          </CardHeader>
          <CardContent>
            {preuves.loading ? <Skeleton className="h-72 w-full" /> : <ProofSuccessChart data={preuves.data ?? []} />}
          </CardContent>
        </Card>
      </div>
      )}
    </div>
  );
}
