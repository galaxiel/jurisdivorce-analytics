"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, FileDown, FileText, Info, Lightbulb, Printer, Target, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { REGIME_LABELS, type BoussoleFormState, type BoussoleReport } from "@/lib/types";
import { exportDossier, type DossierInput } from "@/lib/dossier";
import { formatEur, formatPct } from "@/lib/utils";

/* Étape 4 — Le Dashboard Prédictif : fourchettes, checklist de preuves, alertes pièges,
   et génération du dossier de synthèse (Markdown / impression PDF). */
export function ResultPanel({
  report,
  form,
  onRestart,
}: {
  report: BoussoleReport;
  form: BoussoleFormState;
  onRestart: () => void;
}) {
  const f = report.indemnite_fourchette;

  function buildDossier(): string {
    const lines: string[] = [
      "# Dossier de synthèse — JurisDivorce Analytics",
      "",
      `*Généré le ${new Date().toLocaleDateString("fr-FR")} — rapport statistique indicatif, ne constitue pas un avis juridique.*`,
      "",
      "## 1. Situation déclarée",
      `- Juridiction : ${form.juridiction}`,
      `- Régime matrimonial : ${REGIME_LABELS[form.regime_matrimonial] ?? form.regime_matrimonial}`,
      `- Durée du mariage : ${form.duree_mariage_annees} ans · ${form.nombre_enfants} enfant(s)`,
      `- Valeur locative estimée : ${form.valeur_locative_mensuelle} €/mois · occupation : ${form.mois_occupation} mois par ${form.occupant === "MOI" ? "vous" : "votre conjoint"}`,
      form.heritage_injecte ? `- Héritage injecté dans le bien : ${form.heritage_injecte} €` : "",
      "",
    ];
    if (f) {
      lines.push(
        "## 2. Indemnité d'occupation estimée",
        `| | Montant |`,
        `|---|---|`,
        `| Minimum | ${f.min} € |`,
        `| **Médiane** | **${f.mediane} €** |`,
        `| Maximum | ${f.max} € |`,
        `Pour ${f.mois} mois d'occupation, abattement médian observé : ${f.abattement_median_pct ?? "—"} %.`,
        "",
      );
    }
    if (report.chances_travaux) {
      lines.push(
        "## 3. Remboursement des travaux",
        `- Chances de succès : **${report.chances_travaux.taux_pct} %** avec « ${report.chances_travaux.preuve_retenue} »`,
        `- Moyenne toutes preuves confondues : ${report.chances_travaux.taux_global_pct} %`,
        "",
      );
    }
    if (report.prestation_compensatoire) {
      lines.push(
        "## 4. Prestation compensatoire (référence)",
        `- 10ᵉ percentile : ${report.prestation_compensatoire.capital_min} €`,
        `- Médiane : ${report.prestation_compensatoire.capital_mediane} €`,
        `- 90ᵉ percentile : ${report.prestation_compensatoire.capital_max} €`,
        "",
      );
    }
    if (report.checklist_preuves.length) {
      lines.push("## 5. Checklist des preuves indispensables (extraites des arrêts gagnants)");
      report.checklist_preuves.forEach((c) => lines.push(`- [ ] ${c.preuve} — présente dans ${c.frequence_pct} % des dossiers gagnants`));
      lines.push("");
    }
    if (report.alertes_pieges.length) {
      lines.push("## 6. Alertes pièges (extraites des arrêts perdants)");
      report.alertes_pieges.forEach((a) => lines.push(`- ⚠ ${a.piege} — cause d'échec dans ${a.frequence_pct} % des cas similaires`));
      lines.push("");
    }
    if (report.jumelles.length) {
      lines.push("## 7. Décisions « jumelles » les plus proches");
      report.jumelles.forEach((j, i) =>
        lines.push(`${i + 1}. **${j.juridiction}** (${j.date_decision}) — correspondance ${j.score}/10\n   ${j.resume_3_lignes ?? ""}`),
      );
      lines.push("");
    }
    lines.push("## 8. Notes méthodologiques");
    report.notes.forEach((n) => lines.push(`- ${n}`));
    return lines.filter((l) => l !== undefined).join("\n");
  }

  function downloadDossier() {
    const blob = new Blob([buildDossier()], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dossier-synthese-jurisdivorce.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  /* Chantier 2.2 : « Dire à Notaire / Note pour mon Avocat » sourcé par les arrêts similaires */
  function notaire(): DossierInput {
    return {
      titre: "Projet de « Dire à Notaire » — Simulation liquidation-partage",
      situation: [
        { label: "Juridiction compétente", value: form.juridiction },
        { label: "Régime matrimonial", value: REGIME_LABELS[form.regime_matrimonial] ?? form.regime_matrimonial },
        { label: "Durée du mariage / enfants", value: `${form.duree_mariage_annees} ans · ${form.nombre_enfants} enfant(s)` },
        { label: "Occupation exclusive", value: `${form.mois_occupation} mois par ${form.occupant === "MOI" ? "vous" : "votre conjoint"} · valeur locative ${formatEur(form.valeur_locative_mensuelle)}/mois` },
        ...(form.heritage_injecte ? [{ label: "Héritage injecté dans le bien", value: formatEur(form.heritage_injecte) }] : []),
      ],
      demandes: [
        ...(f ? [{ label: "Indemnité d'occupation (médiane observée)", value: `${formatEur(f.mediane)} (min ${formatEur(f.min)} / max ${formatEur(f.max)}) sur ${f.mois} mois` }] : []),
        ...(report.chances_travaux ? [{ label: "Récompense pour travaux", value: `chances de succès ${formatPct(report.chances_travaux.taux_pct)} avec « ${report.chances_travaux.preuve_retenue} »` }] : []),
        ...(report.prestation_compensatoire ? [{ label: "Prestation compensatoire (médiane observée)", value: formatEur(report.prestation_compensatoire.capital_mediane) }] : []),
      ],
      references: report.jumelles.slice(0, 5).map((j) => ({
        juridiction: j.juridiction ?? "",
        date: j.date_decision ?? "",
        rg: null,
        resume: j.resume_3_lignes ?? "",
      })),
      pieces: report.checklist_preuves.length
        ? report.checklist_preuves.map((c) => `${c.preuve} (présente dans ${c.frequence_pct} % des dossiers gagnants comparables)`)
        : ["Factures nominatives au nom du demandeur", "Relevés bancaires personnels traçant les paiements", "Estimation de valeur locative datée de la séparation", "Titre de propriété mentionnant les quotes-parts"],
      notes: report.notes,
    };
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between no-print">
        <h2 className="text-xl font-bold">Rapport prédictif statistique</h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => exportDossier(notaire(), "doc")}>
            <FileText className="mr-1.5 h-4 w-4" /> Dire à Notaire (Word)
          </Button>
          <Button variant="outline" size="sm" onClick={downloadDossier}>
            <FileDown className="mr-1.5 h-4 w-4" /> Dossier (Markdown)
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            <Printer className="mr-1.5 h-4 w-4" /> Imprimer / PDF
          </Button>
          <Button variant="ghost" size="sm" onClick={onRestart}>
            Refaire le questionnaire
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
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
                    <div className="text-xl font-bold tabular-nums">{formatEur(f.min)}</div>
                  </div>
                  <div className="rounded-lg bg-primary/10 p-3 ring-1 ring-primary/30">
                    <div className="text-xs text-primary">Médiane</div>
                    <div className="text-2xl font-bold tabular-nums text-primary">{formatEur(f.mediane)}</div>
                  </div>
                  <div className="rounded-lg bg-secondary p-3">
                    <div className="text-xs text-muted-foreground">Maximum</div>
                    <div className="text-xl font-bold tabular-nums">{formatEur(f.max)}</div>
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
                <div className="text-3xl font-bold tabular-nums text-success">{formatPct(report.chances_travaux.taux_pct)}</div>
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
                <div className="text-lg font-semibold tabular-nums">{formatEur(report.prestation_compensatoire.capital_min)}</div>
              </div>
              <div className="rounded-lg bg-secondary p-3">
                <div className="text-xs text-muted-foreground">Médiane</div>
                <div className="text-lg font-semibold tabular-nums">{formatEur(report.prestation_compensatoire.capital_mediane)}</div>
              </div>
              <div className="rounded-lg bg-secondary p-3">
                <div className="text-xs text-muted-foreground">90ᵉ percentile</div>
                <div className="text-lg font-semibold tabular-nums">{formatEur(report.prestation_compensatoire.capital_max)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Checklist des preuves indispensables */}
      {report.checklist_preuves.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-5 w-5 text-success" />
              Checklist des preuves indispensables
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.checklist_preuves.map((c) => (
              <div key={c.preuve} className="flex items-center gap-3">
                <span className="w-40 shrink-0 truncate text-sm">{c.preuve}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-success" style={{ width: `${c.frequence_pct}%` }} />
                </div>
                <span className="w-14 shrink-0 text-right text-xs tabular-nums text-muted-foreground">{c.frequence_pct} %</span>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">Fréquence d'apparition dans les dossiers gagnants comparables.</p>
          </CardContent>
        </Card>
      )}

      {/* Alertes pièges */}
      {report.alertes_pieges.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Alertes pièges (issues des arrêts perdants)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report.alertes_pieges.map((a) => (
              <div key={a.piege} className="flex items-center gap-3">
                <span className="w-72 shrink-0 truncate text-sm">{a.piege}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-destructive" style={{ width: `${a.frequence_pct}%` }} />
                </div>
                <span className="w-14 shrink-0 text-right text-xs tabular-nums text-muted-foreground">{a.frequence_pct} %</span>
              </div>
            ))}
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
                <Link href={`/decisions?id=${j.id}`}>Voir la fiche décisionnelle →</Link>
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
