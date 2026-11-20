"""Conftest pytest : expose `pipeline` (racine) et `app` (backend) à l'import."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

# Token admin pour les routes /api/pipeline/* (garde admin_guard, fail-closed)
os.environ.setdefault("JURISDIVORCE_ADMIN_TOKEN", "test-admin-token")

ADMIN_HEADERS = {"X-Admin-Token": os.environ["JURISDIVORCE_ADMIN_TOKEN"]}
