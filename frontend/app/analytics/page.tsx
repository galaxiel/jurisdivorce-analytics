"use client";

import { useAnalytics } from "@/lib/api";
import { BarComparatif } from "@/components/charts/bar-comparatif";
import { MotifsRejetChart } from "@/components/charts/motifs-rejet";
import { PCDistributionChart } from "@/components/charts/pc-distribution";
import { ProofSuccessChart } from "@/components/charts/proof-success";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatEur, formatPct } from "@/lib/utils";
import { PROOF_LABELS } from "@/lib/types";

export default function AnalyticsPage() {
  const { overview, comparatif, pc, motifs, preuves } = useAnalytics();

  const kpis = [
    { label: "Indemnité d'occupation accordée", value: formatPct(overview.data?.taux_occupation_accordee) },
    { label: "Abattement moyen appliqué", value: formatPct(overview.data?.abattement_moyen_pct) },
    { label: "Récompense travaux moyenne accordée", value: formatEur(overview.data?.montant_moyen_recompense_travaux) },
    { label: "Rejets sans factures nominatives", value: formatPct(overview.data?.taux_echec_sans_factures_pct) },
    { label: "Prestation compensatoire accordée", value: formatPct(overview.data?.pc_taux_accorde_pct) },
    { label: "Capital moyen de prestation compensatoire", value: formatEur(overview.data?.pc_capital_moyen) },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {overview.data
            ? `${overview.data.total_decisions.toLocaleString("fr-FR")} décisions · ${overview.data.nb_juridictions} cours d'appel · période ${overview.data.periode}`
            : "Chargement des statistiques…"}
        </p>
      </div>

      {overview.error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          API indisponible : {overview.error}. Lancez le backend (uvicorn) puis rechargez.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="pt-5">
              <div className="text-xl font-bold text-primary">{k.value}</div>
              <p className="mt-1 text-xs text-muted-foreground">{k.label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Comparatif des Cours d'appel</CardTitle>
            <CardDescription>Indemnité d'occupation mensuelle moyenne et abattement moyen accordé.</CardDescription>
          </CardHeader>
          <CardContent>
            {comparatif.loading ? <Skeleton className="h-80 w-full" /> : <BarComparatif data={comparatif.data ?? []} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Distribution des prestations compensatoires</CardTitle>
            <CardDescription>Selon la durée du mariage.</CardDescription>
          </CardHeader>
          <CardContent>{pc.loading ? <Skeleton className="h-80 w-full" /> : <PCDistributionChart data={pc.data ?? []} />}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Top 5 des motifs de rejet</CardTitle>
            <CardDescription>Créances entre époux & récompenses rejetées.</CardDescription>
          </CardHeader>
          <CardContent>{motifs.loading ? <Skeleton className="h-72 w-full" /> : <MotifsRejetChart data={motifs.data ?? []} />}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Taux de succès selon la preuve possédée</CardTitle>
            <CardDescription>Le nerf de la guerre : la facture nominative change tout.</CardDescription>
          </CardHeader>
          <CardContent>{preuves.loading ? <Skeleton className="h-72 w-full" /> : <ProofSuccessChart data={preuves.data ?? []} />}</CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Détail par type de preuve</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {(preuves.data ?? []).map((p) => (
                <li key={p.preuve_type} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span>{PROOF_LABELS[p.preuve_type] ?? p.preuve_type}</span>
                  <span className="text-muted-foreground">
                    {p.nb_reclamations} réclamations · {formatPct(p.taux_succes_pct)} · moy. {formatEur(p.montant_moyen_accorde)}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
