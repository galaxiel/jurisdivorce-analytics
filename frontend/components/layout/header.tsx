"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Calculator, Compass, Library, Radio, Scale, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { useHealth } from "@/lib/api";
import { ThemeToggle } from "@/components/theme-toggle";

const LINKS = [
  { href: "/analytics", label: "Cockpit", icon: BarChart3 },
  { href: "/simulateur", label: "Mon Cas", icon: Compass },
  { href: "/decisions", label: "Jurisprudence", icon: Library },
  { href: "/calculateur", label: "Calculateur", icon: Calculator },
  { href: "/pieges", label: "Pièges", icon: ShieldAlert },
  { href: "/pipeline", label: "Pipeline", icon: Radio },
];

export function Header() {
  const pathname = usePathname();
  const { data: health } = useHealth();
  const healthy = health ? health.db_ok && health.disk_free_gb > 1 : null;

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Scale className="h-5 w-5" />
          </span>
          <span className="hidden sm:inline">
            JurisDivorce <span className="text-primary">Analytics</span>
          </span>
          {/* Chantier 3 : indicateur de santé discret (DB + disque) */}
          <span
            title={health ? `API : ${health.status} · ${health.decisions} décisions · ${health.disk_free_gb} Go libres · worker : ${health.worker_status}` : "Vérification…"}
            className={cn(
              "ml-1 h-2 w-2 rounded-full",
              healthy === null ? "bg-muted-foreground/40" : healthy ? "bg-success" : "bg-destructive",
            )}
          />
        </Link>

        <nav className="flex items-center gap-0.5">
          <Link
            href="/"
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2 py-2 text-sm font-medium transition-colors lg:px-3",
              pathname === "/" ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <span className="hidden md:inline">Accueil</span>
          </Link>
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2 py-2 text-sm font-medium transition-colors lg:px-3",
                  active ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden xl:inline">{label}</span>
              </Link>
            );
          })}
        </nav>

        <ThemeToggle />
      </div>
    </header>
  );
}
