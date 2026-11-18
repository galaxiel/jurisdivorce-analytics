"use client";

import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { REGIME_LABELS, type DecisionListItem } from "@/lib/types";
import { formatEur, formatDate } from "@/lib/utils";

export function DecisionTable({
  items,
  loading,
  onOpen,
}: {
  items: DecisionListItem[];
  loading: boolean;
  onOpen: (id: string) => void;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>Juridiction</TableHead>
          <TableHead>Régime</TableHead>
          <TableHead>Occupation</TableHead>
          <TableHead>PC</TableHead>
          <TableHead>Récompenses</TableHead>
          <TableHead aria-label="Ouvrir" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((d) => (
          <TableRow key={d.id} className="cursor-pointer" onClick={() => onOpen(d.id)}>
            <TableCell className="whitespace-nowrap text-sm">
              <div>{formatDate(d.date_decision)}</div>
              <div className="text-xs text-muted-foreground">{d.numero_rg}</div>
            </TableCell>
            <TableCell className="text-sm font-medium">{d.juridiction}</TableCell>
            <TableCell className="text-sm text-muted-foreground">
              {REGIME_LABELS[d.regime_matrimonial ?? ""] ?? "—"}
              <div className="text-xs">{d.duree_mariage_annees ?? "—"} ans de mariage</div>
            </TableCell>
            <TableCell>
              {d.occupation_accordee === true ? (
                <div>
                  <div className="text-sm font-medium">{formatEur(d.occupation_montant_total)}</div>
                  <Badge variant="success" className="mt-0.5">Accordée</Badge>
                </div>
              ) : d.occupation_accordee === false ? (
                <Badge variant="destructive">Rejetée</Badge>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell>
              {d.pc_accordee === true ? (
                <div>
                  <div className="text-sm font-medium">{formatEur(d.pc_montant_capital)}</div>
                  <Badge variant="success" className="mt-0.5">Accordée</Badge>
                </div>
              ) : d.pc_accordee === false ? (
                <Badge variant="destructive">Rejetée</Badge>
              ) : (
                <span className="text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell>
              <div className="text-sm">{d.nb_recompenses || "—"}</div>
              {d.taux_reussite_recompenses !== null && (
                <Badge variant={d.taux_reussite_recompenses >= 60 ? "success" : d.taux_reussite_recompenses > 0 ? "secondary" : "destructive"} className="mt-0.5">
                  {Math.round(d.taux_reussite_recompenses)} % de succès
                </Badge>
              )}
            </TableCell>
            <TableCell>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </TableCell>
          </TableRow>
        ))}
        {items.length === 0 && (
          <TableRow>
            <TableCell colSpan={7} className="py-10 text-center text-muted-foreground">
              Aucune décision ne correspond à ces filtres.
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
}
