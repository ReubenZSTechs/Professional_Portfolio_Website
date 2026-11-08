"""Vercel Python entrypoint. Vercel serves this FastAPI app for /api/py/* (see vercel.json).

The backend code lives in backend/src and is imported as top-level packages
(core, llm, rag, tools, agent), so that folder goes on sys.path first.
Locally: `npm run dev:api` (uvicorn api.index:app --reload --port 8000).
"""

import importlib
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Imported after the sys.path change above; Vercel serves the module-level `app`.
app = importlib.import_module("agent.main").app

__all__ = ["app"]
