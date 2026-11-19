"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { NATURE_FR, type NatureSucces } from "@/lib/types";

/* Taux de succès par nature de réclamation : réclamé vs obtenu (k€) + taux (courbe). */
export function NatureSuccessChart({ data }: { data: NatureSucces[] }) {
  const rows = data.map((d) => ({
    name: NATURE_FR[d.nature] ?? d.nature,
    "Réclamé (k€)": d.montant_moyen_demande != null ? Math.round(d.montant_moyen_demande / 1000) : 0,
    "Obtenu (k€)": d.montant_moyen_accorde != null ? Math.round(d.montant_moyen_accorde / 1000) : 0,
    taux: d.taux_succes_pct,
    nb: d.nb_reclamations,
  }));

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 60, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
        <XAxis dataKey="name" angle={-30} textAnchor="end" height={70} tick={{ fontSize: 10 }} interval={0} />
        <YAxis yAxisId="eur" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} k€`} />
        <YAxis yAxisId="pct" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} %`} />
        <Tooltip
          formatter={(value: any, name: any) =>
            name === "taux" ? [`${value} %`, "Taux de succès"] : [value, String(name)]
          }
          labelFormatter={(label: any, payload: any) => `${label} (${payload?.[0]?.payload?.nb ?? 0} réclamations)`}
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600, marginBottom: 4 }}
          itemStyle={{ color: "hsl(var(--foreground))" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar yAxisId="eur" dataKey="Réclamé (k€)" fill="hsl(var(--muted-foreground))" radius={[4, 4, 0, 0]} barSize={26} />
        <Bar yAxisId="eur" dataKey="Obtenu (k€)" fill="hsl(var(--success))" radius={[4, 4, 0, 0]} barSize={26} />
        <Line yAxisId="pct" dataKey="taux" stroke="hsl(var(--accent))" strokeWidth={2} dot={{ r: 3 }} name="taux" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
