"use client";

/* Système d'état de déblocage Freemium : 4 niveaux (free, diagnostic_29, pack_avocat_49,
   pass_decisions_19), persistés dans localStorage, synchronisables par token URL après
   redirection Stripe. Mode test / démo dans /pipeline. */

import * as React from "react";

export type Tier = "free" | "diagnostic_29" | "pack_avocat_49" | "pass_decisions_19";

interface Entitlement {
  tier: Tier;
  expires_at: string | null;
}

const STORAGE_KEY = "jd_entitlements";

const TIER_LABELS: Record<Tier, string> = {
  free: "Gratuit",
  diagnostic_29: "Diagnostic Complet (29 €)",
  pack_avocat_49: "Pack Préparation Avocat (49 €)",
  pass_decisions_19: "Pass Exploration (19 € / 7 jours)",
};

function readStorage(): Entitlement | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const ent = JSON.parse(raw) as Entitlement;
    if (ent.expires_at && new Date(ent.expires_at) < new Date()) return null;
    return ent;
  } catch {
    return null;
  }
}

function isExpired(ent: Entitlement | null): boolean {
  return !ent || (ent.expires_at != null && new Date(ent.expires_at) < new Date());
}

interface EntitlementsContextValue {
  tier: Tier;
  canAccess: (feature: "diagnostic" | "dossier" | "decisions_full") => boolean;
  unlock: (tier: Exclude<Tier, "free">, days?: number) => void;
  reset: () => void;
}

const EntitlementsContext = React.createContext<EntitlementsContextValue>({
  tier: "free",
  canAccess: () => false,
  unlock: () => {},
  reset: () => {},
});

export function EntitlementsProvider({ children }: { children: React.ReactNode }) {
  const [tier, setTier] = React.useState<Tier>("free");

  React.useEffect(() => {
    const ent = readStorage();
    setTier(ent && !isExpired(ent) ? ent.tier : "free");
  }, []);

  // Synchronisation par token URL : /?tier=diagnostic_29&days=30
  React.useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const t = sp.get("tier") as Tier | null;
    if (t && t in TIER_LABELS && t !== "free") {
      const days = Number(sp.get("days") || 30);
      unlock(t as Exclude<Tier, "free">, days);
      // nettoie l'URL après application
      window.history.replaceState({}, "", window.location.pathname);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const unlock = React.useCallback((t: Exclude<Tier, "free">, days = 30) => {
    const expires = new Date(Date.now() + days * 24 * 3600 * 1000).toISOString();
    const ent: Entitlement = { tier: t, expires_at: expires };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ent));
    setTier(t);
  }, []);

  const reset = React.useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setTier("free");
  }, []);

  const canAccess = React.useCallback(
    (feature: "diagnostic" | "dossier" | "decisions_full") => {
      if (tier === "pack_avocat_49") return true;
      if (tier === "diagnostic_29") return feature === "diagnostic" || feature === "decisions_full";
      if (tier === "pass_decisions_19") return feature === "decisions_full";
      return false;
    },
    [tier],
  );

  return (
    <EntitlementsContext.Provider value={{ tier, canAccess, unlock, reset }}>
      {children}
    </EntitlementsContext.Provider>
  );
}

export function useEntitlements() {
  return React.useContext(EntitlementsContext);
}

export { TIER_LABELS, STORAGE_KEY };
