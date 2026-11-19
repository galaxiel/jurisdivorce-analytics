"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatEur, formatPct } from "@/lib/utils";
import type { DemandesAnnexesStats, PensionStats } from "@/lib/types";

/* Onglet « Pension alimentaire, PC & demandes annexes » du Cockpit (V5). */
export function PensionTab({ pension, demandesAnnexes }: {
  pension: { data: PensionStats | null; loading: boolean; error: string | null };
  demandesAnnexes: { data: DemandesAnnexesStats | null; loading: boolean; error: string | null };
}) {
  const tooltipStyle = {
    background: "hsl(var(--card))",
    border: "1px solid hsl(var(--border))",
    borderRadius: 8,
    fontSize: 12,
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="lg:col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            Pension alimentaire par enfant — médiane par Cour d&apos;appel
          </CardTitle>
          <CardDescription>
            Époux débiteur de référence (barème indicatif Ministère de la Justice), hors garde alternée.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {pension.loading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={(pension.data?.par_cour ?? []).map((p) => ({
                  name: p.cour.replace("Cour d'appel ", ""),
                  pension: p.pension_mediane,
                  nb: p.nb,
                }))}
                margin={{ top: 8, right: 8, bottom: 60, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis dataKey="name" angle={-30} textAnchor="end" height={70} tick={{ fontSize: 10 }} interval={0} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} €`} />
                <Tooltip
                  formatter={(value: any, _name: any, item: any) => [
                    `${value} €`,
                    `Médiane (${item?.payload?.nb ?? 0} décisions)`,
                  ]}
                  contentStyle={tooltipStyle}
                  labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                  itemStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Bar dataKey="pension" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} barSize={30} />
              </BarChart>
            </ResponsiveContainer>
          )}
          {pension.data?.pension_mediane_globale != null && (
            <p className="mt-2 text-xs text-muted-foreground">
              Médiane nationale : {formatEur(pension.data.pension_mediane_globale)} / enfant / mois.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Pension par revenus du débiteur</CardTitle>
          <CardDescription>Médiane par tranche de revenus mensuels nets.</CardDescription>
        </CardHeader>
        <CardContent>
          {pension.loading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={(pension.data?.par_tranche_revenus ?? []).map((p) => ({
                  name: p.tranche,
                  pension: p.pension_mediane,
                  nb: p.nb,
                }))}
                margin={{ top: 8, right: 8, bottom: 8, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} €`} />
                <Tooltip
                  formatter={(value: any, _name: any, item: any) => [
                    `${value} €`,
                    `Médiane (${item?.payload?.nb ?? 0} décisions)`,
                  ]}
                  contentStyle={tooltipStyle}
                  labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                  itemStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Bar dataKey="pension" fill="hsl(var(--accent))" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Rejet de la PC selon l&apos;écart de revenus</CardTitle>
          <CardDescription>
            Prestations sociales incluses dans l&apos;appréciation globale des ressources.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {demandesAnnexes.loading ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={(demandesAnnexes.data?.pc_rejet_par_ecart ?? []).map((b) => ({
                  name: b.bucket,
                  rejet: b.pct_rejet,
                  nb: b.nb,
                }))}
                margin={{ top: 8, right: 8, bottom: 8, left: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} %`} />
                <Tooltip
                  formatter={(value: any, _name: any, item: any) => [
                    `${value} %`,
                    `${item?.payload?.nb ?? 0} demandes de PC`,
                  ]}
                  contentStyle={tooltipStyle}
                  labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                  itemStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Bar dataKey="rejet" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} barSize={44} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Demandes annexes — taux d&apos;échec</CardTitle>
          <CardDescription>Pour éviter les procédures coûteuses et vouées à l&apos;échec.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {(demandesAnnexes.data?.items ?? []).map((it) => (
            <div key={it.demande} className="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2">
              <span className="font-medium">{it.demande}</span>
              <Badge
                variant={
                  it.taux_accords_pct != null && it.taux_accords_pct >= 50
                    ? "success"
                    : it.taux_accords_pct != null && it.taux_accords_pct >= 20
                      ? "warning"
                      : "destructive"
                }
              >
                {formatPct(it.taux_accords_pct)} d&apos;accords
              </Badge>
              {it.montant_moyen != null && (
                <Badge variant="secondary">moy. {formatEur(it.montant_moyen)}</Badge>
              )}
              <span className="w-full text-xs text-muted-foreground">{it.note}</span>
            </div>
          ))}
          {pension.data?.modes_garde?.length ? (
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Modes de garde :
              </span>
              {pension.data.modes_garde.map((m) => (
                <Badge key={m.mode} variant="outline">{m.mode} · {m.nb}</Badge>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
