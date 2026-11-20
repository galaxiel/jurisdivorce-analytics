"use client";

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Calculator,
  Coins,
  Compass,
  Database,
  FileWarning,
  Library,
  Percent,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/lib/api";
import { formatEur, formatPct } from "@/lib/utils";
import type { KpiOverview } from "@/lib/types";
import statsSnapshot from "@/public/data/stats_globales.json";

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
];

const STEPS = [
  {
    icon: Compass,
    title: "1 · Décrivez votre situation",
    text: "Le simulateur vous pose les questions utiles (statut, chronologie, revenus, biens) et situe votre cas dans la base.",
  },
  {
    icon: BarChart3,
    title: "2 · Observez les fourchettes constatées",
    text: "Sur les décisions comparables de votre juridiction : médianes, percentiles et taux d'accord observés, jamais un montant « dû ».",
  },
  {
    icon: ShieldCheck,
    title: "3 · Préparez votre rendez-vous",
    text: "Exportez un dossier de synthèse statistique et jurisprudentielle pour préparer votre rendez-vous avec votre avocat ou notaire.",
  },
];

export default function LandingPage() {
  const { data } = useApi<KpiOverview>("/api/stats/overview");
  // Pré-remplissage SSR depuis le snapshot (export statique) : pas de cartes vides
  // au premier rendu, meilleur SEO ; l'appel API live écrase ensuite côté client.
  const kpi = (data ?? statsSnapshot) as KpiOverview;

  const kpis = [
    { label: "Décisions analysées", value: kpi.total_decisions.toLocaleString("fr-FR"), icon: Database },
    { label: "Abattement médian sur l'indemnité d'occupation", value: formatPct(kpi.abattement_moyen_pct), icon: Percent },
    { label: "Réclamations rejetées sans factures", value: formatPct(kpi.taux_echec_sans_factures_pct), icon: FileWarning },
    { label: "Capital médian de prestation compensatoire", value: formatEur(kpi.pc_capital_median), icon: Coins },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6">
      {/* ===== Hero ===== */}
      <section className="bg-hero relative -mx-4 overflow-hidden px-4 pb-14 pt-16 text-center sm:-mx-6 sm:px-6 sm:pt-20">
        <div className="bg-grid pointer-events-none absolute inset-0" aria-hidden />
        <div className="relative">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            {`${kpi.total_decisions.toLocaleString("fr-FR")} décisions de ${kpi.nb_juridictions} juridictions · ${kpi.periode}`}
          </div>
          <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-extrabold tracking-tight sm:text-6xl">
            Situez votre litige dans{" "}
            <span className="text-gradient">la jurisprudence réelle</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted-foreground">
            Indemnités d&apos;occupation, récompenses, créances entre époux, prestation compensatoire :
            observez les montants médians et les fourchettes constatées dans les arrêts publiés des cours
            d&apos;appel et de la Cour de cassation.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg" className="shadow-card-hover">
              <Link href="/simulateur">
                Simuler mon cas <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/analytics">Voir les statistiques</Link>
            </Button>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Statistiques indicatives fondées sur la jurisprudence publiée — ne constituent pas un avis juridique.
          </p>
        </div>
      </section>

      {/* ===== KPIs ===== */}
      <section className="grid gap-4 py-10 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label} className="card-hover shadow-card">
            <CardContent className="flex items-start gap-3 pt-5">
              <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <k.icon className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <div className="tabular-nums text-2xl font-bold text-primary">{k.value}</div>
                <p className="mt-1 text-xs leading-snug text-muted-foreground">{k.label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      {/* ===== Méthode ===== */}
      <section className="pb-12">
        <h2 className="text-center text-2xl font-bold tracking-tight">Comment ça marche ?</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <Card key={s.title} className="shadow-card">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
                  <s.icon className="h-5 w-5" />
                </span>
                <CardTitle className="text-base">{s.title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm leading-relaxed text-muted-foreground">{s.text}</CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* ===== Modules ===== */}
      <section className="pb-14">
        <h2 className="text-center text-2xl font-bold tracking-tight">Les modules</h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-sm text-muted-foreground">
          Six outils statistiques, une même base de décisions analysées.
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {MODULES.map((m) => (
            <Link key={m.href} href={m.href} className="group">
              <Card className="card-hover h-full border-transparent shadow-card group-hover:border-primary/30">
                <CardHeader className="flex-row items-center gap-3 space-y-0">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                    <m.icon className="h-5 w-5" />
                  </span>
                  <CardTitle className="flex-1 text-lg">{m.title}</CardTitle>
                  <ArrowRight className="h-4 w-4 -translate-x-1 text-muted-foreground opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
                </CardHeader>
                <CardContent className="text-sm leading-relaxed text-muted-foreground">{m.text}</CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* ===== CTA final ===== */}
      <section className="pb-16">
        <div className="bg-banner card-hover rounded-[var(--radius)] border px-6 py-10 text-center shadow-card">
          <h2 className="mx-auto max-w-2xl text-2xl font-bold tracking-tight sm:text-3xl">
            Une question chiffrée, une base de <span className="text-gradient">{kpi.total_decisions.toLocaleString("fr-FR")} décisions</span> pour la situer
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground">
            Le simulateur « Mon Cas » confronte votre situation aux arrêts comparables : fourchettes observées,
            taux d&apos;accord constatés, preuves qui font la différence.
          </p>
          <Button asChild size="lg" className="mt-6 shadow-card-hover">
            <Link href="/simulateur">
              Lancer la simulation <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
}
