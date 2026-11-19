"use client";

import { Scale } from "lucide-react";
import { useHealth } from "@/lib/api";
import healthSnapshot from "@/public/data/health.json";
import type { HealthStatus } from "@/lib/types";

/* Règle d'Or N°5 — clause de non-responsabilité obligatoire sur toutes les routes publiques
   et en en-tête de chaque document exporté. Ne jamais supprimer ni raccourcir.
   Ce composant est aussi le pied de page unique du site (l'ancien <Footer /> a été
   fusionné ici : marquage des données + source active, rendus dynamiques via /api/health). */
export function LegalDisclaimerFooter() {
  const { data } = useHealth();
  // Pré-remplissage SSR depuis le snapshot (export statique) ; l'API live écrase ensuite.
  const health = (data ?? healthSnapshot) as HealthStatus;
  const synth = health.synth_demo_count ?? 0;

  return (
    <footer className="border-t bg-muted/50 px-4 py-4">
      <div className="mx-auto flex max-w-4xl items-start gap-3">
        <Scale className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
        <div className="space-y-1">
          <p className="text-xs leading-relaxed text-muted-foreground">
            JurisDivorce Analytics est un outil <b>statistique et jurisprudentiel</b> indicatif.
            Les fourchettes et pourcentages affichés sont des <b>observations statistiques</b>{" "}
            issues de décisions de justice passées. Ils ne constituent pas un avis juridique ni
            une consultation personnalisée (loi n° 71-1130 du 31 décembre 1971), et ne remplacent
            en aucun cas l&apos;analyse et les conseils de votre avocat ou notaire.
          </p>
          <p className="text-[11px] text-muted-foreground/80">
            {data
              ? data.source === "snapshot"
                ? `Mode snapshot : l'API ne répond pas, les agrégats servis sont pré-calculés (${data.decisions.toLocaleString("fr-FR")} décisions).`
                : `Source des données : API live · ${health.decisions.toLocaleString("fr-FR")} décisions · worker ${health.worker_status}.`
              : `Source des données : ${health.decisions.toLocaleString("fr-FR")} décisions (snapshot pré-calculé).`}{" "}
            {synth > 0 ? (
              <>
                {synth.toLocaleString("fr-FR")} décision(s) sont marquées{" "}
                <span className="font-mono">SYNTHETIQUE_DEMO</span> (jeu de démonstration) ; les
                décisions issues des archives Open Data Judilibre sont marquées{" "}
                <span className="font-mono">JUDILIBRE_OD</span>.
              </>
            ) : (
              <>
                Les décisions affichées sont issues des archives Open Data Judilibre, marquées{" "}
                <span className="font-mono">JUDILIBRE_OD</span>.
              </>
            )}
          </p>
        </div>
      </div>
    </footer>
  );
}
