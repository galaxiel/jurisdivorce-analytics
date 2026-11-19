"use client";

import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TendancePoint } from "@/lib/types";

/* Analytics temporelles : PC médiane (k€) vs abattement médian et taux de succès (%). */
export function TendancesChart({ data }: { data: TendancePoint[] }) {
  const rows = data.map((d) => ({
    annee: String(d.annee),
    "PC médiane (k€)": d.pc_mediane != null ? Math.round(d.pc_mediane / 1000) : null,
    "Abattement médian (%)": d.abattement_median_pct,
    "Taux de succès (%)": d.taux_succes_pct,
    nb: d.nb_decisions,
  }));

  return (
    <ResponsiveContainer width="100%" height={330}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
        <XAxis dataKey="annee" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="eur" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} k€`} />
        <YAxis yAxisId="pct" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} %`} />
        <Tooltip
          formatter={(value: any, name: any) => [value ?? "—", String(name)]}
          labelFormatter={(label: any, payload: any) => `Année ${label} (${payload?.[0]?.payload?.nb ?? 0} décisions)`}
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600, marginBottom: 4 }}
          itemStyle={{ color: "hsl(var(--foreground))" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line yAxisId="eur" dataKey="PC médiane (k€)" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 2 }} />
        <Line yAxisId="pct" dataKey="Abattement médian (%)" stroke="hsl(var(--accent))" strokeWidth={2} dot={{ r: 2 }} />
        <Line yAxisId="pct" dataKey="Taux de succès (%)" stroke="hsl(var(--warning))" strokeWidth={2} dot={{ r: 2 }} strokeDasharray="4 3" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
