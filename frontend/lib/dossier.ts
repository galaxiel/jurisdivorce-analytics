/* Générateur de « Dire à Notaire / Note pour mon Avocat » — Markdown, Word (.doc) et impression.
   Partagé par le Simulateur et le Calculateur (chantier 2.2 de la mission V3). */

export interface DossierInput {
  titre: string;
  situation: { label: string; value: string }[];
  demandes: { label: string; value: string }[];
  references: { juridiction: string; date: string; rg?: string | null; resume: string }[];
  pieces: string[];
  notes?: string[];
}

export function buildDossierMarkdown(d: DossierInput): string {
  const lines: string[] = [
    `# ${d.titre}`,
    "",
    `*Document préparé avec JurisDivorce Analytics le ${new Date().toLocaleDateString("fr-FR")} — `
      + "à remettre au notaire liquidateur ou à l'avocat, avec les pièces citées. "
      + "Document indicatif : il ne remplace pas l'analyse d'un professionnel du droit.*",
    "",
    "## 1. Exposé de la situation",
    ...d.situation.map((s) => `- **${s.label}** : ${s.value}`),
    "",
    "## 2. Prétentions chiffrées",
    ...d.demandes.map((s) => `- **${s.label}** : ${s.value}`),
    "",
    "## 3. Références de jurisprudence soutenant la position",
    ...d.references.map(
      (r, i) =>
        `${i + 1}. **${r.juridiction}** — ${r.date}${r.rg ? ` (n° RG ${r.rg})` : ""} : ${r.resume}`,
    ),
    "",
    "## 4. Pièces à annexer impérativement",
    ...d.pieces.map((p) => `- [ ] ${p}`),
  ];
  if (d.notes?.length) {
    lines.push("", "## 5. Notes méthodologiques", ...d.notes.map((n) => `- ${n}`));
  }
  return lines.join("\n");
}

function dossierHtml(d: DossierInput): string {
  const list = (items: string[], ordered = false) =>
    `<${ordered ? "ol" : "ul"}>${items.map((i) => `<li>${i}</li>`).join("")}</${ordered ? "ol" : "ul"}>`;
  return `<html><head><meta charset="utf-8"><title>${d.titre}</title></head><body
    style="font-family: Georgia, serif; font-size: 11pt; line-height: 1.5; max-width: 700px; margin: 40px auto;">
  <h1 style="font-size: 16pt;">${d.titre}</h1>
  <p style="color: #666; font-size: 9pt;">Préparé avec JurisDivorce Analytics le ${new Date().toLocaleDateString("fr-FR")}
  — à remettre au notaire liquidateur ou à l'avocat, avec les pièces citées. Document indicatif,
  il ne remplace pas l'analyse d'un professionnel du droit.</p>
  <h2 style="font-size: 13pt;">1. Exposé de la situation</h2>
  ${list(d.situation.map((s) => `<b>${s.label}</b> : ${s.value}`))}
  <h2 style="font-size: 13pt;">2. Prétentions chiffrées</h2>
  ${list(d.demandes.map((s) => `<b>${s.label}</b> : ${s.value}`))}
  <h2 style="font-size: 13pt;">3. Références de jurisprudence soutenant la position</h2>
  ${list(
    d.references.map(
      (r) => `<b>${r.juridiction}</b> — ${r.date}${r.rg ? ` (n° RG ${r.rg})` : ""} : ${r.resume}`,
    ),
    true,
  )}
  <h2 style="font-size: 13pt;">4. Pièces à annexer impérativement</h2>
  ${list(d.pieces)}
  ${d.notes?.length ? `<h2 style="font-size: 13pt;">5. Notes méthodologiques</h2>${list(d.notes)}` : ""}
  </body></html>`;
}

function triggerDownload(content: string, filename: string, mime: string) {
  const blob = new Blob(["\ufeff" + content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Exporte le dossier : "md" (fichier .md), "doc" (Word-compatible .doc) ou "print" (PDF via l'impression). */
export function exportDossier(d: DossierInput, mode: "md" | "doc" | "print") {
  const base = "dire-a-notaire-jurisdivorce";
  if (mode === "md") {
    triggerDownload(buildDossierMarkdown(d), `${base}.md`, "text/markdown;charset=utf-8");
  } else if (mode === "doc") {
    triggerDownload(dossierHtml(d), `${base}.doc`, "application/msword");
  } else {
    const w = window.open("", "_blank");
    if (w) {
      w.document.write(dossierHtml(d));
      w.document.close();
      w.focus();
      w.print();
    }
  }
}
