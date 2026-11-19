"use client";

import { useSearchParams } from "next/navigation";
import { CheckCircle2, CreditCard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useEntitlements } from "@/lib/entitlements";
import { TIER_LABELS } from "@/lib/entitlements";

/* Page de simulation de paiement : s'affiche quand STRIPE_SECRET_KEY n'est pas configurée.
   Permet de valider un paiement test en 1 clic et de débloquer immédiatement les résultats. */
export default function CheckoutSimulationPage() {
  const searchParams = useSearchParams();
  const { unlock } = useEntitlements();
  const tier = (searchParams.get("tier") ?? "diagnostic_29") as "diagnostic_29" | "pack_avocat_49" | "pass_decisions_19";
  const days = Number(searchParams.get("days") || 30);
  const label = TIER_LABELS[tier] ?? tier;
  const price = tier === "diagnostic_29" ? "29 €" : tier === "pack_avocat_49" ? "49 €" : "19 €";

  function validate() {
    unlock(tier, days);
    window.location.href = "/simulateur";
  }

  return (
    <div className="mx-auto flex max-w-lg items-center justify-center px-4 py-16">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CreditCard className="h-5 w-5 text-primary" /> Paiement simulé — {label}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Mode démo : <b>STRIPE_SECRET_KEY</b> n&apos;est pas configurée. Cliquez pour
            débloquer immédiatement l&apos;accès {label} ({price}) pendant {days} jours.
          </p>
        </CardHeader>
        <CardContent>
          <Button className="w-full" onClick={validate}>
            <CheckCircle2 className="mr-1.5 h-4 w-4" /> Valider le paiement test
          </Button>
          <p className="mt-3 text-[10px] text-muted-foreground">
            En production, cette page est remplacée par la session Stripe Checkout
            (paiement par carte sécurisé). Configurez <code>STRIPE_SECRET_KEY</code> dans
            le fichier <code>.env</code> pour activer les vrais paiements.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
