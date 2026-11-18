"use client";

import * as React from "react";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { JURIDICTIONS, REGIME_LABELS, STATUT_LABELS, type DecisionFilters } from "@/lib/types";

export function DecisionFiltersBar({
  filters,
  onChange,
  total,
}: {
  filters: DecisionFilters;
  onChange: (f: DecisionFilters) => void;
  total?: number;
}) {
  const [q, setQ] = React.useState(filters.q ?? "");

  // Debounce de la recherche texte : 400 ms
  React.useEffect(() => {
    const t = setTimeout(() => {
      if (q !== (filters.q ?? "")) onChange({ ...filters, q: q || undefined });
    }, 400);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  function set(patch: Partial<DecisionFilters>) {
    onChange({ ...filters, ...patch });
  }

  return (
    <div className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-2 lg:grid-cols-5">
      <div className="space-y-1.5">
        <Label>Cour d&apos;appel</Label>
        <Select value={filters.juridiction ?? ""} onChange={(e) => set({ juridiction: e.target.value || undefined })}>
          <option value="">Toutes</option>
          {JURIDICTIONS.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Régime matrimonial</Label>
        <Select value={filters.regime ?? ""} onChange={(e) => set({ regime: e.target.value || undefined })}>
          <option value="">Tous</option>
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
        <Label>Statut de la récompense</Label>
        <Select value={filters.statut_recompense ?? ""} onChange={(e) => set({ statut_recompense: e.target.value || undefined })}>
          <option value="">Tous</option>
          {Object.entries(STATUT_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Prestation compensatoire</Label>
        <Select value={filters.presence_pc ?? ""} onChange={(e) => set({ presence_pc: e.target.value || undefined })}>
          <option value="">Toutes</option>
          <option value="true">Demandée</option>
          <option value="false">Non demandée</option>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Recherche texte</Label>
        <div className="flex gap-2">
          <Input placeholder="motifs, RG, cour…" value={q} onChange={(e) => setQ(e.target.value)} />
          <Button
            variant="outline"
            size="icon"
            aria-label="Réinitialiser les filtres"
            onClick={() => {
              setQ("");
              onChange({});
            }}
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {total !== undefined && (
        <p className="text-xs text-muted-foreground lg:col-span-5">
          {total.toLocaleString("fr-FR")} décision(s) correspondante(s)
        </p>
      )}
    </div>
  );
}
