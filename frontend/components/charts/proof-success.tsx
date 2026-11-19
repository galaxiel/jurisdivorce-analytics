"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PROOF_LABELS, type PreuveSucces } from "@/lib/types";

/* Taux de succès des réclamations selon le type de preuve possédée. */
const FILL_BY_TYPE: Record<string, string> = {
  FACTURE_NOMINATIVE: "hsl(var(--success))",
  RELEVE_BANCAIRE: "hsl(var(--primary))",
  ATTESTATION: "hsl(var(--accent))",
  AUTRE: "hsl(var(--muted-foreground))",
  AUCUNE: "hsl(var(--destructive))",
};

export function ProofSuccessChart({ data }: { data: PreuveSucces[] }) {
  const rows = data.map((d) => ({
    name: PROOF_LABELS[d.preuve_type] ?? d.preuve_type,
    taux: d.taux_succes_pct,
    nb: d.nb_reclamations,
    fill: FILL_BY_TYPE[d.preuve_type] ?? "hsl(var(--primary))",
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-12} textAnchor="end" height={60} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v} %`} />
        <Tooltip
          formatter={(value: any, _name: any, item: any) => [
            `${value} %`,
            `Taux de succès (${item?.payload?.nb ?? 0} réclamations)`,
          ]}
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600, marginBottom: 4 }}
          itemStyle={{ color: "hsl(var(--foreground))" }}
        />
        <Bar dataKey="taux" radius={[4, 4, 0, 0]} barSize={44}>
          {rows.map((row) => (
            <Cell key={row.name} fill={row.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
