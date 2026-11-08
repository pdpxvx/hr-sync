"""API REST mínima de l'ERP.

Executa:  uvicorn erp.api:app --reload
Docs:     http://127.0.0.1:8000/docs
"""
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from erp.db import TABLES, connect

app = FastAPI(title="Mini ERP", description="ERP simulat d'una empresa de treball temporal")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _list(table: str, updated_since: str | None):
    if table not in TABLES:  # llista blanca: res d'SQL dinàmic amb input de l'usuari
        raise HTTPException(404)
    with connect() as conn:
        if updated_since:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE updated_at > ? ORDER BY id", (updated_since,)
            ).fetchall()
        else:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@app.get("/health")
def health():
    return {"status": "ok", "time": _now()}


@app.get("/clients")
def clients(updated_since: str | None = None):
    return _list("clients", updated_since)


@app.get("/candidates")
def candidates(updated_since: str | None = None):
    return _list("candidates", updated_since)


@app.get("/placements")
def placements(updated_since: str | None = None):
    return _list("placements", updated_since)


class CandidatePatch(BaseModel):
    email: str | None = None
    phone: str | None = None
    city: str | None = None


@app.patch("/candidates/{candidate_id}")
def update_candidate(candidate_id: str, patch: CandidatePatch):
    """Permet simular un canvi a l'ERP per provar la sincronització incremental."""
    changes = patch.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(400, "Cap camp per actualitzar")
    changes["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in changes)  # claus fixades pel model Pydantic
    with connect() as conn:
        cur = conn.execute(
            f"UPDATE candidates SET {cols} WHERE id = ?", (*changes.values(), candidate_id)
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Candidat no trobat")
        row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
    return dict(row)
