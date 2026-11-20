# 🔒 Administration du pipeline (`/pipeline`) — procédure

La page `/pipeline` et toutes les routes `/api/pipeline/*` sont protégées par
la **Règle d'Or N°7** (voir `AGENTS.md`) : en-tête `X-Admin-Token` obligatoire,
égal à la variable d'environnement `JURISDIVORCE_ADMIN_TOKEN` (garde
`admin_guard` dans `backend/app/routers/pipeline.py`, **fail-closed** : variable
absente → 404 sur tout `/api/pipeline/*`).

## Utilisation

1. Ouvrir `/pipeline` (URL directe — la page n'est plus dans la navbar ni sur l'accueil).
2. Saisir le token admin dans l'écran « Accès réservé » → **Déverrouiller**.
3. Le navigateur le conserve en `localStorage` (clé `jd_admin_token`) : plus besoin
   de le ressaisir. Bouton **Verrouiller** pour l'effacer du navigateur.

## Où est le token (local, jamais committé)

- `backend/.env` → `JURISDIVORCE_ADMIN_TOKEN=...` (gitignoré)
- `backend/.env.ADMIN.md` → notes locales avec la valeur courante + cette
  procédure (gitignoré via le pattern `.env.*`)

## Régénérer le token (perdu ou compromis)

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# → remplacer la valeur dans backend/.env, puis redémarrer le backend :
powershell.exe -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,8100 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000   # dev
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8100   # tunnel/static
# → re-saisir le nouveau token dans /pipeline
```

## Vérification rapide (garde active)

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/pipeline/state                              # 404
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Admin-Token: faux" http://127.0.0.1:8000/api/pipeline/state      # 404
TOKEN=$(grep JURISDIVORCE_ADMIN_TOKEN backend/.env | cut -d= -f2)
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Admin-Token: $TOKEN" http://127.0.0.1:8000/api/pipeline/state      # 200
```

## Règles

- ❌ Ne jamais committer `backend/.env` ni `backend/.env.ADMIN.md` (déjà gitignorés).
- ❌ Ne jamais remettre `/pipeline` dans la navbar (`header.tsx`) ou l'accueil (`page.tsx`).
- ❌ Ne jamais retirer `Depends(admin_guard)` du routeur pipeline.
- ✅ Si `JURISDIVORCE_ADMIN_TOKEN` n'est pas définie, tout `/api/pipeline/*` renvoie 404 (fail-closed).
