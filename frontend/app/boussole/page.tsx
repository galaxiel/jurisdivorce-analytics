"use client";

import { useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Step1Statut } from "@/components/boussole/step1-statut";
import { Step2Bien } from "@/components/boussole/step2-bien";
import { Step3Travaux } from "@/components/boussole/step3-travaux";
import { ResultPanel } from "@/components/boussole/result-panel";
import { postBoussole } from "@/lib/api";
import { JURIDICTIONS, type BoussoleFormState, type BoussoleReport } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEPS = ["Statut & Régime", "Le Bien & l'Occupation", "Travaux & Financement", "Rapport prédictif"];

const DEFAULT_FORM: BoussoleFormState = {
  juridiction: JURIDICTIONS[0],
  regime_matrimonial: "COMMUNAUTE_REDUITE_AUX_ACQUETS",
  duree_mariage_annees: 12,
  nombre_enfants: 1,
  valeur_locative_mensuelle: 800,
  occupant: "CONJOINT",
  mois_occupation: 12,
  paye_credit: "COMMUN",
  travaux: "NA",
  preuves: [],
};

export default function BoussolePage() {
  const [form, setForm] = useState<BoussoleFormState>(DEFAULT_FORM);
  const [step, setStep] = useState(1);
  const [report, setReport] = useState<BoussoleReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function patch(p: Partial<BoussoleFormState>) {
    setForm((f) => ({ ...f, ...p }));
  }

  async function submit() {
    setLoading(true);
    setError(null);
    try {
      const res = await postBoussole({ ...form });
      setReport(res);
      setStep(4);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function next() {
    if (step < 3) setStep(step + 1);
    else await submit();
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold">La Boussole — simulateur « Mon Cas »</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        4 étapes pour obtenir une estimation chiffrée fondée sur les décisions comparables en base.
      </p>

      {/* Progression */}
      <div className="mt-6 flex items-center gap-2">
        {STEPS.map((label, i) => {
          const n = i + 1;
          const done = step > n || (step === 4 && report !== null);
          const active = step === n;
          return (
            <div key={label} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="flex w-full items-center">
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-colors",
                    done
                      ? "border-success bg-success text-success-foreground"
                      : active
                        ? "border-primary bg-primary text-primary-foreground"
                        : "bg-card text-muted-foreground",
                  )}
                >
                  {done ? <Check className="h-4 w-4" /> : n}
                </span>
                {n < STEPS.length && <span className={cn("h-0.5 flex-1", done ? "bg-success" : "bg-border")} />}
              </div>
              <span className={cn("text-center text-[11px] leading-tight", active ? "font-semibold" : "text-muted-foreground")}>
                {label}
              </span>
            </div>
          );
        })}
      </div>

      <Card className="mt-6">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{STEPS[step - 1]}</CardTitle>
        </CardHeader>
        <CardContent>
          {step === 1 && <Step1Statut form={form} setForm={patch} />}
          {step === 2 && <Step2Bien form={form} setForm={patch} />}
          {step === 3 && <Step3Travaux form={form} setForm={patch} />}
          {step === 4 && report && <ResultPanel report={report} onRestart={() => { setReport(null); setStep(1); setForm(DEFAULT_FORM); }} />}

          {error && <p className="mt-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}

          {step < 4 && (
            <div className="mt-6 flex justify-between">
              <Button variant="ghost" onClick={() => setStep(Math.max(1, step - 1))} disabled={step === 1}>
                Retour
              </Button>
              <Button onClick={next} disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                {step === 3 ? "Calculer mon rapport" : "Continuer"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
