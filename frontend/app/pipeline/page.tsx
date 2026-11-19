"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Coins, Database, FileArchive, Gauge, Loader2, Pause, Play, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/analytics/kpi-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { postPipelineControl, usePipelineArchives, usePipelineLogs, usePipelineState } from "@/lib/api";
import { cn } from "@/lib/utils";

/* Vue 5 — Moniteur du pipeline : avancement archives, file GLM, logs, tokens. */
export default function PipelinePage() {
  const state = usePipelineState();
  const logs = usePipelineLogs();
  const archives = usePipelineArchives();
  const [busy, setBusy] = useState(false);

  async function control(action: "pause" | "resume" | "stop") {
    setBusy(true);
    try {
      await postPipelineControl(action);
    } catch {
      /* le moniteur reflète l'erreur via le polling */
    } finally {
      setBusy(false);
    }
  }

  const s = state.data;
  const statusVariant = {
    running: { label: "En cours", variant: "success" as const, icon: Loader2 },
    paused: { label: "En pause", variant: "secondary" as const, icon: Pause },
    stopped: { label: "Arrêté", variant: "destructive" as const, icon: Square },
    idle: { label: "Inactif", variant: "outline" as const, icon: Clock },
  }[s?.status ?? "idle"];

  return (
    <div className="mx-auto max-w-7xl space-y-5 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Moniteur du Pipeline</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Téléchargement des archives Open Data (CAPP · CASS · TJ), file d&apos;attente GLM Flash, consommation de tokens.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusVariant.variant} className="px-3 py-1 text-sm">
            {s?.status === "running" && <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />}
            {statusVariant.label}
          </Badge>
          <Button size="sm" variant="outline" disabled={busy || s?.status !== "running"} onClick={() => control("pause")}>
            <Pause className="mr-1 h-3.5 w-3.5" /> Pause
          </Button>
          <Button size="sm" variant="outline" disabled={busy || s?.status !== "paused"} onClick={() => control("resume")}>
            <Play className="mr-1 h-3.5 w-3.5" /> Reprise
          </Button>
          <Button size="sm" variant="destructive" disabled={busy || s?.status === "idle"} onClick={() => control("stop")}>
            <Square className="mr-1 h-3.5 w-3.5" /> Stop
          </Button>
        </div>
      </div>

      {state.error && (
        <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
          API indisponible : {state.error}.
        </p>
      )}

      {s?.current_archive && (
        <p className="flex items-center gap-2 truncate rounded-md border bg-card px-3 py-2 text-xs text-muted-foreground">
          <FileArchive className="h-3.5 w-3.5 shrink-0" />
          Archive courante : <span className="truncate font-mono">{s.current_archive}</span>
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        <KpiCard label="Archives traitées / total" value={`${s?.archives_done ?? 0} / ${s?.archives_total ?? 0}`} />
        <KpiCard label="Décisions parcourues" value={(s?.decisions_scanned ?? 0).toLocaleString("fr-FR")} />
        <KpiCard label="Conservées par le filtre" value={(s?.decisions_kept ?? 0).toLocaleString("fr-FR")} tone="success" />
        <KpiCard label="Analysées par GLM" value={(s?.decisions_analyzed ?? 0).toLocaleString("fr-FR")} tone="primary" />
        <KpiCard label="Échecs" value={(s?.decisions_failed ?? 0).toLocaleString("fr-FR")} tone="destructive" />
        <KpiCard label="Tokens aujourd'hui" value={(s?.tokens_today ?? 0).toLocaleString("fr-FR")} hint="Quota Zhipu : 300 M/jour" />
        <KpiCard label="Vitesse" value={`${s?.vitesse_par_minute ?? 0}/min`} tone="neutral" />
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4 text-primary" /> Archives ({archives.data?.length ?? 0} dernières)
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-96 overflow-y-auto p-0 pb-2">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Archive</TableHead>
                  <TableHead>Fonds</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Conservées</TableHead>
                  <TableHead>Analysées</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(archives.data ?? []).map((a) => (
                  <TableRow key={a.url}>
                    <TableCell className="max-w-72 truncate font-mono text-xs">{a.url.split("/").pop()}</TableCell>
                    <TableCell><Badge variant="outline">{a.fonds}</Badge></TableCell>
                    <TableCell>
                      <Badge variant={a.status === "done" ? "success" : a.status === "error" ? "destructive" : "secondary"}>
                        {a.status === "done" ? "Terminée" : a.status === "error" ? "Erreur" : "En cours"}
                      </Badge>
                      {a.error && <p className="mt-1 max-w-52 truncate text-[10px] text-destructive">{a.error}</p>}
                    </TableCell>
                    <TableCell className="tabular-nums">{a.decisions_found}</TableCell>
                    <TableCell className="tabular-nums">{a.decisions_analyzed}</TableCell>
                  </TableRow>
                ))}
                {(archives.data ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                      Aucune archive traitée pour l&apos;instant — lancez :
                      <code className="ml-2 rounded bg-secondary px-1.5 py-0.5 text-xs">python -m pipeline.ingest run --download --analyze</code>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Gauge className="h-4 w-4 text-primary" /> Logs en direct
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-96 space-y-1.5 overflow-y-auto font-mono text-[11px] leading-relaxed">
            {(logs.data ?? []).map((log) => (
              <p key={log.id} className="flex gap-2">
                <span className="shrink-0 text-muted-foreground/60">{log.ts.slice(11, 19)}</span>
                <span
                  className={cn(
                    "shrink-0 font-semibold",
                    log.level === "ERROR" ? "text-destructive" : log.level === "WARN" ? "text-accent" : "text-success",
                  )}
                >
                  {log.level === "ERROR" ? <AlertTriangle className="inline h-3 w-3" /> : log.level === "INFO" ? <CheckCircle2 className="inline h-3 w-3" /> : <Coins className="inline h-3 w-3" />}
                </span>
                <span className="text-muted-foreground">{log.message}</span>
              </p>
            ))}
            {(logs.data ?? []).length === 0 && (
              <p className="py-8 text-center text-muted-foreground">Pas encore de logs — le pipeline écrit ici dès son lancement.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
