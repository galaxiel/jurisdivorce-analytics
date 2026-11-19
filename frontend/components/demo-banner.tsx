"use client";

import { useEffect, useState } from "react";
import { Database, Eraser } from "lucide-react";
import { Button } from "@/components/ui/button";
import { deleteDemo, postDemoSeed, useApi } from "@/lib/api";

/* Chantier 2.4 : mode démo — bandeau si la base est presque vide (< 50 décisions),
   chargement de 50 arrêts réalistes (is_demo) et purge en 1 clic. */
export function DemoBanner() {
  const [tick, setTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const health = useApi<{ decisions: number }>("/api/health", tick);
  const demo = useApi<{ demo_decisions: number }>("/api/demo/count", tick);

  useEffect(() => {
    if (busy) {
      const t = setTimeout(() => {
        setBusy(false);
        setTick((t) => t + 1);
      }, 1500);
      return () => clearTimeout(t);
    }
  }, [busy]);

  if (health.loading || !health.data) return null;
  const total = health.data.decisions;
  const demoCount = demo.data?.demo_decisions ?? 0;
  if (total >= 50 && demoCount === 0) return null;

  async function load() {
    setBusy(true);
    await postDemoSeed();
  }
  async function purge() {
    setBusy(true);
    await deleteDemo();
  }

  return (
    <div className="border-b border-warning/40 bg-warning/10 px-4 py-2.5">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-2 text-sm">
        <span className="flex items-center gap-2 text-foreground">
          <Database className="h-4 w-4 text-warning" />
          {total < 50
            ? `La base ne contient que ${total} décision(s) — chargez un jeu de démonstration réaliste pour tester tous les graphiques.`
            : `${demoCount} arrêts de démonstration (is_demo) présents dans la base.`}
        </span>
        <span className="flex gap-2">
          {total < 50 && (
            <Button size="sm" variant="outline" className="h-8" disabled={busy} onClick={load}>
              <Database className="mr-1.5 h-3.5 w-3.5" /> Charger 50 arrêts de démonstration
            </Button>
          )}
          {demoCount > 0 && (
            <Button size="sm" variant="outline" className="h-8" disabled={busy} onClick={purge}>
              <Eraser className="mr-1.5 h-3.5 w-3.5" /> Purger les données de démo
            </Button>
          )}
        </span>
      </div>
    </div>
  );
}
