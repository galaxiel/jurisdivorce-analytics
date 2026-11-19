/**
 * Identité visuelle centralisée (cahier des charges : "toute l'identité visuelle
 * modifiable en une seule passe"). Les triplets HSL vivent dans app/globals.css
 * (:root / .dark) ; ce fichier est la source de vérité pour Tailwind et le JS.
 *
 * Re-skin : changez les valeurs HSL ici ET dans globals.css — rien d'autre.
 */
export const themeConfig = {
  /** Triplets HSL utilisés par Tailwind (voir tailwind.config.ts) */
  hslTokens: {
    primary: "224 76% 48%", // bleu royal
    accent: "172 66% 40%", // teal
    success: "160 74% 34%",
    destructive: "356 74% 50%",
    background: "210 40% 98%",
    surface: "0 0% 100%",
  } as const,

  radius: "0.75rem",

  fontFamily: {
    sans: "'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, monospace",
  },

  gradients: {
    hero: "radial-gradient(1200px 500px at 50% -10%, hsl(var(--primary) / 0.14), transparent)",
    card: "linear-gradient(180deg, hsl(var(--surface)), hsl(var(--surface)))",
  },

  shadows: {
    card: "0 1px 2px 0 rgb(15 23 42 / 0.05), 0 1px 3px 0 rgb(15 23 42 / 0.04)",
    cardHover: "0 4px 16px -2px rgb(15 23 42 / 0.12)",
  },
} as const;

export type ThemeConfig = typeof themeConfig;
