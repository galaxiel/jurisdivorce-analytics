"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AbattementBucket } from "@/lib/types";

/* Distribution des abattements d'indemnité d'occupation (10 %, 15 %, 20 %, 25 %, 30 %…). */
export function AbattementDistributionChart({ data }: { data: AbattementBucket[] }) {
  const rows = data.map((d) => ({
    name: d.bucket,
    nb: d.nb_decisions,
    moyenne: d.moyenne_indemnite_mensuelle,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: any, _name: any, item: any) => [
            `${value} décisions`,
            item?.payload?.moyenne != null ? `Indemnité moyenne ${item.payload.moyenne} €/mois` : "Décisions",
          ]}
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600, marginBottom: 4 }}
          itemStyle={{ color: "hsl(var(--foreground))" }}
        />
        <Bar dataKey="nb" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} barSize={48} />
      </BarChart>
    </ResponsiveContainer>
  );
}
