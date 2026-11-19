import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { DemoBanner } from "@/components/demo-banner";
import { Header } from "@/components/layout/header";
import { LegalDisclaimerFooter } from "@/components/legal-disclaimer-footer";
import { EntitlementsProvider } from "@/lib/entitlements";

export const metadata: Metadata = {
  title: "JurisDivorce Analytics — Boussole & Analytics Liquidation-Partage",
  description:
    "Plateforme d'analyse statistique et décisionnelle de la jurisprudence en droit de la famille : indemnités d'occupation, récompenses, prestation compensatoire.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body className="min-h-screen">
        <EntitlementsProvider>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <DemoBanner />
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <LegalDisclaimerFooter />
          </div>
        </ThemeProvider>
        </EntitlementsProvider>
      </body>
    </html>
  );
}
