"use client";

import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { PROOF_OPTIONS, type BoussoleFormState } from "@/lib/types";

/* Étape 3 — Travaux & Financement */
export function Step3Travaux({
  form,
  setForm,
}: {
  form: BoussoleFormState;
  setForm: (patch: Partial<BoussoleFormState>) => void;
}) {
  const CREDIT: { value: BoussoleFormState["paye_credit"]; label: string }[] = [
    { value: "MOI", label: "Moi" },
    { value: "CONJOINT", label: "Mon conjoint" },
    { value: "COMMUN", label: "Compte commun" },
    { value: "NA", label: "Pas de crédit" },
  ];
  const TRAVAUX: { value: BoussoleFormState["travaux"]; label: string }[] = [
    { value: "MOI", label: "Moi" },
    { value: "CONJOINT", label: "Mon conjoint" },
    { value: "NA", label: "Aucun travaux" },
  ];

  function togglePreuve(value: string) {
    const next = form.preuves.includes(value)
      ? form.preuves.filter((p) => p !== value)
      : [...form.preuves, value];
    setForm({ preuves: next });
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>Qui a payé le crédit immobilier ?</Label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {CREDIT.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setForm({ paye_credit: o.value })}
              className={cn(
                "rounded-md border px-3 py-2.5 text-sm font-medium transition-colors",
                form.paye_credit === o.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "bg-card text-muted-foreground hover:bg-secondary",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label>Qui a financé les travaux sur le bien ?</Label>
        <div className="grid grid-cols-3 gap-2">
          {TRAVAUX.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setForm({ travaux: o.value })}
              className={cn(
                "rounded-md border px-3 py-2.5 text-sm font-medium transition-colors",
                form.travaux === o.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "bg-card text-muted-foreground hover:bg-secondary",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label>Quels justificatifs pouvez-vous produire ? (plusieurs choix possibles)</Label>
        <div className="grid gap-2 sm:grid-cols-2">
          {PROOF_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => togglePreuve(o.value)}
              className={cn(
                "flex items-center gap-2 rounded-md border px-3 py-2.5 text-left text-sm font-medium transition-colors",
                form.preuves.includes(o.value)
                  ? "border-success bg-success/10 text-success"
                  : "bg-card text-muted-foreground hover:bg-secondary",
              )}
            >
              <span
                className={cn(
                  "flex h-4 w-4 items-center justify-center rounded border",
                  form.preuves.includes(o.value) ? "border-success bg-success text-success-foreground" : "border-input",
                )}
              >
                {form.preuves.includes(o.value) ? "✓" : ""}
              </span>
              {o.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Les factures nominatives au nom de l&apos;époux demandeur sont, de loin, la preuve la plus
          souvent retenue par les tribunaux.
        </p>
      </div>
    </div>
  );
}
