"use client";

import { AlertTriangle, BadgeCheck, CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useDecision } from "@/lib/api";
import { PROOF_LABELS, REGIME_LABELS, STATUT_LABELS } from "@/lib/types";
import { formatEur, formatDate } from "@/lib/utils";

const CATEGORIE_LABELS: Record<string, string> = {
  TRAVAUX_BIEN_PROPRE: "Travaux sur bien propre",
  REMBOURSEMENT_EMPRUNT: "Remboursement d'emprunt",
  APPORT_FONDS_PROPRES: "Apport en fonds propres",
  AUTRE: "Autre",
};

/* Fiche décisionnelle détaillée : vue côte-à-côte Résumé IA vs Extrait brut (cahier des charges §Module 3). */
export function DecisionDetailDialog({ id, onClose }: { id: string | null; onClose: () => void }) {
  const { data, loading, error } = useDecision(id);

  return (
    <Dialog
      open={Boolean(id)}
      onClose={onClose}
      title={
        data
          ? `${data.juridiction} — ${formatDate(data.date_decision)} (${data.numero_rg ?? "RG n/a"})`
          : "Chargement de la décision…"
      }
    >
      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {data && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge variant={data.source === "SYNTHETIQUE_DEMO" ? "destructive" : "success"}>
              {data.source === "SYNTHETIQUE_DEMO" ? "Données de démonstration" : "Judilibre — officiel"}
            </Badge>
            <Badge variant="secondary">{REGIME_LABELS[data.regime_matrimonial ?? ""] ?? "Régime inconnu"}</Badge>
            <Badge variant="outline">{data.duree_mariage_annees ?? "—"} ans de mariage</Badge>
            <Badge variant="outline">{data.nombre_enfants ?? 0} enfant(s)</Badge>
            {data.valeur_bien_principal && (
              <Badge variant="outline">Bien estimé {formatEur(data.valeur_bien_principal)}</Badge>
            )}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Résumé structuré IA</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <p>{data.resume_3_lignes}</p>

                {data.points_forts_gagnants.length > 0 && (
                  <div>
                    <h4 className="mb-1.5 flex items-center gap-1.5 font-semibold text-success">
                      <CheckCircle2 className="h-4 w-4" /> Points forts gagnants
                    </h4>
                    <ul className="space-y-1 text-muted-foreground">
                      {data.points_forts_gagnants.map((p, i) => (
                        <li key={i}>— {p}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.pieges_et_erreurs.length > 0 && (
                  <div>
                    <h4 className="mb-1.5 flex items-center gap-1.5 font-semibold text-destructive">
                      <AlertTriangle className="h-4 w-4" /> Pièges &amp; erreurs à éviter
                    </h4>
                    <ul className="space-y-1 text-muted-foreground">
                      {data.pieges_et_erreurs.map((p, i) => (
                        <li key={i}>— {p}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.recompenses.length > 0 && (
                  <div>
                    <h4 className="mb-1.5 font-semibold">Récompenses &amp; créances</h4>
                    <ul className="space-y-2">
                      {data.recompenses.map((r) => (
                        <li key={r.id} className="rounded-md border p-2.5 text-xs">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold">{CATEGORIE_LABELS[r.categorie ?? ""] ?? r.categorie}</span>
                            {r.statut === "REJETE" ? (
                              <Badge variant="destructive">
                                <XCircle className="mr-1 h-3 w-3" /> Rejetée
                              </Badge>
                            ) : (
                              <Badge variant="success">
                                <BadgeCheck className="mr-1 h-3 w-3" /> {STATUT_LABELS[r.statut ?? ""]}
                              </Badge>
                            )}
                            <span className="ml-auto">
                              {r.statut !== "REJETE" ? (
                                <>
                                  {formatEur(r.montant_accorde)} <span className="text-muted-foreground">/ {formatEur(r.montant_reclame)} demandés</span>
                                </>
                              ) : (
                                <span className="text-muted-foreground">{formatEur(r.montant_reclame)} demandés</span>
                              )}
                            </span>
                          </div>
                          <div className="mt-1 text-muted-foreground">
                            {r.preuve_clef_retenue && <p>Preuve retenue : {r.preuve_clef_retenue}</p>}
                            {r.motif_echec && <p>Échec : {r.motif_echec}</p>}
                            {r.preuve_type && <p className="italic">Type de preuve : {PROOF_LABELS[r.preuve_type] ?? r.preuve_type}</p>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Extrait brut officiel de l&apos;arrêt</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="max-h-[420px] overflow-y-auto whitespace-pre-wrap rounded-md bg-secondary p-3 font-mono text-xs leading-relaxed text-muted-foreground">
                  {data.raw_excerpt || "Texte intégral indisponible."}
                </pre>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </Dialog>
  );
}
