"use client";

import { useState } from "react";
import { Calculator, FileDown, FileText, Loader2, Scale, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { postOccupationCalc, postRecompenseCalc, useApi } from "@/lib/api";
import { JURIDICTIONS, type OccupationCalcResult, type RecompenseCalcResult } from "@/lib/types";
import { exportDossier, type DossierInput } from "@/lib/dossier";
import { cn, formatEur, formatPct } from "@/lib/utils";

interface CalculateurSnapshot {
  cours: { juridiction: string; abattement_median: number }[];
  abattement_median_global: number | null;
  taux_rejet_amelioration: number | null;
  taux_rejet_entretien: number | null;
}

const TABS = [
  { key: "occupation" as const, label: "Indemnité d'occupation (art. 815-9)" },
  { key: "recompense" as const, label: "Récompense / profit subsistant (art. 1469)" },
  { key: "balance" as const, label: "Balance finale chez le notaire (Soulte)" },
];

/* Vue 6 — Calculateur juridique : formules légales + jurisprudence réelle.
   Fonctionne avec l'API live, ou bascule automatiquement sur le snapshot statique
   (frontend/public/data/calculateur.json) si l'API est injoignable. */
export default function CalculateurPage() {
  const [tab, setTab] = useState<"occupation" | "recompense" | "balance">("occupation");
  const [occupationResult, setOccupationResult] = useState<OccupationCalcResult | null>(null);
  const [recompenseResult, setRecompenseResult] = useState<RecompenseCalcResult | null>(null);

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-bold">Calculateur juridique</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Formules légales françaises couplées aux statistiques réelles de la base
          (abattement médian de votre cour, taux de rejet constatés, arrêts comparables).
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm font-medium transition-colors",
              tab === t.key
                ? "border-primary bg-primary/10 text-primary"
                : "bg-card text-muted-foreground hover:bg-secondary",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "occupation" && (
        <OccupationCalc result={occupationResult} setResult={setOccupationResult} />
      )}
      {tab === "recompense" && (
        <RecompenseCalc result={recompenseResult} setResult={setRecompenseResult} />
      )}
      {tab === "balance" && (
        <BalanceFinale occupationResult={occupationResult} recompenseResult={recompenseResult} />
      )}
    </div>
  );
}

