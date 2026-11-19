import { Scale } from "lucide-react";

/* Règle d'Or N°5 — clause de non-responsabilité obligatoire sur toutes les routes publiques
   et en en-tête de chaque document exporté. Ne jamais supprimer ni raccourcir. */
export function LegalDisclaimerFooter() {
  return (
    <div className="border-t bg-muted/50 px-4 py-4">
      <div className="mx-auto flex max-w-4xl items-start gap-3">
        <Scale className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
        <p className="text-xs leading-relaxed text-muted-foreground">
          JurisDivorce Analytics est un outil <b>statistique et jurisprudentiel</b> indicatif.
          Les fourchettes et pourcentages affichés sont des <b>observations statistiques</b>{" "}
          issues de décisions de justice passées. Ils ne constituent pas un avis juridique ni
          une consultation personnalisée (loi n° 71-1130 du 31 décembre 1971), et ne remplacent
          en aucun cas l&apos;analyse et les conseils de votre avocat ou notaire.
        </p>
      </div>
    </div>
  );
}
