"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { JURIDICTIONS, REGIME_LABELS, type BoussoleFormState } from "@/lib/types";

/* Étape 1 — Statut & Régime */
export function Step1Statut({
  form,
  setForm,
}: {
  form: BoussoleFormState;
  setForm: (patch: Partial<BoussoleFormState>) => void;
}) {
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <div className="space-y-1.5 sm:col-span-2">
        <Label htmlFor="juridiction">Juridiction (Cour d&apos;appel régionale)</Label>
        <Select
          id="juridiction"
          value={form.juridiction}
          onChange={(e) => setForm({ juridiction: e.target.value })}
        >
          {JURIDICTIONS.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="regime">Régime matrimonial</Label>
        <Select
          id="regime"
          value={form.regime_matrimonial}
          onChange={(e) => setForm({ regime_matrimonial: e.target.value })}
        >
          {Object.entries(REGIME_LABELS)
            .filter(([k]) => k !== "INCONNU")
            .map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="duree">Durée du mariage (années)</Label>
        <Input
          id="duree"
          type="number"
          min={0}
          max={70}
          value={form.duree_mariage_annees}
          onChange={(e) => setForm({ duree_mariage_annees: Math.max(0, Number(e.target.value)) })}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="enfants">Nombre d&apos;enfants</Label>
        <Input
          id="enfants"
          type="number"
          min={0}
          max={12}
          value={form.nombre_enfants}
          onChange={(e) => setForm({ nombre_enfants: Math.max(0, Number(e.target.value)) })}
        />
      </div>
    </div>
  );
}
