"use client";

import { CartesianGrid, Cell, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { PCCorrelationPoint } from "@/lib/types";

/* Corrélation durée du mariage / écart de revenus vs prestation compensatoire accordée.
   Chaque point est coloré selon le bucket d'écart de revenus mensuel. */
const BUCKETS = [
  { label: "Écart < 1 500 €/mois", test: (v: number) => v < 1500, fill: "hsl(var(--success))" },
  { label: "1 500 – 3 000 €", test: (v: number) => v < 3000, fill: "hsl(var(--primary))" },
  { label: "3 000 – 4 500 €", test: (v: number) => v < 4500, fill: "hsl(var(--accent))" },
  { label: "≥ 4 500 €", test: () => true, fill: "hsl(var(--destructive))" },
];

export function PCScatterChart({ data }: { data: PCCorrelationPoint[] }) {
  const series = BUCKETS.map((b) => ({
    ...b,
    points: data
      .filter((p) => p.duree_mariage_annees != null && p.capital_accorde != null)
      .filter((p) => b.test(p.ecart_revenus_mensuel ?? 0))
      .map((p) => ({
        duree: p.duree_mariage_annees,
        capital: Math.round((p.capital_accorde ?? 0) / 1000),
        ecart: p.ecart_revenus_mensuel ?? 0,
      })),
  }));

  return (
    <ResponsiveContainer width="100%" height={340}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis type="number" dataKey="duree" name="Durée du mariage" unit=" ans" tick={{ fontSize: 11 }} />
        <YAxis type="number" dataKey="capital" name="PC accordée" unit=" k€" tick={{ fontSize: 11 }} />
        <ZAxis range={[30, 30]} />
        <Tooltip
          formatter={(value: any, name: any) =>
            name === "Durée du mariage" ? [`${value} ans`, name] : name === "PC accordée" ? [`${value} k€`, name] : [value, name]
          }
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {series.map((s) => (
          <Scatter key={s.label} name={s.label} data={s.points} fill={s.fill} fillOpacity={0.55}>
            {s.points.map((p, i) => (
              <Cell key={i} fill={s.fill} fillOpacity={0.5} />
            ))}
          </Scatter>
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  );
}
