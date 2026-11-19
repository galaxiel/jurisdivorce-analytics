"use client";

import * as React from "react";
import { ChevronDown, Download, RotateCcw, SlidersHorizontal } from "lucide-react";
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
import { cn } from "@/lib/utils";

/* Barre de filtres croisés universelle.
   Desktop (lg+) : sticky, tous les champs visibles.
   Mobile : repliée par défaut (bouton + compteur de filtres actifs), le panneau ouvert
   n'est PAS sticky — il défile normalement avec la page (plus rien ne masque l'écran). */
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
  const [open, setOpen] = React.useState(false);

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

  const activeCount = [
    filters.juridiction, filters.annee, filters.regime, filters.type_procedure,
    filters.nature_reclamation, filters.issue, filters.has_immo,
    filters.montant_min, filters.montant_max, filters.q,
  ].filter(Boolean).length;

  const hasFilters = activeCount > 0;

  return (
    <div className="no-print relative z-30 rounded-xl border bg-card/95 px-3 py-3 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-card/85 lg:sticky lg:top-14">
      {/* Ligne d'en-tête : bouton d'ouverture (mobile) + exports */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground lg:pointer-events-none"
          aria-expanded={open}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" /> Filtres croisés
          {hasFilters && (
            <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary">
              {activeCount}
            </span>
          )}
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform lg:hidden", open && "rotate-180")} />
        </button>
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

      {/* Panneau : toujours ouvert sur desktop ; repliable sur mobile */}
      <div
        className={cn(
          "mt-2 grid gap-2.5 lg:grid",
          compact ? "sm:grid-cols-3 lg:grid-cols-6" : "sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8",
          open ? "grid grid-cols-1 sm:grid-cols-2 max-h-[62vh] overflow-y-auto pr-1" : "hidden",
        )}
      >
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
          <Label className="text-[11px] text-muted-foreground">Régime matrimonial</Label>
          <Select className="h-9 text-xs" value={filters.regime ?? ""} onChange={(e) => set({ regime: e.target.value || undefined })}>
            <option value="">Tous</option>
            {Object.entries(REGIME_LABELS).filter(([k]) => k !== "INCONNU").map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px] text-muted-foreground">Contentieux</Label>
          <Select className="h-9 text-xs" value={filters.type_procedure ?? ""} onChange={(e) => set({ type_procedure: e.target.value || undefined })}>
            <option value="">Tous</option>
            {Object.keys(TYPE_PROCEDURE_LABELS).map((k) => (
              <option key={k} value={k}>{TYPE_PROCEDURE_LABELS[k]}</option>
            ))}
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
            {Object.entries(STATUT_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
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

      {/* Recherche + reset : même logique de visibilité que le panneau */}
      <div className={cn("items-center gap-2 lg:flex", open ? "mt-2.5 flex" : "hidden")}>
        <Input className="h-9 max-w-sm text-xs" placeholder="Recherche plein texte (motifs, RG, cour…)" value={q} onChange={(e) => setQ(e.target.value)} />
        <Button variant="ghost" size="sm" className="h-9 text-xs" onClick={() => { setQ(""); onChange({}); }}>
          <RotateCcw className="mr-1 h-3 w-3" /> Réinitialiser
        </Button>
      </div>
    </div>
  );
}
