"use client";

import Link from "next/link";
import { ShieldAlert, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePieges } from "@/lib/api";
import { formatEur, formatPct } from "@/lib/utils";

/* Vue 7 — Radar des « Pièges & Motifs de Rejet » : analyse des échecs devant les juges. */
export default function PiegesPage() {
  const { data, loading, error } = usePieges();
  const totalRejets = data?.reduce((acc, p) => acc + p.nb_cas, 0) ?? 0;

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-8 sm:px-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <ShieldAlert className="h-6 w-6 text-destructive" /> Radar des pièges &amp; motifs de rejet
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Les {data?.length ?? 0} raisons principales pour lesquelles les demandes financières sont
          rejetées — {totalRejets.toLocaleString("fr-FR")} réclamations rejetées analysées.
        </p>
      </div>

      {error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          API indisponible : {error}.
        </p>
      )}

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
      )}

      <div className="space-y-3">
        {(data ?? []).map((p, i) => (
          <Card key={p.motif}>
            <CardContent className="space-y-3 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="shrink-0">#{i + 1}</Badge>
                <span className="text-sm font-semibold">{p.motif}</span>
                <Badge variant={p.pct_rejets >= 15 ? "destructive" : p.pct_rejets >= 8 ? "warning" : "secondary"}>
                  {formatPct(p.pct_rejets)} des rejets
                </Badge>
                <Badge variant="outline">{p.nb_cas} cas</Badge>
                <Badge variant="destructive">
                  Montant moyen perdu : {formatEur(p.montant_moyen_perdu)}
                </Badge>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full bg-destructive" style={{ width: `${Math.min(100, p.pct_rejets * 3)}%` }} />
              </div>
              {p.exemples.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Arrêts illustratifs</p>
                  {p.exemples.map((ex) => (
                    <div key={ex.id} className="rounded-md border bg-secondary/40 p-2.5 text-xs">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold">{ex.juridiction}</span>
                        <span className="text-muted-foreground">{ex.date_decision} · {ex.numero_rg}</span>
                        {ex.montant_perdu != null && (
                          <Badge variant="destructive" className="ml-auto">
                            <TriangleAlert className="mr-1 h-3 w-3" /> {formatEur(ex.montant_perdu)} réclamés
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 text-muted-foreground">{ex.resume}</p>
                      <Button asChild variant="link" size="sm" className="h-auto p-0 text-xs">
                        <Link href={`/decisions?id=${ex.id}`}>Voir la fiche décisionnelle →</Link>
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
