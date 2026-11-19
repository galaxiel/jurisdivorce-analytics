"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Calculator, Compass, Library, Radio, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/lib/api";
import { formatEur, formatPct } from "@/lib/utils";
import type { KpiOverview } from "@/lib/types";

const MODULES = [
  {
    href: "/analytics",
    icon: BarChart3,
    title: "Cockpit Global",
    text: "KPIs réactifs aux filtres croisés : abattements d'occupation, comparateur inter-cours, taux de succès par nature de réclamation, corrélation PC.",
  },
  {
    href: "/simulateur",
    icon: Compass,
    title: "Simulateur « Mon Cas »",
    text: "Questionnaire en 4 étapes : fourchettes observées, checklist des preuves indispensables, alertes pièges et dossier de synthèse exportable.",
  },
  {
    href: "/calculateur",
    icon: Calculator,
    title: "Calculateur juridique",
    text: "Art. 815-9 : indemnité d'occupation avec abattement médian de votre cour et alerte prescription. Art. 1469 : profit subsistant vs dépense faite.",
  },
  {
    href: "/decisions",
    icon: Library,
    title: "Explorer la Jurisprudence",
    text: "Recherche plein texte et filtres multicritères, cartes lisibles d'un coup d'œil avec badges financiers, export CSV/JSON.",
  },
  {
    href: "/pieges",
    icon: ShieldAlert,
    title: "Radar des Pièges",
    text: "Les 10 motifs de rejet les plus fréquents : % des échecs, montant moyen perdu et arrêts illustratifs pour chaque piège.",
  },
  {
    href: "/pipeline",
    icon: Radio,
    title: "Moniteur du Pipeline",
    text: "Avancement du téléchargement des archives Open Data (CAPP · CASS · TJ), file d'attente GLM Flash, tokens consommés, config à chaud.",
  },
];

export default function LandingPage() {
  const { data, loading } = useApi<KpiOverview>("/api/stats/overview");

  const kpis = [
    { label: "Décisions analysées", value: data ? data.total_decisions.toLocaleString("fr-FR") : null },
    { label: "Abattement moyen sur l'indemnité d'occupation", value: data ? formatPct(data.abattement_moyen_pct) : null },
    { label: "Réclamations rejetées sans factures", value: data ? formatPct(data.taux_echec_sans_factures_pct) : null },
    { label: "Capital moyen de prestation compensatoire", value: data ? formatEur(data.pc_capital_moyen) : null },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6">
      <section className="py-16 text-center">
        <h1 className="mx-auto max-w-4xl text-4xl font-extrabold tracking-tight sm:text-5xl">
          Transformez des milliers d&apos;arrêts en{" "}
          <span className="text-primary">intelligence décisionnelle</span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
          Indemnités d&apos;occupation, récompenses, créances entre époux, prestation compensatoire :
          évaluez objectivement la valeur de votre litige à partir de la jurisprudence réelle des cours
          d&apos;appel et de la Cour de cassation.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button asChild size="lg">
            <Link href="/boussole">
              Simuler mon cas <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/analytics">Voir les statistiques</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-4 pb-12 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label}>
            <CardContent className="pt-5">
              <div className="text-2xl font-bold text-primary">
                {k.value ?? <Skeleton className="h-8 w-24" />}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{k.label}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 pb-16 md:grid-cols-2 xl:grid-cols-4">
        {MODULES.map((m) => (
          <Link key={m.href} href={m.href} className="group">
            <Card className="h-full transition-shadow group-hover:shadow-md">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <m.icon className="h-5 w-5" />
                </span>
                <CardTitle className="text-lg">{m.title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{m.text}</CardContent>
            </Card>
          </Link>
        ))}
      </section>
    </div>
  );
}
