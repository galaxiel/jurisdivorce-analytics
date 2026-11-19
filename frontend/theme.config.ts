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

  radius: "0.875rem",

  fontFamily: {
    sans: "'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', ui-monospace, 'SF Mono', Consolas, monospace",
  },

  gradients: {
    hero: "radial-gradient(1100px 480px at 50% -12%, hsl(var(--primary) / 0.16), transparent 70%), radial-gradient(700px 320px at 85% 0%, hsl(var(--accent) / 0.10), transparent 70%)",
    banner: "linear-gradient(120deg, hsl(var(--primary) / 0.14), hsl(var(--accent) / 0.12))",
    card: "linear-gradient(180deg, hsl(var(--surface)), hsl(var(--surface)))",
  },

  shadows: {
    card: "0 1px 2px 0 rgb(15 23 42 / 0.05), 0 2px 6px -1px rgb(15 23 42 / 0.05)",
    cardHover: "0 10px 24px -8px rgb(15 23 42 / 0.18), 0 2px 6px -2px rgb(15 23 42 / 0.08)",
    elevated: "0 16px 40px -12px rgb(15 23 42 / 0.25)",
  },
} as const;

export type ThemeConfig = typeof themeConfig;
