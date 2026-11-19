"use client";

import { useState } from "react";
import {
  ArrowLeft, Calculator, Car, FileDown, FileText, Home, KeyRound,
  Loader2, Plus, Printer, Receipt, Trash2, Users,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  BIEN_TYPE_LABELS, MODE_GARDE_LABELS, STATUT_LABELS,
  defaultSimForm, newBien, type SimBien, type SimFormState, type SimStatut,
} from "@/lib/simulateur-types";
import {
  computeDiagnosticLocal, type SimDiagnostic,
} from "@/lib/simulateur-diagnostic";
import { postSimulateurDiagnostic, useApi } from "@/lib/api";
import { exportDossier, type DossierInput } from "@/lib/dossier";
import { COURS_APPEL_OFFICIELLES } from "@/lib/types";
import { useEntitlements } from "@/lib/entitlements";
import { PaywallOverlay, PaywallHint } from "@/components/paywall-overlay";
import { cn, formatEur, formatPct } from "@/lib/utils";

const STEPS = [
  "Situation & chronologie",
  "Revenus & charges",
  "Biens & véhicules",
  "Demandes annexes",
  "Diagnostic complet",
];

/* Vue 4 — Simulateur « Mon Cas » V5 : configurateur modulaire multi-situations. */
export default function SimulateurPage() {
  const [form, setForm] = useState(() => defaultSimForm(COURS_APPEL_OFFICIELLES[0]));
  const { tier, unlock } = useEntitlements();
  const [step, setStep] = useState(1);
  const [report, setReport] = useState<SimDiagnostic | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function patch(p: Partial<SimFormState>) {
    setForm((f) => ({ ...f, ...p }));
  }

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const res = await postSimulateurDiagnostic(form);
      setReport(res as SimDiagnostic);
      setStep(5);
    } catch {
      // Mode statique : diagnostic client sur le snapshot decisions_index.json
      try {
        const idx = await fetch("/data/decisions_index.json").then((r) => r.json());
        setReport(computeDiagnosticLocal(form, idx));
        setStep(5);
      } catch (e2) {
        setError((e2 as Error).message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold">Simulateur « Mon Cas »</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Cochez uniquement ce qui vous concerne : le diagnostic s&apos;adapte à votre situation
        (mariage, PACS, concubinage — un ou plusieurs biens, demandes annexes).
      </p>

      <div className="mt-6 flex flex-wrap gap-1.5">
        {STEPS.map((label, i) => {
          const n = i + 1;
          const done = step > n;
          const active = step === n;
          return (
            <button
              key={label}
              type="button"
              onClick={() => (report ? setStep(5) : n < 5 && setStep(n))}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                done ? "border-success bg-success/10 text-success"
                  : active ? "border-primary bg-primary text-primary-foreground"
                    : "bg-card text-muted-foreground hover:bg-secondary",
              )}
            >
              {n}. {label}
            </button>
          );
        })}
      </div>

      <Card className="mt-6">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{STEPS[step - 1]}</CardTitle>
        </CardHeader>
        <CardContent>
          {step === 1 && <StepSituation form={form} patch={patch} />}
          {step === 2 && <StepRevenus form={form} patch={patch} />}
          {step === 3 && <StepBiens form={form} patch={patch} />}
          {step === 4 && <StepDemandes form={form} patch={patch} />}
          {step === 5 && report && (
            <StepDiagnostic report={report} form={form} onRestart={() => {
              setReport(null); setStep(1);
              setForm(defaultSimForm(form.juridiction));
            }} />
          )}

          {error && <p className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

          {step < 5 && (
            <div className="mt-6 flex justify-between">
              <Button variant="ghost" onClick={() => setStep(Math.max(1, step - 1))} disabled={step === 1}>
                <ArrowLeft className="mr-1 h-4 w-4" /> Retour
              </Button>
              <Button onClick={submit} disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                {step === 4 ? "Générer mon diagnostic" : "Continuer"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

const JURIDICTIONS_DEFAULT = [
  "Cour d'appel de Paris", "Cour d'appel de Versailles", "Cour d'appel de Lyon",
  "Cour d'appel d'Aix-en-Provence", "Cour d'appel de Rennes", "Cour d'appel de Bordeaux",
];

/* ------------------------------------------------------------ Étape 1 */
function StepSituation({ form, patch }: { form: SimFormState; patch: (p: Partial<SimFormState>) => void }) {
  return (
    <div className="space-y-5">
      <div className="space-y-1.5">
        <Label>Statut</Label>
        <Select value={form.statut} onChange={(e) => patch({ statut: e.target.value as SimStatut })}>
          {Object.entries(STATUT_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </Select>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1.5">
          <Label>Date du mariage / PACS</Label>
          <Input type="date" value={form.date_mariage} onChange={(e) => patch({ date_mariage: e.target.value })} />
        </div>
        <div className="space-y-1.5">
          <Label>Date réelle de séparation (fin de vie commune)</Label>
          <Input type="date" value={form.date_separation} onChange={(e) => patch({ date_separation: e.target.value })} />
        </div>
        <div className="space-y-1.5">
          <Label>Date de l&apos;assignation en divorce</Label>
          <Input type="date" value={form.date_assignation} onChange={(e) => patch({ date_assignation: e.target.value })} />
        </div>
      </div>
      <div className="rounded-lg border border-info/40 bg-info/5 p-3 text-xs text-muted-foreground">
        Art. 262-1 du Code civil : pour les mariés sous communauté, les biens acquis après
        l&apos;assignation (mais avant le divorce) tombent en <b>indivision</b> — la communauté
        bascule. La vie commune <b>antérieure au mariage</b> n&apos;est pas retenue par les juges
        pour la prestation compensatoire.
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>Enfants à charge</Label>
          <Input type="number" min={0} max={12} value={form.enfants}
            onChange={(e) => patch({ enfants: Math.max(0, Number(e.target.value)) })} />
        </div>
        <div className="space-y-1.5">
          <Label>Mode de garde</Label>
          <Select value={form.mode_garde} onChange={(e) => patch({ mode_garde: e.target.value as SimFormState["mode_garde"] })}>
            {Object.entries(MODE_GARDE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </Select>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ Étape 2 */
function RevenusEditor({
  qui, form, patch,
}: {
  qui: "a" | "b"; form: SimFormState; patch: (p: Partial<SimFormState>) => void;
}) {
  const p = (k: keyof SimFormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    patch({ [k]: Math.max(0, Number(e.target.value)) } as Partial<SimFormState>);
  const label = qui === "a" ? "Époux / parent A" : "Époux / parent B";
  const k = (s: string) => `rev_${qui}_${s}` as keyof SimFormState;
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Users className="h-4 w-4 text-primary" /> {label}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1"><Label className="text-xs">Revenus nets mensuels (salaires / BIC / BNC)</Label>
          <Input type="number" min={0} value={form[k("net")] as number} onChange={p(k("net"))} /></div>
        <div className="space-y-1"><Label className="text-xs">Revenus complémentaires (fonciers, primes)</Label>
          <Input type="number" min={0} value={form[k("compl")] as number} onChange={p(k("compl"))} /></div>
        <div className="space-y-1"><Label className="text-xs">Prestations sociales &amp; allocations perçues</Label>
          <Input type="number" min={0} value={form[k("presta")] as number} onChange={p(k("presta"))} /></div>
        <div className="space-y-1"><Label className="text-xs">Charges fixes (loyer / crédit personnel)</Label>
          <Input type="number" min={0} value={form[k("charges")] as number} onChange={p(k("charges"))} /></div>
      </CardContent>
    </Card>
  );
}

function StepRevenus({ form, patch }: { form: SimFormState; patch: (p: Partial<SimFormState>) => void }) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Les prestations sociales et allocations sont intégrées dans l&apos;appréciation globale
        des ressources par le juge pour la prestation compensatoire.
      </p>
      <RevenusEditor qui="a" form={form} patch={patch} />
      <RevenusEditor qui="b" form={form} patch={patch} />
    </div>
  );
}

/* ------------------------------------------------------------ Étape 3 */
function StepBiens({ form, patch }: { form: SimFormState; patch: (p: Partial<SimFormState>) => void }) {
  function addBien(type: SimBien["type"]) {
    patch({ biens: [...form.biens, newBien(type)] });
  }
  function update(i: number, p: Partial<SimBien>) {
    patch({ biens: form.biens.map((b, j) => (j === i ? { ...b, ...p } : b)) });
  }
  function remove(i: number) {
    patch({ biens: form.biens.filter((_, j) => j !== i) });
  }

  const ICONS = { occupation: Home, locatif: KeyRound, vehicule: Car, creance: Receipt } as const;

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Ajoutez un ou plusieurs biens, chacun avec son statut précis. Les calculs s&apos;adaptent
        au type (indemnité d&apos;occupation, compte de gestion, argus − crédit, créances).
      </p>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(BIEN_TYPE_LABELS) as SimBien["type"][]).map((t) => {
          const Icon = ICONS[t];
          return (
            <Button key={t} variant="outline" size="sm" onClick={() => addBien(t)}>
              <Plus className="mr-1 h-3.5 w-3.5" /> {BIEN_TYPE_LABELS[t]}
            </Button>
          );
        })}
      </div>

      {form.biens.map((b, i) => {
        const Icon = ICONS[b.type];
        return (
          <Card key={i}>
            <CardHeader className="flex-row items-center gap-2 pb-1">
              <Icon className="h-4 w-4 text-primary" />
              <CardTitle className="text-sm">{BIEN_TYPE_LABELS[b.type]}</CardTitle>
              <Button variant="ghost" size="icon" className="ml-auto h-7 w-7" onClick={() => remove(i)}
                aria-label="Retirer ce bien">
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="space-y-1">
                <Label className="text-xs">Description</Label>
                <Input className="h-9 text-xs" placeholder="ex : résidence principale, studio locatif…"
                  value={b.description} onChange={(e) => update(i, { description: e.target.value })} />
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1"><Label className="text-xs">Valeur (€)</Label>
                  <Input type="number" min={0} value={b.valeur || ""} onChange={(e) => update(i, { valeur: Math.max(0, Number(e.target.value)) })} /></div>
                <div className="space-y-1"><Label className="text-xs">Crédit restant dû (€)</Label>
                  <Input type="number" min={0} value={b.credit || ""} onChange={(e) => update(i, { credit: Math.max(0, Number(e.target.value)) })} /></div>
                <div className="space-y-1"><Label className="text-xs">Quote-part occupant (%)</Label>
                  <Input type="number" min={0} max={100} value={b.quote_part_occupant} onChange={(e) => update(i, { quote_part_occupant: Number(e.target.value) })} /></div>
              </div>
              {b.type === "occupation" && (
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="space-y-1"><Label className="text-xs">Valeur locative mensuelle (€)</Label>
                    <Input type="number" min={0} value={b.valeur_locative || ""} onChange={(e) => update(i, { valeur_locative: Math.max(0, Number(e.target.value)) })} /></div>
                  <div className="space-y-1"><Label className="text-xs">Mois d&apos;occupation</Label>
                    <Input type="number" min={0} value={b.mois_occupation || ""} onChange={(e) => update(i, { mois_occupation: Math.max(0, Number(e.target.value)) })} /></div>
                  <div className="space-y-1"><Label className="text-xs">Occupant</Label>
                    <Select className="h-9 text-xs" value={b.occupant} onChange={(e) => update(i, { occupant: e.target.value as "A" | "B" })}>
                      <option value="A">Époux A</option><option value="B">Époux B</option>
                    </Select></div>
                </div>
              )}
              {b.type === "locatif" && (
                <div className="grid gap-3 sm:grid-cols-4">
                  <div className="space-y-1"><Label className="text-xs">Loyers/mois (€)</Label>
                    <Input type="number" min={0} value={b.loyers || ""} onChange={(e) => update(i, { loyers: Math.max(0, Number(e.target.value)) })} /></div>
                  <div className="space-y-1"><Label className="text-xs">Charges/mois (€)</Label>
                    <Input type="number" min={0} value={b.charges || ""} onChange={(e) => update(i, { charges: Math.max(0, Number(e.target.value)) })} /></div>
                  <div className="space-y-1"><Label className="text-xs">Mois de gestion</Label>
                    <Input type="number" min={0} value={b.mois_gestion || ""} onChange={(e) => update(i, { mois_gestion: Math.max(0, Number(e.target.value)) })} /></div>
                  <div className="space-y-1"><Label className="text-xs">Gestionnaire</Label>
                    <Select className="h-9 text-xs" value={b.gestionnaire} onChange={(e) => update(i, { gestionnaire: e.target.value as "A" | "B" })}>
                      <option value="A">Époux A</option><option value="B">Époux B</option>
                    </Select></div>
                </div>
              )}
              {b.type === "vehicule" && (
                <div className="space-y-1"><Label className="text-xs">Jouissance pendant la procédure</Label>
                  <Select className="h-9 text-xs" value={b.jouissance} onChange={(e) => update(i, { jouissance: e.target.value as "A" | "B" })}>
                    <option value="A">Époux A</option><option value="B">Époux B</option>
                  </Select></div>
              )}
              {b.type === "creance" && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1"><Label className="text-xs">Montant (€)</Label>
                    <Input type="number" min={0} value={b.montant || ""} onChange={(e) => update(i, { montant: Math.max(0, Number(e.target.value)) })} /></div>
                  <div className="space-y-1"><Label className="text-xs">Créancier</Label>
                    <Select className="h-9 text-xs" value={b.debiteur} onChange={(e) => update(i, { debiteur: e.target.value as "A" | "B" })}>
                      <option value="A">Époux A</option><option value="B">Époux B</option>
                    </Select></div>
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
      {form.biens.length === 0 && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          Aucun bien ajouté — ajoutez ceux qui vous concernent.
        </p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------ Étape 4 */
function StepDemandes({ form, patch }: { form: SimFormState; patch: (p: Partial<SimFormState>) => void }) {
  function toggle(key: keyof SimFormState["demandes"]) {
    patch({ demandes: { ...form.demandes, [key]: !form.demandes[key] } });
  }
  const D = form.demandes;
  const items: { key: keyof SimFormState["demandes"]; label: string; hint: string }[] = [
    { key: "pc", label: "Prestation compensatoire", hint: "Art. 270 — pour les mariés uniquement" },
    { key: "pension", label: "Pension alimentaire (CEE)", hint: "Contribution à l'entretien et l'éducation des enfants" },
    { key: "nomUsage", label: "Conservation du nom d'usage", hint: "Art. 264 — rejetée sans accord ni intérêt avéré" },
    { key: "di", label: "Dommages-intérêts", hint: "Art. 266 ou 1240 — préjudice exceptionnel à prouver" },
    { key: "faute", label: "Divorce pour faute", hint: "Art. 242 — violation grave des devoirs" },
    { key: "art700", label: "Remboursement frais d'avocat (art. 700 CPC)", hint: "Souvent accordé partiellement" },
  ];
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Cochez ce que vous envisagez de demander — ou ce que l&apos;autre partie réclame. Le
        diagnostic affichera le taux d&apos;acceptation réel observé dans la base.
      </p>
      {items.map((it) => (
        <button
          key={it.key}
          type="button"
          onClick={() => toggle(it.key)}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg border px-4 py-3 text-left transition-colors",
            D[it.key] ? "border-primary bg-primary/5" : "bg-card hover:bg-secondary",
          )}
        >
          <span className={cn(
            "flex h-5 w-5 shrink-0 items-center justify-center rounded border text-[10px]",
            D[it.key] ? "border-primary bg-primary text-primary-foreground" : "border-input",
          )}>
            {D[it.key] ? "✓" : ""}
          </span>
          <span className="flex-1">
            <span className="block text-sm font-medium">{it.label}</span>
            <span className="block text-xs text-muted-foreground">{it.hint}</span>
          </span>
        </button>
      ))}
      {D.pc && (
        <div className="space-y-1.5">
          <Label>Montant de PC envisagé (€)</Label>
          <Input type="number" min={0} value={D.pcMontant || ""}
            onChange={(e) => patch({ demandes: { ...D, pcMontant: Math.max(0, Number(e.target.value)) } })} />
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------ Étape 5 */
function StepDiagnostic({
  report, form, onRestart,
}: {
  report: SimDiagnostic;
  form: SimFormState;
  onRestart: () => void;
}) {
  const { tier } = useEntitlements();
  const pc = report.pc as { fourchette?: { min: number; mediane: number; max: number }; echantillon?: number } | null;
  const pension = report.pension as {
    bareme_total_mensuel: number; bareme_par_enfant: number;
    pension_mediane_globale: number | null;
  } | null;
  const bilan = report.bilan as { biens: Record<string, unknown>[]; indemnites_occupation_total: number; solde_gestion_total: number; creances_total: number };

  function dossier(): DossierInput {
    return {
      titre: "Dossier préparatoire Avocat / Notaire — Simulation multi-situations",
      situation: [
        { label: "Juridiction compétente", value: form.juridiction },
        { label: "Statut", value: STATUT_LABELS[form.statut] },
        { label: "Dates clés", value: `Mariage/PACS ${form.date_mariage} · Séparation ${form.date_separation} · Assignation ${form.date_assignation}` },
        { label: "Enfants", value: `${form.enfants} — garde : ${MODE_GARDE_LABELS[form.mode_garde]}` },
        { label: "Revenus mensuels (avec prestations)", value: `A : ${formatEur(report.ressources.a_total as number)} · B : ${formatEur(report.ressources.b_total as number)}` },
      ],
      demandes: [
        ...(pc
          ? [{ label: "Prestation compensatoire (médiane)", value: formatEur((pc.fourchette as { mediane: number }).mediane) }]
          : []),
        ...(pension
          ? [{ label: "Pension alimentaire (barème indicatif)", value: `${formatEur(pension.bareme_total_mensuel)}/mois pour ${form.enfants} enfant(s)` }]
          : []),
        { label: "Indemnités d'occupation cumulées", value: formatEur(bilan.indemnites_occupation_total) },
        { label: "Solde de gestion des biens locatifs", value: formatEur(bilan.solde_gestion_total) },
      ],
      references: (bilan.biens as { type: string; detail: string }[]).map((b) => ({
        juridiction: BIEN_TYPE_LABELS[b.type as SimBien["type"]] ?? b.type,
        date: "", rg: null, resume: b.detail,
      })),
      pieces: [
        "Ordonnance de non-conciliation et assignation",
        "Avis d'imposition et bulletins de salaire des deux époux",
        "Titres de propriété, tableaux d'amortissement du crédit",
        "Factures et relevés bancaires des travaux et créances",
        "Justificatifs des prestations sociales perçues",
      ],
      notes: [...report.notes, "Diagnostic statistique indicatif : ne remplace pas l'analyse d'un professionnel du droit."],
    };
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Diagnostic complet « Mon Cas »</h2>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => exportDossier(dossier(), "doc")}>
            <FileText className="mr-1.5 h-4 w-4" /> Dossier (Word)
          </Button>
          <Button variant="outline" size="sm" onClick={() => exportDossier(dossier(), "md")}>
            <FileDown className="mr-1.5 h-4 w-4" /> Markdown
          </Button>
          <Button variant="outline" size="sm" onClick={() => exportDossier(dossier(), "print")}>
            <Printer className="mr-1.5 h-4 w-4" /> PDF
          </Button>
        </div>
      </div>

      <Badge variant={report.source === "live" ? "success" : "warning"}>
        Source : {report.source === "live" ? "API en direct" : "Snapshot Open Data"}
      </Badge>

      {/* Bloc 1 — PC & pension */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">1. Prestation compensatoire &amp; pension alimentaire</CardTitle>
          {tier === "free" && (
            <PaywallHint text="Les fourchettes chiffrées sont floutées — débloquez le Diagnostic Complet" />
          )}
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
            <div className="rounded-lg bg-secondary p-2">
              <div className="text-[10px] text-muted-foreground">Revenus A</div>
              <div className="font-bold tabular-nums">{formatEur(report.ressources.a_total as number)}</div>
            </div>
            <div className="rounded-lg bg-secondary p-2">
              <div className="text-[10px] text-muted-foreground">Revenus B</div>
              <div className="font-bold tabular-nums">{formatEur(report.ressources.b_total as number)}</div>
            </div>
            <div className="rounded-lg bg-secondary p-2">
              <div className="text-[10px] text-muted-foreground">Écart mensuel</div>
              <div className="font-bold tabular-nums">{formatEur(report.ressources.ecart as number)}</div>
            </div>
            <div className="rounded-lg bg-secondary p-2">
              <div className="text-[10px] text-muted-foreground">Vie commune</div>
              <div className="font-bold tabular-nums">{String(report.chronologie.duree_vie_commune_mariage_annees)} ans</div>
            </div>
          </div>
          {pc && (
            <p>
              <b>PC (médiane observée)</b> : {formatEur((pc.fourchette as { mediane: number }).mediane)}{" "}
              (min {formatEur((pc.fourchette as { min: number }).min)} / max{" "}
              {formatEur((pc.fourchette as { max: number }).max)}) — {String(pc.echantillon)} décisions
              comparables.
            </p>
          )}
          {pension && (
            <p>
              <b>Pension alimentaire (barème indicatif)</b> :{" "}
              {formatEur(pension.bareme_total_mensuel)}/mois pour {form.enfants} enfant(s) —{" "}
              {formatEur(pension.bareme_par_enfant)}/enfant. Médiane de la base :{" "}
              {formatEur(pension.pension_mediane_globale)}. Frais exceptionnels partagés par moitié.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Bloc 2 — Bilan patrimonial */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">2. Bilan patrimonial &amp; compte de gestion</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(bilan.biens as Record<string, unknown>[]).length === 0 && (
            <p className="text-muted-foreground">Aucun bien déclaré à l&apos;étape 3.</p>
          )}
          {(bilan.biens as Record<string, unknown>[]).map((b, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-xs">
              <Badge variant="outline">{String(b.type)}</Badge>
              <span className="font-semibold">{String(b.description)}</span>
              <span className="text-muted-foreground">{String(b.detail)}</span>
              <span className="ml-auto font-bold tabular-nums">{formatEur(b.montant_net as number)}</span>
              <Badge variant="secondary">{String(b.beneficiaire)}</Badge>
            </div>
          ))}
          <div className="flex flex-wrap gap-3 pt-1 text-xs">
            <span>Indemnités d&apos;occupation : <b>{formatEur(bilan.indemnites_occupation_total)}</b></span>
            <span>Solde de gestion : <b>{formatEur(bilan.solde_gestion_total)}</b></span>
            <span>Créances : <b>{formatEur(bilan.creances_total)}</b></span>
          </div>
        </CardContent>
      </Card>

      {/* Bloc 3 — Radar des demandes annexes */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">3. Radar de probabilité des demandes annexes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {report.radar.map((r) => (
            <div key={r.demande} className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2">
              <span className="font-medium">{r.demande}</span>
              <Badge variant={r.taux_accords_pct != null && r.taux_accords_pct >= 50 ? "success" : "destructive"}>
                {r.taux_accords_pct != null ? formatPct(r.taux_accords_pct) : "—"} d&apos;accords
              </Badge>
              {r.montant_moyen != null && (
                <Badge variant="secondary">moy. {formatEur(r.montant_moyen)}</Badge>
              )}
              <span className="w-full text-xs text-muted-foreground">{r.note}</span>
            </div>
          ))}
          <p className="pt-1 text-xs text-muted-foreground">
            Exemple : les demandes d&apos;art. 266 / 1240 et de conservation du nom d&apos;usage sans
            accord sont rejetées dans plus de 80 % des jugements en l&apos;absence de preuve d&apos;un
            préjudice exceptionnel ou d&apos;un intérêt professionnel avéré.
          </p>
        </CardContent>
      </Card>

      {/* Bloc 4 — notes */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">4. Notes méthodologiques</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {report.notes.map((n, i) => <li key={i}>— {n}</li>)}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
