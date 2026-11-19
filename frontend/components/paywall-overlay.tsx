"use client";

import { Check, Lock, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/* Overlay de paywall : rend les enfants réellement sous le flou (blur-md select-none),
   avec une carte de déblocage centrée au premier plan. Règle d'Or N°5 : les textes
   chiffrés sont rendus (pour le SEO et la structure) mais floutés et non sélectionnables. */

interface PaywallOverlayProps {
  tier: "diagnostic_29" | "pack_avocat_49";
  onUnlock: (tier: "diagnostic_29" | "pack_avocat_49") => void;
  className?: string;
}

const OFFERS = [
  {
    tier: "diagnostic_29" as const,
    name: "Diagnostic Complet « Mon Cas »",
    price: "29 €",
    subtitle: "TTC · Paiement unique",
    features: [
      "Fourchettes chiffrées exactes (basse / médiane / haute)",
      "Détail du compte de gestion des biens indivis / locatifs",
      "Checklist des preuves déterminantes",
      "5 arrêts similaires complets (Juridiction, Date, N° RG)",
    ],
    highlight: false,
  },
  {
    tier: "pack_avocat_49" as const,
    name: "Pack Préparation Avocat / Dire à Notaire",
    price: "49 €",
    subtitle: "TTC · Paiement unique",
    features: [
      "Tout le Diagnostic Complet (29 €)",
      "Générateur de dossier exportable structuré (.pdf / .docx / .md)",
      "Prêt à remettre à son avocat ou notaire",
      "Checklist complète des pièces justificatives",
    ],
    highlight: true,
  },
];

export function PaywallOverlay({ tier, onUnlock, className }: PaywallOverlayProps) {
  return (
    <div className={cn("relative", className)}>
      {/* Contenu flouté (rendu réellement pour le SEO et la structure) */}
      <div className="pointer-events-none select-none blur-md" aria-hidden="true">
        {/*
          Le contenu chiffré réel est rendu ici par le parent via children.
          Ce composant ne fait que superposer le voile.
        */}
        <div className="h-64 rounded-lg bg-secondary/50" />
      </div>

      {/* Carte de déblocage centrée */}
      <div className="absolute inset-0 flex items-center justify-center p-2">
        <div className="w-full max-w-2xl rounded-xl border-2 border-primary/30 bg-card p-5 shadow-xl">
          <div className="mb-3 flex items-center gap-2">
            <Zap className="h-5 w-5 text-warning" />
            <span className="text-sm font-semibold">
              Débloquez les résultats chiffrés et les arrêts similaires
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {OFFERS.map((offer) => (
              <div
                key={offer.tier}
                className={cn(
                  "relative rounded-lg border p-4 text-sm",
                  offer.highlight
                    ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                    : "border-border bg-card",
                )}
              >
                {offer.highlight && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-0.5 text-[10px] font-bold text-primary-foreground">
                    Le plus choisi
                  </span>
                )}
                <p className="font-semibold">{offer.name}</p>
                <p className="mt-1 text-2xl font-extrabold tabular-nums">{offer.price}</p>
                <p className="text-[10px] text-muted-foreground">{offer.subtitle}</p>
                <ul className="mt-2.5 space-y-1 text-xs text-muted-foreground">
                  {offer.features.map((f) => (
                    <li key={f} className="flex items-start gap-1.5">
                      <Check className="mt-0.5 h-3 w-3 shrink-0 text-success" /> {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className={cn("mt-3 w-full", offer.highlight && "bg-primary text-primary-foreground hover:bg-primary/90")}
                  variant={offer.highlight ? "default" : "outline"}
                  size="sm"
                  onClick={() => onUnlock(offer.tier)}
                >
                  Débloquer — {offer.price}
                </Button>
              </div>
            ))}
          </div>
          <p className="mt-3 text-center text-[10px] text-muted-foreground">
            Paiement unique · Sans abonnement · Accès immédiat
          </p>
        </div>
      </div>
    </div>
  );
}

/* Overlay simplifié pour le Pass Jurisprudence 19 € dans /decisions. */
export function PassOverlay({ onUnlock, className }: { onUnlock: () => void; className?: string }) {
  return (
    <div className={cn("relative", className)}>
      <div className="pointer-events-none select-none blur-md" aria-hidden="true">
        <div className="h-40 rounded-lg bg-secondary/50" />
      </div>
      <div className="absolute inset-0 flex items-center justify-center p-2">
        <div className="w-full max-w-md rounded-xl border-2 border-primary/30 bg-card p-5 shadow-xl">
          <div className="mb-2 flex items-center gap-2">
            <Lock className="h-5 w-5 text-primary" />
            <span className="text-sm font-semibold">Fiche décisionnelle complète</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Débloquez l&apos;analyse détaillée des preuves et motifs décisifs, et le texte
            intégral surligné — pour tous les arrêts de la base pendant 7 jours.
          </p>
          <p className="mt-2 text-2xl font-extrabold tabular-nums">19 €</p>
          <p className="text-[10px] text-muted-foreground">TTC · 7 jours · Paiement unique</p>
          <Button className="mt-3 w-full" onClick={onUnlock}>
            <Zap className="mr-1.5 h-3.5 w-3.5" /> Débloquer — 19 € / 7 jours
          </Button>
        </div>
      </div>
    </div>
  );
}

/* Légende du lock (rappel discret) */
export function PaywallHint({ text }: { text: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
      <Lock className="h-3 w-3" /> {text}
    </span>
  );
}

