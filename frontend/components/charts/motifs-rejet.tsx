"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MotifRejet } from "@/lib/types";

/* Top 5 des motifs de rejet des créances entre époux. */
export function MotifsRejetChart({ data }: { data: MotifRejet[] }) {
  const rows = data.map((d) => ({
    motif: d.motif.length > 52 ? `${d.motif.slice(0, 52)}…` : d.motif,
    full: d.motif,
    nb_cas: d.nb_cas,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="motif" width={280} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value: any) => [`${value} cas`, "Réclamations rejetées"]}
          labelFormatter={(_: any, payload: any) => payload?.[0]?.payload?.full ?? ""}
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12, maxWidth: 320 }}
        />
        <Bar dataKey="nb_cas" fill="hsl(var(--destructive))" radius={[0, 4, 4, 0]} barSize={20} />
      </BarChart>
    </ResponsiveContainer>
  );
}
