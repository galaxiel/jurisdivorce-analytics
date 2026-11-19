"use client";

import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  hint,
  tone = "primary",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "primary" | "success" | "destructive" | "neutral";
}) {
  const toneClass = {
    primary: "text-primary",
    success: "text-success",
    destructive: "text-destructive",
    neutral: "text-foreground",
  }[tone];

  return (
    <Card className="shadow-card">
      <CardContent className="p-4">
        <div className={cn("text-2xl font-bold tabular-nums", toneClass)}>{value}</div>
        <p className="mt-1 text-xs font-medium leading-snug text-muted-foreground">{label}</p>
        {hint && <p className="mt-0.5 text-[11px] text-muted-foreground/70">{hint}</p>}
      </CardContent>
    </Card>
  );
}
