"use client";

import { ChevronRight, Home } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { NATURE_FR, REGIME_LABELS, type DecisionListItem } from "@/lib/types";
import { formatEur, formatDate } from "@/lib/utils";

/* Carte de décision ultra-lisible : badges financiers d'un coup d'œil (Module 3 v2). */
export function DecisionCard({
  item,
  onOpen,
}: {
  item: DecisionListItem;
  onOpen: (id: string) => void;
}) {
  return (
    <Card
      className="card-hover cursor-pointer"
      onClick={() => onOpen(item.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onOpen(item.id)}
    >
      <CardContent className="space-y-2.5 p-4">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <span className="text-sm font-semibold">{item.juridiction}</span>
          <span className="text-xs text-muted-foreground">
            {formatDate(item.date_decision)} · {item.numero_rg}
          </span>
          <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
        </div>

        <div className="flex flex-wrap gap-1.5">
          {item.type_procedure && <Badge variant="secondary">{item.type_procedure}</Badge>}
          <Badge variant="outline">{REGIME_LABELS[item.regime_matrimonial ?? ""] ?? "Régime inconnu"}</Badge>
          <Badge variant="outline">{item.duree_mariage_annees ?? "—"} ans</Badge>
          {item.occupation_montant_total != null && (
            <Badge variant={item.occupation_accordee ? "success" : "destructive"}>
              <Home className="mr-1 h-3 w-3" />
              {item.occupation_accordee
                ? `IO ${formatEur(item.occupation_montant_total)}${item.occupation_abattement_pct != null ? ` · abattement ${Math.round(item.occupation_abattement_pct)} %` : ""}`
                : "IO rejetée"}
            </Badge>
          )}
          {item.pc_accordee === true && <Badge variant="success">PC {formatEur(item.pc_montant_capital)}</Badge>}
          {item.total_demande != null && item.total_demande > 0 && (
            <Badge variant={item.total_accorde ? "default" : "destructive"}>
              Demande {formatEur(item.total_demande)} → Obtenu {formatEur(item.total_accorde)}
            </Badge>
          )}
        </div>

        {item.resume_3_lignes && (
          <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">{item.resume_3_lignes}</p>
        )}
      </CardContent>
    </Card>
  );
}
