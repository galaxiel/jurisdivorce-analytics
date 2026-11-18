"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PCDistribution } from "@/lib/types";

/* Distribution des prestations compensatoires selon la durée du mariage. */
export function PCDistributionChart({ data }: { data: PCDistribution[] }) {
  const rows = data.map((d) => ({
    name: d.bucket,
    "Capital moyen": d.capital_moyen ?? 0,
    "Capital médian": d.capital_median ?? 0,
    nb: d.nb_decisions,
  }));

  return (
    <ResponsiveContainer width="100%" height={330}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)} k€`} />
        <Tooltip
          formatter={(value: any, name: any) => [`${Number(value).toLocaleString("fr-FR")} €`, String(name)]}
          labelFormatter={(label: any, payload: any) => `Durée ${label} (${payload?.[0]?.payload?.nb ?? 0} décisions)`}
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="Capital moyen" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Capital médian" fill="hsl(var(--accent))" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
