"use client";

import * as React from "react";
import { Download, RotateCcw, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  NATURE_FR,
  REGIME_LABELS,
  STATUT_LABELS,
  TYPE_PROCEDURE_LABELS,
  type DecisionFilters,
  type Facets,
} from "@/lib/types";

/* Barre de filtres croisés universelle — partagée par le Cockpit et l'Explorateur. */
export function FilterBar({
  filters,
  onChange,
  facets,
  onExport,
  compact = false,
}: {
  filters: DecisionFilters;
  onChange: (f: DecisionFilters) => void;
  facets?: Facets | null;
  onExport?: (format: "csv" | "json") => void;
  compact?: boolean;
}) {
  const [q, setQ] = React.useState(filters.q ?? "");

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

  const juridictions = facets?.juridictions?.length ? facets.juridictions : [];
  const annees = facets?.annees?.length ? facets.annees : [];
  const natures = facets?.natures?.length ? facets.natures : Object.keys(NATURE_FR);

  return (
    <div className="no-print sticky top-14 z-30 -mx-1 rounded-xl border bg-card/95 px-3 py-3 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/85">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <SlidersHorizontal className="h-3.5 w-3.5" /> Filtres croisés
        {onExport && (
          <span className="ml-auto flex gap-1.5">
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={() => onExport("csv")}>
              <Download className="mr-1 h-3 w-3" /> CSV
            </Button>
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={() => onExport("json")}>
              <Download className="mr-1 h-3 w-3" /> JSON
            </Button>
          </span>
        )}
      </div>

      <div className={`grid gap-2.5 ${compact ? "sm:grid-cols-3 lg:grid-cols-6" : "sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8"}`}>
        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Cour d&apos;appel</Label>
          <Select className="h-9 text-xs" value={filters.juridiction ?? ""} onChange={(e) => set({ juridiction: e.target.value || undefined })}>
            <option value="">Toutes</option>
            {juridictions.map((j) => <option key={j} value={j}>{j}</option>)}
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Année</Label>
          <Select className="h-9 text-xs" value={filters.annee ?? ""} onChange={(e) => set({ annee: e.target.value || undefined })}>
            <option value="">Toutes</option>
            {annees.map((a) => <option key={a} value={a}>{a}</option>)}
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Régime</Label>
          <Select className="h-9 text-xs" value={filters.regime ?? ""} onChange={(e) => set({ regime: e.target.value || undefined })}>
            <option value="">Tous</option>
            {Object.entries(REGIME_LABELS).filter(([k]) => k !== "INCONNU").map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Contentieux</Label>
          <Select className="h-9 text-xs" value={filters.type_procedure ?? ""} onChange={(e) => set({ type_procedure: e.target.value || undefined })}>
            <option value="">Tous</option>
            {Object.keys(TYPE_PROCEDURE_LABELS).map((k) => <option key={k} value={k}>{TYPE_PROCEDURE_LABELS[k]}</option>)}
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Nature réclamation</Label>
          <Select className="h-9 text-xs" value={filters.nature_reclamation ?? ""} onChange={(e) => set({ nature_reclamation: e.target.value || undefined })}>
            <option value="">Toutes</option>
            {natures.map((k) => <option key={k} value={k}>{NATURE_FR[k] ?? k}</option>)}
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Issue</Label>
          <Select className="h-9 text-xs" value={filters.issue ?? ""} onChange={(e) => set({ issue: e.target.value || undefined })}>
            <option value="">Toutes</option>
            {Object.entries(STATUT_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Immobilier</Label>
          <Select className="h-9 text-xs" value={filters.has_immo ?? ""} onChange={(e) => set({ has_immo: e.target.value || undefined })}>
            <option value="">Tous</option>
            <option value="true">Bien immobilier</option>
            <option value="false">Sans immobilier</option>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Montant litige (€)</Label>
          <div className="flex gap-1">
            <Input className="h-9 text-xs" type="number" placeholder="min" value={filters.montant_min ?? ""} onChange={(e) => set({ montant_min: e.target.value || undefined })} />
            <Input className="h-9 text-xs" type="number" placeholder="max" value={filters.montant_max ?? ""} onChange={(e) => set({ montant_max: e.target.value || undefined })} />
          </div>
        </div>
      </div>

      <div className="mt-2.5 flex items-center gap-2">
        <Input className="h-9 max-w-sm text-xs" placeholder="Recherche plein texte (motifs, RG, cour…)" value={q} onChange={(e) => setQ(e.target.value)} />
        <Button variant="ghost" size="sm" className="h-9 text-xs" onClick={() => { setQ(""); onChange({}); }}>
          <RotateCcw className="mr-1 h-3 w-3" /> Réinitialiser
        </Button>
      </div>
    </div>
  );
}
