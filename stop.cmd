@echo off
title JurisDivorce Analytics - Arret
echo [ARRET] Fermeture de l'API (port 8000) et du site (port 3100)...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,3100 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Write-Host ('  - processus ' + $_ + ' arrete') }"
echo [OK] Serveurs arretes. Les fenetres cmd /k restent ouvertes : fermez-les manuellement.
pause
