"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI

from app.api import teams

app = FastAPI(title="TNC Model 2025", version="0.1.0")
app.include_router(teams.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
