export function Footer() {
  return (
    <footer className="border-t py-6">
      <div className="mx-auto max-w-7xl space-y-1 px-4 text-center text-xs text-muted-foreground sm:px-6">
        <p>
          JurisDivorce Analytics — outil statistique indicatif fondé sur la jurisprudence publiée.
          Il ne constitue pas un avis juridique et ne remplace pas votre avocat ou notaire.
        </p>
        <p>
          Les données sont marquées <span className="font-mono">SYNTHETIQUE_DEMO</span> tant que le
          pipeline d&apos;ingestion Open Data n&apos;a pas été exécuté sur les archives Judilibre.
        </p>
      </div>
    </footer>
  );
}
