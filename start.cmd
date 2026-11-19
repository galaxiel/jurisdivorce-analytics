@echo off
setlocal
title JurisDivorce Analytics - Lanceur
set ROOT=%~dp0
set FRONT_PORT=3100

echo ============================================================
echo   JurisDivorce Analytics - demarrage local
echo   API  : http://127.0.0.1:8000
echo   Site : http://localhost:%FRONT_PORT%
echo ============================================================
echo.

rem --- Verifications prealables ---
where python >nul 2>nul || (echo [ERREUR] Python introuvable dans le PATH. Installez Python 3.11+ & pause & exit /b 1)
where node >nul 2>nul || (echo [ERREUR] Node.js introuvable dans le PATH. Installez Node 18+ & pause & exit /b 1)

rem --- Backend : generation des donnees de demonstration si la base est absente ---
if not exist "%ROOT%backend\jurisprudence.db" (
  echo [BACKEND] Premiere fois : generation des donnees de demonstration...
  pushd "%ROOT%backend"
  python -m app.seed
  popd
)

rem --- Frontend : installation des dependances si necessaire ---
if not exist "%ROOT%frontend\node_modules" (
  echo [FRONTEND] Premiere fois : installation des dependances npm, 1 a 2 minutes...
  pushd "%ROOT%frontend"
  call npm install --no-audit --no-fund
  popd
)

echo [DEMARRAGE] Ouverture de deux fenetres : API + Site. Laissez-les ouvertes.
echo [INFO] Pour tout arreter : lancez stop.cmd ou fermez les deux fenetres.
echo.

rem --- API dans sa propre fenetre ---
start "JurisDivorce API" cmd /k "cd /d %ROOT%backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

rem --- Attendre que l'API reponde ---
set /a tries=0
:waitapi
set /a tries+=1
curl -s -o nul --max-time 3 http://127.0.0.1:8000/api/health && goto apiready
if %tries% GEQ 30 goto apiready
timeout /t 1 /nobreak >nul
goto waitapi
:apiready
echo [OK] API prete sur le port 8000.

rem --- Site dans sa propre fenetre (mode dev : toujours a jour) ---
start "JurisDivorce Site" cmd /k "cd /d %ROOT%frontend && npm run dev -- -p %FRONT_PORT%"

rem --- Attendre que le site reponde puis ouvrir le navigateur ---
set /a tries=0
:waitfront
set /a tries+=1
curl -s -o nul --max-time 30 http://127.0.0.1:%FRONT_PORT% && goto ready
if %tries% GEQ 45 goto ready
timeout /t 2 /nobreak >nul
goto waitfront
:ready
start "" http://localhost:%FRONT_PORT%
echo.
echo ============================================================
echo   [OK] JurisDivorce Analytics est pret :
echo        http://localhost:%FRONT_PORT%
echo   La premiere page peut prendre 10-20 s a compiler.
echo ============================================================
pause
