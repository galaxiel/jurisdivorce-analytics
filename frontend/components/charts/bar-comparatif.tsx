"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CourComparatif } from "@/lib/types";

/* Comparatif des Cours d'appel : indemnité moyenne (barres) + abattement moyen (courbe). */
export function BarComparatif({ data }: { data: CourComparatif[] }) {
  const rows = data.map((d) => ({
    name: d.juridiction.replace("Cour d'appel d'", "").replace("Cour d'appel de ", ""),
    indemnite: d.indemnite_moyenne_mensuelle ?? 0,
    abattement: d.abattement_moyen_pct ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={330}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
        <XAxis dataKey="name" angle={-35} textAnchor="end" height={70} tick={{ fontSize: 11 }} interval={0} />
        <YAxis yAxisId="eur" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} €`} />
        <YAxis yAxisId="pct" orientation="right" domain={[0, 50]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} %`} />
        <Tooltip
          formatter={(value: any, name: any) =>
            name === "indemnite" ? [`${value} €`, "Indemnité mensuelle moyenne"] : [`${value} %`, "Abattement moyen"]
          }
          labelFormatter={(label: any) => `Cour d'appel : ${label}`}
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
        />
        <Bar yAxisId="eur" dataKey="indemnite" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} name="indemnite" />
        <Line yAxisId="pct" dataKey="abattement" stroke="hsl(var(--accent))" strokeWidth={2} dot={{ r: 3 }} name="abattement" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
