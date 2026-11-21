"""Aspirateur multi-fonds Open Data DILA / Judilibre : CAPP, CASS, TJ (et autres).

Étape 1.1 du cahier des charges : parcourt récursivement l'index HTML public de
`echanges.dila.gouv.fr/OPENDATA/` (dossiers fonds : `CAPP/`, `CASS/`, `TJ/` →
archives `.tar.gz` / `.zip`), découvre TOUTES les archives — dont le dump global
du Cours d'appel — et télécharge en flux vers `archives/` (dossier dédié aux
données non fiables, jamais dans le code).

Structure réelle vérifiée en ligne :
  /OPENDATA/CAPP/Freemium_capp_global_YYYYMMDD-HHMMSS.tar.gz (~292 Mo, XML JURI)
L'URL de base est configurable : `JUDILIBRE_OPENDATA_URL`.
"""
import asyncio
import os
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urljoin

import httpx

HREF_RE = re.compile(r'href="([^"?#]+)"', re.IGNORECASE)
ARCHIVE_RE = re.compile(r"\.(tar\.gz|tgz|zip)$", re.IGNORECASE)
KNOWN_FONDS = ("CAPP", "CASS", "INCA", "TJ", "TGE", "TC", "TGO", "CPH", "TOM")
DEFAULT_OPENDATA_URL = "https://echanges.dila.gouv.fr/OPENDATA/"


def fonds_from_path(url: str) -> str:
    """Fonds = segment de chemin (CAPP/…) ou nom du fichier (…_capp_global_…)."""
    path = unquote(url)
    for segment in path.split("/"):
        upper = segment.upper()
        for fonds in KNOWN_FONDS:
            if upper == fonds or upper.startswith(fonds + "_"):
                return fonds
    basename = path.split("/")[-1].split("?")[0]
    for fonds in KNOWN_FONDS:
        if fonds.lower() in basename.lower():
            return fonds
    return "AUTRE"


async def list_archives(client: httpx.AsyncClient, base_url: str,
                        fonds_filter: Optional[List[str]] = None,
                        max_archives: Optional[int] = None,
                        max_depth: int = 4, log=print) -> List[Dict[str, str]]:
    """Parcours BFS de l'index de fichiers publics ; retourne {url, fonds}.

    Avec un filtre de fonds, on n'explore que les répertoires dont le chemin
    contient un fonds cible — évite de crawler les dossiers LEGI/LODECIM etc.
    """
    found: Dict[str, Dict[str, str]] = {}
    seen_dirs: set = set()
    queue: List[Tuple[str, int]] = [(base_url, 0)]

    while queue and (max_archives is None or len(found) < max_archives):
        url, depth = queue.pop(0)
        if url in seen_dirs or depth > max_depth:
            continue
        seen_dirs.add(url)
        try:
            response = await client.get(url, timeout=60)
            response.raise_for_status()
        except Exception as exc:  # un sous-répertoire manquant ne bloque pas la campagne
            log(f"[WARN] Index illisible {url} : {exc}")
            continue
        for href in HREF_RE.findall(response.text):
            link = urljoin(url, href)
            if link.endswith("/"):
                if fonds_filter and not any(
                    f.lower() in unquote(link).lower() for f in fonds_filter
                ):
                    continue  # répertoire hors fonds cibles
                queue.append((link, depth + 1))
            elif ARCHIVE_RE.search(link):
                fonds = fonds_from_path(link)
                if fonds_filter and fonds not in fonds_filter:
                    continue
                if link not in found:
                    found[link] = {"url": link, "fonds": fonds}
        await asyncio.sleep(0)

    archives = list(found.values())
    if max_archives:
        archives = archives[:max_archives]

    # Tri par date (dans le nom de fichier) puis taille — HEAD pour obtenir la taille
    await _enrich_sizes(client, archives, log)
    archives.sort(key=_archive_sort_key, reverse=True)
    total_mb = round(sum(a.get("size_bytes") or 0 for a in archives) / 1e6, 1)
    log(f"[INDEX] {len(archives)} archives découvertes sur {base_url} ({total_mb} Mo au total, "
        f"triées par date puis taille)")
    return archives


_TIMESTAMP = re.compile(r"(\d{8})-?(\d{4})?")


def _archive_sort_key(archive: dict):
    m = _TIMESTAMP.search(archive["url"])
    stamp = (m.group(1) + m.group(2)) if m else "0"
    return (stamp, archive.get("size_bytes") or 0)


async def _enrich_sizes(client: httpx.AsyncClient, archives: List[dict], log=print) -> None:
    for archive in archives:
        try:
            response = await client.head(archive["url"], timeout=30, follow_redirects=True)
            archive["size_bytes"] = int(response.headers.get("content-length", 0) or 0)
        except Exception:
            archive["size_bytes"] = 0


async def download_archive(client: httpx.AsyncClient, url: str, dest_dir: str, log=print) -> Tuple[str, int]:
    """Téléchargement en flux (chunks de 1 Mo) — n'extrait JAMAIS dans le code."""
    os.makedirs(dest_dir, exist_ok=True)
    name = unquote(url.split("/")[-1].split("?")[0]) or "archive.tar.gz"
    path = os.path.join(dest_dir, name)
    total = 0
    async with client.stream("GET", url, timeout=None) as response:
        response.raise_for_status()
        with open(path, "wb") as file:
            async for chunk in response.aiter_bytes(1 << 20):
                file.write(chunk)
                total += len(chunk)
    log(f"[DOWNLOAD] {name} ({total / 1e6:.1f} Mo)")
    return path, total
