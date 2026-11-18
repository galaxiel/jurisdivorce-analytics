"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { BoussoleFormState } from "@/lib/types";

/* Étape 2 — Le Bien & L'Occupation */
export function Step2Bien({
  form,
  setForm,
}: {
  form: BoussoleFormState;
  setForm: (patch: Partial<BoussoleFormState>) => void;
}) {
  const OCCUPANTS: { value: "MOI" | "CONJOINT"; label: string }[] = [
    { value: "MOI", label: "Moi" },
    { value: "CONJOINT", label: "Mon conjoint" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="vl">Valeur locative mensuelle estimée (€)</Label>
          <Input
            id="vl"
            type="number"
            min={0}
            max={10000}
            value={form.valeur_locative_mensuelle}
            onChange={(e) => setForm({ valeur_locative_mensuelle: Math.max(0, Number(e.target.value)) })}
          />
          <p className="text-xs text-muted-foreground">Loyer que le bien pourrait rapporter (estimation d&apos;agence).</p>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="mois">Durée d&apos;occupation exclusive (mois)</Label>
          <Input
            id="mois"
            type="number"
            min={0}
            max={240}
            value={form.mois_occupation}
            onChange={(e) => setForm({ mois_occupation: Math.max(0, Number(e.target.value)) })}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Qui a occupé seul le bien depuis la séparation ?</Label>
        <div className="flex gap-2">
          {OCCUPANTS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => setForm({ occupant: o.value })}
              className={cn(
                "flex-1 rounded-md border px-3 py-2.5 text-sm font-medium transition-colors",
                form.occupant === o.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "bg-card text-muted-foreground hover:bg-secondary",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
