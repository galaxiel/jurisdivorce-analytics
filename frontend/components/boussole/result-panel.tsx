"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, Info, Lightbulb, Target, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatEur, formatPct } from "@/lib/utils";
import type { BoussoleReport } from "@/lib/types";

/* Étape 4 — Le Dashboard Prédictif */
export function ResultPanel({ report, onRestart }: { report: BoussoleReport; onRestart: () => void }) {
  const f = report.indemnite_fourchette;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Rapport prédictif statistique</h2>
        <Button variant="outline" size="sm" onClick={onRestart}>
          Refaire le questionnaire
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {/* Fourchette indemnité d'occupation */}
        <Card className="md:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-5 w-5 text-primary" />
              Indemnité d&apos;occupation estimée
            </CardTitle>
          </CardHeader>
          <CardContent>
            {f ? (
              <>
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-lg bg-secondary p-3">
                    <div className="text-xs text-muted-foreground">Minimum</div>
                    <div className="text-xl font-bold">{formatEur(f.min)}</div>
                  </div>
                  <div className="rounded-lg bg-primary/10 p-3 ring-1 ring-primary/30">
                    <div className="text-xs text-primary">Médiane</div>
                    <div className="text-2xl font-bold text-primary">{formatEur(f.mediane)}</div>
                  </div>
                  <div className="rounded-lg bg-secondary p-3">
                    <div className="text-xs text-muted-foreground">Maximum</div>
                    <div className="text-xl font-bold">{formatEur(f.max)}</div>
                  </div>
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  Pour {f.mois} mois d&apos;occupation
                  {f.valeur_locative_utilisee ? ` (valeur locative de ${formatEur(f.valeur_locative_utilisee)}/mois)` : ""}
                  {f.abattement_median_pct != null ? ` — abattement médian observé : ${formatPct(f.abattement_median_pct)}` : ""}.
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Estimation indisponible.</p>
            )}
          </CardContent>
        </Card>

        {/* Chances travaux */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="h-5 w-5 text-primary" />
              Remboursement des travaux
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report.chances_travaux ? (
              <>
                <div className="text-3xl font-bold text-success">{formatPct(report.chances_travaux.taux_pct)}</div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-success transition-all"
                    style={{ width: `${Math.min(100, report.chances_travaux.taux_pct ?? 0)}%` }}
                  />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Avec « {report.chances_travaux.preuve_retenue} » — contre {formatPct(report.chances_travaux.taux_global_pct)} en moyenne
                  toutes preuves confondues.
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Aucun travaux déclaré dans le questionnaire.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Prestation compensatoire */}
      {report.prestation_compensatoire && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Info className="h-5 w-5 text-primary" />
              Prestation compensatoire (référence selon votre durée de mariage)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-secondary p-3">
                <div className="text-xs text-muted-foreground">10ᵉ percentile</div>
                <div className="text-lg font-semibold">{formatEur(report.prestation_compensatoire.capital_min)}</div>
              </div>
              <div className="rounded-lg bg-secondary p-3">
                <div className="text-xs text-muted-foreground">Médiane</div>
                <div className="text-lg font-semibold">{formatEur(report.prestation_compensatoire.capital_mediane)}</div>
              </div>
              <div className="rounded-lg bg-secondary p-3">
                <div className="text-xs text-muted-foreground">90ᵉ percentile</div>
                <div className="text-lg font-semibold">{formatEur(report.prestation_compensatoire.capital_max)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Jumelles */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">5 décisions de justice « jumelles » les plus proches</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {report.jumelles.map((j, i) => (
            <div key={j.id} className="rounded-lg border p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">#{i + 1}</Badge>
                <Badge variant="default">Correspondance {j.score}/10</Badge>
                <span className="text-sm font-semibold">{j.juridiction}</span>
                <span className="text-xs text-muted-foreground">
                  {j.date_decision} · {j.duree_mariage_annees} ans de mariage
                </span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{j.resume_3_lignes}</p>
              <Button asChild variant="link" size="sm" className="mt-1 h-auto p-0">
                <Link href={`/jurisprudence?id=${j.id}`}>Voir la fiche décisionnelle →</Link>
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Notes */}
      <Card>
        <CardContent className="pt-5">
          <ul className="space-y-2 text-sm text-muted-foreground">
            {report.notes.map((n, i) => (
              <li key={i} className="flex gap-2">
                <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
                {n}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