/* ------------------------------------------------------------ Art. 815-9 */
function OccupationCalc({
  result,
  setResult,
}: {
  result: OccupationCalcResult | null;
  setResult: (r: OccupationCalcResult | null) => void;
}) {
  const snapshot = useApi<CalculateurSnapshot>("/data/calculateur.json");
  const [juridiction, setJuridiction] = useState(JURIDICTIONS[0]);
  const [vl, setVl] = useState(900);
  const [debut, setDebut] = useState("2021-01-01");
  const [fin, setFin] = useState(new Date().toISOString().slice(0, 10));
  const [quotePart, setQuotePart] = useState(50);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function monthsBetween(a: string, b: string): number {
    const d1 = new Date(a);
    const d2 = new Date(b);
    if (Number.isNaN(d1.getTime()) || Number.isNaN(d2.getTime()) || d2 < d1) return 0;
    return Math.max(1, Math.round((d2.getTime() - d1.getTime()) / (30.44 * 24 * 3600 * 1000)));
  }

  /** Même calcul que le backend, exécuté côté client avec le snapshot statique. */
  function computeLocal(): OccupationCalcResult {
    const snap = snapshot.data;
    const abatMedian =
      snap?.cours.find((c) => c.juridiction === juridiction)?.abattement_median ??
      snap?.abattement_median_global ??
      null;
    const mois = monthsBetween(debut, fin);
    const abatEff = (abatMedian ?? 0) / 100;
    const base = vl * mois * (quotePart / 100);
    const moisRec = Math.min(mois, 60);
    return {
      mois,
      montant_brut: Math.round(base),
      abattement_median_pct: abatMedian,
      montant_net: Math.round(base * (1 - abatEff)),
      prescription: {
        depassement_mois: Math.max(0, mois - 60),
        mois_recouvrables: moisRec,
        montant_recuperable: Math.round(vl * moisRec * (quotePart / 100) * (1 - abatEff)),
        alerte: mois > 60,
      },
      comparables: [],
      echantillon: 0,
    };
  }

  async function compute() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await postOccupationCalc({
          juridiction,
          valeur_locative_mensuelle: vl,
          date_debut: debut,
          date_fin: fin,
          quote_part_autres_pct: quotePart,
        }),
      );
    } catch {
      if (snapshot.data) {
        setResult(computeLocal());
        setError(null);
      } else {
        setError("API injoignable et snapshot absent — lancez scripts/export_static_bundle.py.");
      }
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
        {
          label: "Part nette du conjoint non-occupant (après abattement médian)",
          value: `${formatEur(result.montant_net)} (abattement médian observé : ${formatPct(result.abattement_median_pct)})`,
        },
        ...(result.prescription.alerte
          ? [
              {
                label: "Prescription quinquennale",
                value: `${result.prescription.depassement_mois} mois au-delà de 5 ans : montant recouvrable plafonné à ${formatEur(result.prescription.montant_recuperable)} sans acte interruptif`,
              },
            ]
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
        "Fondement légal : art. 815-9 du Code civil — l'indemnité est due à l'indivision et "
        + "profite à chaque co-indivisaire à proportion de ses droits.",
        `Échantillon : ${result.echantillon || "snapshot"} décisions d'occupation accordée.`,
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
          L&apos;indemnité d&apos;occupation (art. 815-9 du Code civil) est due <b>à
          l&apos;indivision</b> : chaque co-indivisaire non-occupant en perçoit sa part, à
          proportion de ses droits. Elle est souvent réduite d&apos;un abattement de précarité.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Cour d&apos;appel</Label>
            <Select value={juridiction} onChange={(e) => setJuridiction(e.target.value)}>
              {JURIDICTIONS.map((j) => (
                <option key={j} value={j}>{j}</option>
              ))}
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
            <input
              type="range" min={0} max={100} step={5} value={quotePart}
              onChange={(e) => setQuotePart(Number(e.target.value))}
              className="w-full accent-[hsl(var(--primary))]"
            />
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
                <div className="text-xs text-primary">Part nette du conjoint non-occupant</div>
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

            {result.comparables.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-semibold">Les 10 arrêts les plus proches de votre cour</h3>
                <div className="space-y-2">
                  {result.comparables.map((c) => (
                    <div key={c.id} className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-xs">
                      <span className="font-semibold">{c.juridiction}</span>
                      <span className="text-muted-foreground">{c.date_decision} · {c.numero_rg}</span>
                      <Badge variant="secondary">Abattement {c.abattement_pct} %</Badge>
                      <span className="ml-auto font-medium">
                        {formatEur(c.montant_mensuel_final)}/mois × {c.duree_mois} mois = {formatEur(c.montant_total)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
function RecompenseCalc({
  result,
  setResult,
}: {
  result: RecompenseCalcResult | null;
  setResult: (r: RecompenseCalcResult | null) => void;
}) {
  const snapshot = useApi<CalculateurSnapshot>("/data/calculateur.json");
  const [avant, setAvant] = useState(400000);
  const [actuelle, setActuelle] = useState(480000);
  const [travaux, setTravaux] = useState(50000);
  const [nature, setNature] = useState<"amelioration" | "entretien">("amelioration");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function compute() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await postRecompenseCalc({
          valeur_bien_avant_travaux: avant,
          valeur_bien_actuelle: actuelle,
          montant_travaux: travaux,
          nature,
        }),
      );
    } catch {
      if (snapshot.data) {
        const plusValue = Math.max(0, actuelle - avant);
        setResult({
          plus_value: plusValue,
          profit_subsistant: Math.min(travaux, plusValue),
          depense_faite: travaux,
          regle: plusValue < travaux ? "Profit subsistant" : "Dépense faite",
          taux_rejet_amelioration_pct: snapshot.data.taux_rejet_amelioration,
          taux_rejet_entretien_pct: snapshot.data.taux_rejet_entretien,
          alertes:
            plusValue === 0
              ? ["Aucune plus-value constatée : la récompense est plafonnée au profit subsistant (art. 1469 III)."]
              : [],
        });
      } else {
        setError("API injoignable et snapshot absent — lancez scripts/export_static_bundle.py.");
      }
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

/* ------------------------------------------------------------ Balance finale (soulte) */
interface BalanceResult {
  actifBrut: number;
  creditRestant: number;
  actifNet: number;
  partA: number;
  partB: number;
  creditA: number;
  creditB: number;
  droitsA: number;
  droitsB: number;
  gardien: "A" | "B";
  soulte: number;
  sens: string;
}

function BalanceFinale({
  occupationResult,
  recompenseResult,
}: {
  occupationResult: OccupationCalcResult | null;
  recompenseResult: RecompenseCalcResult | null;
}) {
  const [valeurBien, setValeurBien] = useState(450000);
  const [credit, setCredit] = useState(80000);
  const [quoteA, setQuoteA] = useState(50);
  const [nonOccupant, setNonOccupant] = useState<"A" | "B">("B");
  const [indemnite, setIndemnite] = useState(0);
  const [creancesA, setCreancesA] = useState(0);
  const [creancesB, setCreancesB] = useState(0);
  const [gardien, setGardien] = useState<"A" | "B">("A");
  const [result, setResult] = useState<BalanceResult | null>(null);

  function compute(): BalanceResult {
    const actifBrut = Math.max(0, valeurBien);
    const actifNet = Math.max(0, actifBrut - credit);
    const partA = Math.round(actifNet * (quoteA / 100));
    const partB = actifNet - partA;
    const indemnitePour = nonOccupant; // l'indemnité profite au non-occupant
    const creditA = creancesA + (indemnitePour === "A" ? indemnite : 0);
    const creditB = creancesB + (indemnitePour === "B" ? indemnite : 0);
    const droitsA = partA + creditA;
    const droitsB = partB + creditB;
    // Le gardien attribue le bien à lui-même : il compense l'autre sur la totalité de ses droits.
    const autre = gardien === "A" ? "B" : "A";
    const soulte = Math.round(autre === "A" ? droitsA : droitsB);
    return {
      actifBrut,
      creditRestant: credit,
      actifNet,
      partA,
      partB,
      creditA,
      creditB,
      droitsA,
      droitsB,
      gardien,
      soulte,
      sens: `versés par l'époux ${gardien} à l'époux ${autre}`,
    };
  }

  function notaire(res: RecompenseCalcResult | null): DossierInput | null {
    if (!res || !result) return null;
    const autre = gardien === "A" ? "B" : "A";
    return {
      titre: "Projet de « Dire à Notaire » — Balance finale de l'indivision et soulte",
      situation: [
        { label: "Valeur vénale du bien indivis", value: formatEur(result.actifBrut) },
        { label: "Capital restant dû du crédit", value: formatEur(result.creditRestant) },
        { label: "Actif net de l'indivision", value: formatEur(result.actifNet) },
        { label: "Quote-parts", value: `Époux A : ${quoteA} % · Époux B : ${100 - quoteA} %` },
        { label: "Attribution du bien", value: `à l'époux ${gardien}` },
      ],
      demandes: [
        { label: `Droits de l'époux ${gardien} (part + comptes)`, value: formatEur(gardien === "A" ? result.droitsA : result.droitsB) },
        { label: `Droits de l'époux ${autre} (part + comptes)`, value: formatEur(autre === "A" ? result.droitsA : result.droitsB) },
        { label: "Soulte à verser", value: `${formatEur(result.soulte)} ${result.sens} (modèle simplifié, hors frais)` },
      ],
      references: [],
      pieces: [
        "Titre de propriété et tableau de répartition des quotes-parts",
        "Relevé du capital restant dû du crédit immobilier",
        "Justificatifs de l'indemnité d'occupation calculée",
        "Justificatifs des créances de chaque époux (factures, relevés)",
      ],
      notes: [
        "Modèle simplifié : hors frais de notaire, intérêts et fiscalité de la soulte.",
        "Les règles d'imputation détaillées (art. 1469, décret) relèvent du notaire liquidateur.",
      ],
    };
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Scale className="h-5 w-5 text-primary" /> Balance finale chez le notaire — Soulte
        </CardTitle>
        <CardDescription>
          Combinez tous les postes en un seul tableau récapitulatif : actif net, droits de chaque
          époux et montant de la soulte due à celui qui ne garde pas le bien.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Valeur vénale du bien immobilier indivis (€)</Label>
            <Input type="number" min={0} value={valeurBien} onChange={(e) => setValeurBien(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Capital restant dû du crédit (€)</Label>
            <Input type="number" min={0} value={credit} onChange={(e) => setCredit(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label>Quote-part de l&apos;époux A : {quoteA} % · époux B : {100 - quoteA} %</Label>
            <input
              type="range" min={0} max={100} step={5} value={quoteA}
              onChange={(e) => setQuoteA(Number(e.target.value))}
              className="w-full accent-[hsl(var(--primary))]"
            />
          </div>
        </div>

        {occupationResult && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border bg-secondary/50 px-3 py-2 text-xs">
            <span>
              Indemnité d&apos;occupation nette calculée à l&apos;onglet 1 :{" "}
              <b>{formatEur(occupationResult.montant_net)}</b>
            </span>
            <Button
              size="sm" variant="outline" className="h-7 text-xs"
              onClick={() => setIndemnite(Math.round(occupationResult.montant_net))}
            >
              Importer
            </Button>
          </div>
        )}
        {recompenseResult && (
          <div className="flex flex-wrap items-center gap-2 rounded-md border bg-secondary/50 px-3 py-2 text-xs">
            <span>
              Récompense calculée à l&apos;onglet 2 : <b>{formatEur(recompenseResult.profit_subsistant)}</b>
            </span>
            <Button
              size="sm" variant="outline" className="h-7 text-xs"
              onClick={() => setCreancesA(Math.round(recompenseResult.profit_subsistant))}
            >
              Importer comme créance de l&apos;époux A
            </Button>
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Indemnité d&apos;occupation nette accumulée (€)</Label>
            <Input type="number" min={0} value={indemnite} onChange={(e) => setIndemnite(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Bénéficiaire de l&apos;indemnité (non-occupant)</Label>
            <Select value={nonOccupant} onChange={(e) => setNonOccupant(e.target.value as "A" | "B")}>
              <option value="A">Époux A</option>
              <option value="B">Époux B</option>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Créances de l&apos;époux A (travaux, crédit…) — €</Label>
            <Input type="number" min={0} value={creancesA} onChange={(e) => setCreancesA(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Créances de l&apos;époux B — €</Label>
            <Input type="number" min={0} value={creancesB} onChange={(e) => setCreancesB(Math.max(0, Number(e.target.value)))} />
          </div>
          <div className="space-y-1.5">
            <Label>Qui garde le bien ?</Label>
            <Select value={gardien} onChange={(e) => setGardien(e.target.value as "A" | "B")}>
              <option value="A">Époux A</option>
              <option value="B">Époux B</option>
            </Select>
          </div>
        </div>

        <Button onClick={() => setResult(compute())}>
          <Calculator className="mr-1.5 h-4 w-4" /> Calculer la balance finale
        </Button>

        {result && (
          <div className="space-y-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Poste</TableHead>
                  <TableHead className="text-right">Époux A</TableHead>
                  <TableHead className="text-right">Époux B</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell>Actif net (bien − crédit restant dû)</TableCell>
                  <TableCell className="text-right tabular-nums">{formatEur(result.partA)}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatEur(result.partB)}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Indemnité d&apos;occupation (au non-occupant)</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {nonOccupant === "A" ? formatEur(indemnite) : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {nonOccupant === "B" ? formatEur(indemnite) : "—"}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Créances / récompenses</TableCell>
                  <TableCell className="text-right tabular-nums">{formatEur(creancesA)}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatEur(creancesB)}</TableCell>
                </TableRow>
                <TableRow className="bg-secondary/50 font-semibold">
                  <TableCell>Droits totaux</TableCell>
                  <TableCell className="text-right tabular-nums">{formatEur(result.droitsA)}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatEur(result.droitsB)}</TableCell>
                </TableRow>
              </TableBody>
            </Table>

            <div className="rounded-lg bg-primary/10 p-4 text-center ring-1 ring-primary/30">
              <div className="text-sm text-primary">
                Soulte — {result.sens} (l&apos;époux {result.gardien} garde le bien)
              </div>
              <div className="text-3xl font-bold tabular-nums text-primary">{formatEur(result.soulte)}</div>
              <p className="mt-1 text-xs text-muted-foreground">
                Modèle simplifié hors frais de notaire et fiscalité ; les règles d&apos;imputation
                détaillées relèvent du notaire liquidateur.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline" size="sm"
                onClick={() => { const d = notaire(recompenseResult); if (d) exportDossier(d, "doc"); }}
              >
                <FileText className="mr-1.5 h-4 w-4" /> Dire à Notaire (Word)
              </Button>
              <Button
                variant="outline" size="sm"
                onClick={() => { const d = notaire(recompenseResult); if (d) exportDossier(d, "md"); }}
              >
                <FileDown className="mr-1.5 h-4 w-4" /> Markdown
              </Button>
              <Button
                variant="outline" size="sm"
                onClick={() => { const d = notaire(recompenseResult); if (d) exportDossier(d, "print"); }}
              >
                <Calculator className="mr-1.5 h-4 w-4" /> Imprimer / PDF
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
