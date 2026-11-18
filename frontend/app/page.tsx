"use client";

import Link from "next/link";
import { ArrowRight, BarChart3, Compass, Library } from "lucide-react";
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
    title: "Dashboard Analytics",
    text: "Taux d'abattement moyen sur l'indemnité d'occupation, montants des récompenses, comparatif des Cours d'appel, top des motifs de rejet.",
  },
  {
    href: "/boussole",
    icon: Compass,
    title: "La Boussole — Mon Cas",
    text: "Questionnaire en 4 étapes : fourchette d'indemnité d'occupation, chances de succès selon vos preuves, 5 décisions jumelles.",
  },
  {
    href: "/jurisprudence",
    icon: Library,
    title: "Explorer la Jurisprudence",
    text: "Moteur de recherche à filtres combinés : cour d'appel, régime matrimonial, statut des récompenses, prestation compensatoire.",
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

      <section className="grid gap-4 pb-16 md:grid-cols-3">
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
