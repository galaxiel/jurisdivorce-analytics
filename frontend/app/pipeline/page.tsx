"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Coins, Database, FileArchive, Gauge, KeyRound, Loader2, Pause, Play, RefreshCw, Save, Square } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KpiCard } from "@/components/analytics/kpi-card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  getAdminToken,
  postPipelineControl,
  postRetryFailed,
  putPipelineConfig,
  setAdminToken,
  useBenchmark,
  usePipelineArchives,
  usePipelineConfig,
  usePipelineLogs,
  usePipelineState,
} from "@/lib/api";
import { cn } from "@/lib/utils";

/* Vue 5 — Moniteur du pipeline (admin) : avancement archives, file GLM, logs, tokens.
   Protégé par X-Admin-Token (JURISDIVORCE_ADMIN_TOKEN côté backend). */
export default function PipelinePage() {
  const [token, setToken] = useState("");
  const [tokenSet, setTokenSet] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const t = getAdminToken();
    if (t) {
      setToken(t);
      setTokenSet(true);
    }
  }, []);

  function submitToken() {
    setAdminToken(token.trim());
    setTokenSet(Boolean(token.trim()));
    setRefreshKey((k) => k + 1);
  }

  const state = usePipelineState(refreshKey);
  const logs = usePipelineLogs(refreshKey);
  const archives = usePipelineArchives(refreshKey);
  const config = usePipelineConfig(refreshKey);
  const benchmark = useBenchmark(refreshKey);
  const [busy, setBusy] = useState(false);
  const [cfg, setCfg] = useState<{ max_concurrency: string; model: string; max_chars: string } | null>(null);
  const [cfgSaved, setCfgSaved] = useState(false);

  if (!tokenSet) {
    return (
      <div className="mx-auto max-w-md space-y-4 px-4 py-16">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <KeyRound className="h-5 w-5 text-primary" /> Accès réservé — Moniteur du Pipeline
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Cette page d&apos;administration est protégée. Saisissez le token admin
              (<code className="rounded bg-secondary px-1 text-xs">JURISDIVORCE_ADMIN_TOKEN</code>) :
            </p>
            <Input
              type="password"
              placeholder="Token admin…"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitToken()}
            />
            <Button className="w-full" onClick={submitToken} disabled={!token.trim()}>
              Déverrouiller
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

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

  async function retryFailed() {
    setBusy(true);
    try {
      await postRetryFailed();
    } finally {
      setBusy(false);
    }
  }

  async function saveConfig() {
    if (!cfg) return;
    setBusy(true);
    try {
      await putPipelineConfig({
        max_concurrency: Number(cfg.max_concurrency),
        model: cfg.model,
        max_chars: Number(cfg.max_chars),
      });
      setCfgSaved(true);
      setTimeout(() => setCfgSaved(false), 2500);
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
  }[s?.status ?? "idle"] ?? { label: s?.status ?? "Inactif", variant: "outline" as const, icon: Clock };

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
          <Button
            size="sm" variant="ghost" title="Verrouiller (oublier le token)"
            onClick={() => { setAdminToken(""); setToken(""); setTokenSet(false); }}
          >
            <KeyRound className="mr-1 h-3.5 w-3.5" /> Verrouiller
          </Button>
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
          <Button size="sm" variant="outline" disabled={busy} onClick={retryFailed} title="Relancer les décisions en échec (DLQ)">
            <RefreshCw className="mr-1 h-3.5 w-3.5" /> Relancer les échecs
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

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <KpiCard label="Archives traitées / total" value={`${s?.archives_done ?? 0} / ${s?.archives_total ?? 0}`} />
        <KpiCard label="Fichiers XML/JSON lus" value={(s?.files_read ?? 0).toLocaleString("fr-FR")} />
        <KpiCard label="Décisions parcourues" value={(s?.decisions_scanned ?? 0).toLocaleString("fr-FR")} />
        <KpiCard label="Conservées par le filtre" value={(s?.decisions_kept ?? 0).toLocaleString("fr-FR")} tone="success" />
        <KpiCard label="Analysées par GLM" value={(s?.decisions_analyzed ?? 0).toLocaleString("fr-FR")} tone="primary" />
        <KpiCard label="Échecs (DLQ)" value={(s?.decisions_failed ?? 0).toLocaleString("fr-FR")} tone="destructive" />
        <KpiCard label="Tokens aujourd'hui" value={(s?.tokens_today ?? 0).toLocaleString("fr-FR")} hint="Quota Zhipu : 300 M/jour" />
        <KpiCard label="Vitesse" value={`${s?.vitesse_par_minute ?? 0}/min`} tone="neutral" />
      </div>

      {/* Chantier 1.6 : configuration à chaud + Chantier 2.4 : benchmark */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Configuration du worker (appliquée à chaud)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Concurrence max</Label>
                <Input
                  className="h-9 text-sm" type="number" min={1} max={100}
                  value={cfg?.max_concurrency ?? config.data?.max_concurrency ?? 25}
                  onChange={(e) =>
                    setCfg({
                      max_concurrency: e.target.value,
                      model: cfg?.model ?? config.data?.model ?? "",
                      max_chars: cfg?.max_chars ?? String(config.data?.max_chars ?? 48000),
                    })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Modèle GLM</Label>
                <Input
                  className="h-9 text-sm" placeholder="glm-4-flash"
                  value={cfg?.model ?? config.data?.model ?? ""}
                  onChange={(e) =>
                    setCfg({
                      max_concurrency: cfg?.max_concurrency ?? String(config.data?.max_concurrency ?? 25),
                      model: e.target.value,
                      max_chars: cfg?.max_chars ?? String(config.data?.max_chars ?? 48000),
                    })
                  }
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Budget caractères/décision</Label>
                <Input
                  className="h-9 text-sm" type="number" min={4000}
                  value={cfg?.max_chars ?? config.data?.max_chars ?? 48000}
                  onChange={(e) =>
                    setCfg({
                      max_concurrency: cfg?.max_concurrency ?? String(config.data?.max_concurrency ?? 25),
                      model: cfg?.model ?? config.data?.model ?? "",
                      max_chars: e.target.value,
                    })
                  }
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" onClick={saveConfig} disabled={busy}>
                <Save className="mr-1.5 h-3.5 w-3.5" /> Appliquer sans redémarrer
              </Button>
              {cfgSaved && <span className="text-xs text-success">✓ Le worker relit cette table à chaque décision.</span>}
              {config.error && <span className="text-xs text-destructive">{config.error}</span>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <Gauge className="h-4 w-4 text-primary" /> Benchmark de performance
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border px-3 py-2 text-sm">
              <span className="text-muted-foreground">Liste 100 décisions :</span>{" "}
              <b className="tabular-nums">{benchmark.data?.db_list_100_ms ?? "—"} ms</b>
            </div>
            <div className="rounded-md border px-3 py-2 text-sm">
              <span className="text-muted-foreground">Agrégats cockpit :</span>{" "}
              <b className="tabular-nums">{benchmark.data?.stats_overview_ms ?? "—"} ms</b>
            </div>
            <div className="rounded-md border px-3 py-2 text-sm">
              <span className="text-muted-foreground">Taille de la base :</span>{" "}
              <b className="tabular-nums">{benchmark.data?.db_size_mb ?? "—"} Mo</b>
            </div>
            <div className="rounded-md border px-3 py-2 text-sm">
              <span className="text-muted-foreground">Vitesse ingestion :</span>{" "}
              <b className="tabular-nums">{benchmark.data?.vitesse_par_minute ?? "—"}/min</b>
            </div>
            <div className="rounded-md border px-3 py-2 text-sm">
              <span className="text-muted-foreground">Fiches brutes conservées (raw_fiches) :</span>{" "}
              <b className="tabular-nums">{(benchmark.data?.raw_fiches ?? 0).toLocaleString("fr-FR")}</b>
              {benchmark.data?.raw_fiches_mb != null && (
                <span className="text-muted-foreground"> · {benchmark.data.raw_fiches_mb.toLocaleString("fr-FR")} Mo</span>
              )}
            </div>
          </CardContent>
        </Card>
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
                    <TableCell className="max-w-72 truncate font-mono text-xs">{a.url.split(/[\\/]/).pop()}</TableCell>
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
