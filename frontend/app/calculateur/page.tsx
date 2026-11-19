"use client";

import { useState } from "react";
import { Calculator, FileDown, FileText, Loader2, Scale, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { postOccupationCalc, postRecompenseCalc } from "@/lib/api";
import { JURIDICTIONS, type OccupationCalcResult, type RecompenseCalcResult } from "@/lib/types";
import { exportDossier, type DossierInput } from "@/lib/dossier";
import { formatEur, formatPct } from "@/lib/utils";
import { cn } from "@/lib/utils";

/* Vue 6 — Calculateur juridique couplant formules légales et jurisprudence réelle. */
export default function CalculateurPage() {
  const [tab, setTab] = useState<"occupation" | "recompense">("occupation");
  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold">Calculateur juridique</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Formules légales françaises couplées aux statistiques réelles de la base
          (abattement médian de votre cour, taux de rejet constatés, arrêts comparables).
        </p>
      </div>

      <div className="flex gap-2">
        {[
          { key: "occupation" as const, label: "Indemnité d'occupation (art. 815-9)" },
          { key: "recompense" as const, label: "Récompense / profit subsistant (art. 1469)" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
              tab === t.key ? "border-primary bg-primary/10 text-primary" : "bg-card text-muted-foreground hover:bg-secondary",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "occupation" ? <OccupationCalc /> : <RecompenseCalc />}
    </div>
  );
}

/* ------------------------------------------------------------ Art. 815-9 */
function OccupationCalc() {
  const [juridiction, setJuridiction] = useState(JURIDICTIONS[0]);
  const [vl, setVl] = useState(900);
  const [debut, setDebut] = useState("2021-01-01");
  const [fin, setFin] = useState(new Date().toISOString().slice(0, 10));
  const [quotePart, setQuotePart] = useState(50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<OccupationCalcResult | null>(null);

  async function compute() {
    setLoading(true);
    setError(null);
    try {
      setResult(await postOccupationCalc({ juridiction, valeur_locative_mensuelle: vl, date_debut: debut, date_fin: fin, quote_part_autres_pct: quotePart }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function dossier(): DossierInput | null {
    if (!result) return null;
    return {
      titre: "Projet de « Dire à Notaire » — Indemnité d'occupation (art. 815-9 C. civ.)",
      situation: [
        { label: "Cour d'appel territorialement compétente", value: juridiction },
        { label: "Valeur locative mensuelle estimée", value: formatEur(vl) },
        { label: "Occupation exclusive", value: `du ${debut} au ${fin} (${result.mois} mois)` },
        { label: "Quote-part revenant aux non-occupants", value: `${quotePart} %` },
      ],
      demandes: [
        { label: "Indemnité théorique brute", value: formatEur(result.montant_brut) },
        { label: "Indemnité nette après abattement de précarité médian", value: `${formatEur(result.montant_net)} (abattement médian observé : ${formatPct(result.abattement_median_pct)} sur ${result.echantillon} décisions)` },
        ...(result.prescription.alerte
          ? [{ label: "⚠ Prescription quinquennale", value: `${result.prescription.depassement_mois} mois au-delà de 5 ans : montant recouvrable plafonné à ${formatEur(result.prescription.montant_recuperable)} sans acte interruptif` }]
          : []),
      ],
      references: result.comparables.slice(0, 5).map((c) => ({
        juridiction: c.juridiction ?? "",
        date: c.date_decision ?? "",
        rg: c.numero_rg,
        resume: `Occupation accordée avec abattement de ${c.abattement_pct} % — ${formatEur(c.montant_mensuel_final)}/mois pendant ${c.duree_mois} mois (total ${formatEur(c.montant_total)}).`,
      })),
      pieces: [
        "Ordonnance de non-conciliation ou assignation fixant le début de l'occupation exclusive",
        "Estimation de valeur locative par agence immobilière (datée de la séparation)",
        "Constat de commissaire de justice établissant l'occupation exclusive",
        "Titre de propriété mentionnant les quotes-parts",
        "Tout acte interruptif de prescription (mise en demeure, assignation) le cas échéant",
      ],
      notes: [
        `Échantillon : ${result.echantillon} décisions d'occupation accordée de la cour (ou plan national si échantillon trop faible).`,
        "Fondement légal : art. 815-9 du Code civil (indivision) et art. 1469 pour les récompenses.",
      ],
    };
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Scale className="h-5 w-5 text-primary" /> Indemnité d&apos;occupation en indivision
        </CardTitle>
        <CardDescription>
          L&apos;occupant doit aux autres indivisaires une indemnité proportionnelle à sa quote-part
          (art. 815-9), souvent réduite d&apos;un abattement de précarité.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Cour d&apos;appel</Label>
            <Select value={juridiction} onChange={(e) => setJuridiction(e.target.value)}>
              {JURIDICTIONS.map((j) => <option key={j} value={j}>{j}</option>)}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Valeur locative mensuelle estimée (€)</Label>
            <Input type="number" min={0} value={vl} onChange={(e) => setVl(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Début de l&apos;occupation exclusive (ONC / assignation)</Label>
            <Input type="date" value={debut} onChange={(e) => setDebut(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Date prévue du partage</Label>
            <Input type="date" value={fin} onChange={(e) => setFin(e.target.value)} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Quote-part revenant aux non-occupants : {quotePart} %</Label>
            <input type="range" min={0} max={100} step={5} value={quotePart} onChange={(e) => setQuotePart(Number(e.target.value))} className="w-full accent-[hsl(var(--primary))]" />
          </div>
        </div>

        <Button onClick={compute} disabled={loading}>
          {loading && <Loader2 className="h-4 w-4 animate-spin" />} Calculer avec la jurisprudence de ma cour
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}

        {result && (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg bg-secondary p-3 text-center">
                <div className="text-xs text-muted-foreground">Brut ({result.mois} mois × {quotePart} %)</div>
                <div className="text-xl font-bold tabular-nums">{formatEur(result.montant_brut)}</div>
              </div>
              <div className="rounded-lg bg-primary/10 p-3 text-center ring-1 ring-primary/30">
                <div className="text-xs text-primary">Net après abattement médian</div>
                <div className="text-2xl font-bold tabular-nums text-primary">{formatEur(result.montant_net)}</div>
              </div>
              <div className="rounded-lg bg-secondary p-3 text-center">
                <div className="text-xs text-muted-foreground">Abattement médian de la cour</div>
                <div className="text-xl font-bold tabular-nums">{formatPct(result.abattement_median_pct)}</div>
              </div>
            </div>

            {result.prescription.alerte && (
              <div className="flex gap-2 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                <div>
                  <b>Prescription quinquennale dépassée de {result.prescription.depassement_mois} mois.</b>{" "}
                  Sans acte interruptif (mise en demeure, assignation), seules les 5 dernières années sont
                  recouvrables : <b>{formatEur(result.prescription.montant_recuperable)}</b> au lieu de{" "}
                  {formatEur(result.montant_net)}.
                </div>
              </div>
            )}

            <div>
              <h3 className="mb-2 text-sm font-semibold">Les 10 arrêts les plus proches de votre cour</h3>
              <div className="space-y-2">
                {result.comparables.map((c) => (
                  <div key={c.id} className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-xs">
                    <span className="font-semibold">{c.juridiction}</span>
                    <span className="text-muted-foreground">{c.date_decision} · {c.numero_rg}</span>
                    <Badge variant="secondary">Abattement {c.abattement_pct} %</Badge>
                    <span className="ml-auto font-medium">{formatEur(c.montant_mensuel_final)}/mois × {c.duree_mois} mois = {formatEur(c.montant_total)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => exportDossier(dossier()!, "doc")}>
                <FileText className="mr-1.5 h-4 w-4" /> Dire à Notaire (Word)
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportDossier(dossier()!, "md")}>
                <FileDown className="mr-1.5 h-4 w-4" /> Markdown
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportDossier(dossier()!, "print")}>
                <Calculator className="mr-1.5 h-4 w-4" /> Imprimer / PDF
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------ Art. 1469 */
function RecompenseCalc() {
  const [avant, setAvant] = useState(400000);
  const [actuelle, setActuelle] = useState(480000);
  const [travaux, setTravaux] = useState(50000);
  const [nature, setNature] = useState<"amelioration" | "entretien">("amelioration");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecompenseCalcResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function compute() {
    setLoading(true);
    setError(null);
    try {
      setResult(await postRecompenseCalc({ valeur_bien_avant_travaux: avant, valeur_bien_actuelle: actuelle, montant_travaux: travaux, nature }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function dossier(): DossierInput | null {
    if (!result) return null;
    return {
      titre: "Projet de « Dire à Notaire » — Récompense pour travaux (art. 1469 C. civ.)",
      situation: [
        { label: "Valeur du bien avant travaux", value: formatEur(avant) },
        { label: "Valeur actuelle du bien", value: formatEur(actuelle) },
        { label: "Travaux financés", value: `${formatEur(travaux)} (${nature === "amelioration" ? "amélioration" : "entretien"})` },
      ],
      demandes: [
        { label: "Plus-value constatée", value: formatEur(result.plus_value) },
        { label: "Règle de calcul appliquée", value: result.regle },
        { label: "Récompense réclamée", value: `${formatEur(result.profit_subsistant)} (plafonnée au profit subsistant, art. 1469 III)` },
        { label: "Contexte jurisprudentiel", value: `taux de rejet constaté : ${formatPct(result.taux_rejet_amelioration_pct)} (amélioration) / ${formatPct(result.taux_rejet_entretien_pct)} (prox. entretien)` },
      ],
      references: [],
      pieces: [
        "Factures nominatives des travaux au nom de l'époux demandeur",
        "Relevés bancaires personnels traçant les paiements",
        "Devis avant/après et factures finales des entreprises",
        "Expertise de valorisation du bien avant et après travaux",
        "Clause de remploi notariée le cas échéant (origine propre des fonds)",
      ],
      notes: result.alertes,
    };
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Scale className="h-5 w-5 text-primary" /> Récompense / profit subsistant
        </CardTitle>
        <CardDescription>
          La récompense est la dépense faite, plafonnée au profit subsistant au jour du partage (art. 1469).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Valeur du bien avant travaux (€)</Label>
            <Input type="number" min={0} value={avant} onChange={(e) => setAvant(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Valeur actuelle du bien (€)</Label>
            <Input type="number" min={0} value={actuelle} onChange={(e) => setActuelle(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Montant des travaux financés (€)</Label>
            <Input type="number" min={0} value={travaux} onChange={(e) => setTravaux(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Nature des travaux</Label>
            <Select value={nature} onChange={(e) => setNature(e.target.value as "amelioration" | "entretien")}>
              <option value="amelioration">Amélioration (agrandissement, rénovation lourde…)</option>
              <option value="entretien">Entretien courant (non remboursable)</option>
            </Select>
          </div>
        </div>

        <Button onClick={compute} disabled={loading}>
          {loading && <Loader2 className="h-4 w-4 animate-spin" />} Calculer la récompense
        </Button>
        {error && <p className="text-sm text-destructive">{error}</p>}

        {result && (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg bg-secondary p-3 text-center">
                <div className="text-xs text-muted-foreground">Plus-value</div>
                <div className="text-lg font-bold tabular-nums">{formatEur(result.plus_value)}</div>
              </div>
              <div className="rounded-lg bg-secondary p-3 text-center">
                <div className="text-xs text-muted-foreground">Dépense faite</div>
                <div className="text-lg font-bold tabular-nums">{formatEur(result.depense_faite)}</div>
              </div>
              <div className="rounded-lg bg-success/10 p-3 text-center ring-1 ring-success/30">
                <div className="text-xs text-success">Récompense ({result.regle})</div>
                <div className="text-2xl font-bold tabular-nums text-success">{formatEur(result.profit_subsistant)}</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant={result.taux_rejet_amelioration_pct && result.taux_rejet_amelioration_pct > 40 ? "destructive" : "secondary"}>
                Rejet travaux d&apos;amélioration : {formatPct(result.taux_rejet_amelioration_pct)}
              </Badge>
              <Badge variant="warning">Rejet prox. entretien : {formatPct(result.taux_rejet_entretien_pct)}</Badge>
            </div>

            {result.alertes.map((a, i) => (
              <div key={i} className="flex gap-2 rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">
                <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" /> {a}
              </div>
            ))}

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => exportDossier(dossier()!, "doc")}>
                <FileText className="mr-1.5 h-4 w-4" /> Dire à Notaire (Word)
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportDossier(dossier()!, "md")}>
                <FileDown className="mr-1.5 h-4 w-4" /> Markdown
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportDossier(dossier()!, "print")}>
                <Calculator className="mr-1.5 h-4 w-4" /> Imprimer / PDF
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
