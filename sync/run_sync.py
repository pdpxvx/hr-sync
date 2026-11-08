"""Sincronització ERP -> Salesforce.

  python -m sync.run_sync              # incremental (només el que ha canviat)
  python -m sync.run_sync --full       # tot
  python -m sync.run_sync --dry-run    # sense tocar Salesforce

Estratègia: sempre es llegeix i es neteja TOT l'ERP (per poder detectar duplicats i
referències amb el context complet), però només s'envien els registres modificats
des de l'última sincronització correcta.
"""
from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from sync.cleaning import CleanResult, clean_all
from sync.salesforce import (DryRunTarget, SalesforceTarget, has_credentials, to_account,
                             to_candidate, to_placement)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output"
STATE_FILE = ROOT / "data" / "sync_state.json"

log = logging.getLogger("sync")


def fetch(erp_url: str) -> tuple[list, list, list]:
    def get(path):
        r = requests.get(f"{erp_url}/{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    return get("clients"), get("candidates"), get("placements")


def load_state() -> dict:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def write_report(res: CleanResult, results: dict, raw_counts: dict, mode: str,
                 started: str) -> Path:
    OUT_DIR.mkdir(exist_ok=True)
    by_action = Counter((i.entity, i.action) for i in res.issues)
    lines = [
        "# Informe de sincronització", "",
        f"- **Inici:** {started}", f"- **Mode:** {mode}", "",
        "## Volums", "",
        "| Entitat | Registres ERP | Després de netejar | Enviats | Creats | Actualitzats | Errors |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, sobject, clean in (("Clients", "Account", res.clients),
                                  ("Candidats", "Candidate__c", res.candidates),
                                  ("Contractes", "Placement__c", res.placements)):
        r = results.get(sobject, {})
        lines.append(f"| {label} | {raw_counts[sobject]} | {len(clean)} | {r.get('sent', 0)} | "
                     f"{r.get('created', 0)} | {r.get('updated', 0)} | {len(r.get('errors', []))} |")
    lines += ["", "## Qualitat de dades", "", "| Entitat | Acció | Casos |", "|---|---|---|"]
    lines += [f"| {e} | {a} | {n} |" for (e, a), n in sorted(by_action.items())]
    lines += ["", "## Detall d'incidències", "", "| Entitat | Id ERP | Camp | Problema | Acció |",
              "|---|---|---|---|---|"]
    lines += [f"| {i.entity} | {i.erp_id} | {i.field} | {i.problem} | {i.action} |"
              for i in res.issues]
    errors = [(s, e) for s, r in results.items() for e in r.get("errors", [])]
    if errors:
        lines += ["", "## Errors de Salesforce", ""]
        lines += [f"- `{s}` {e['erp_id']}: {e['errors']}" for s, e in errors]
    path = OUT_DIR / "sync_report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(description="Sincronitza l'ERP amb Salesforce")
    ap.add_argument("--erp-url", default="http://127.0.0.1:8000")
    ap.add_argument("--full", action="store_true", help="ignora l'última sincronització")
    ap.add_argument("--dry-run", action="store_true", help="no escriu a Salesforce")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dry_run = args.dry_run or not has_credentials()
    if dry_run and not args.dry_run:
        log.warning("No hi ha credencials de Salesforce a .env: s'executa en dry-run")
    state_key = "last_dry_run" if dry_run else "last_success"  # el dry-run no contamina l'estat real
    state = load_state()
    since = None if args.full else state.get(state_key)

    clients, candidates, placements = fetch(args.erp_url)
    log.info("ERP: %d clients, %d candidats, %d contractes",
             len(clients), len(candidates), len(placements))

    res = clean_all(clients, candidates, placements)
    log.info("Després de netejar: %d clients, %d candidats, %d contractes (%d incidències)",
             len(res.clients), len(res.candidates), len(res.placements), len(res.issues))

    # ">=" i no ">": si un canvi cau al mateix segon que l'última sincronització, es torna a
    # enviar. No passa res, perquè l'upsert per External ID és idempotent.
    changed = lambda rows: [r for r in rows if not since or r["updated_at"] >= since]  # noqa: E731
    payloads = {
        "Account": [to_account(c) for c in changed(res.clients)],
        "Candidate__c": [to_candidate(c) for c in changed(res.candidates)],
        "Placement__c": [to_placement(p) for p in changed(res.placements)],
    }

    target = DryRunTarget(OUT_DIR) if dry_run else SalesforceTarget()

    results = {}
    for sobject, records in payloads.items():  # l'ordre del dict respecta les dependències
        results[sobject] = target.upsert(sobject, records)
        r = results[sobject]
        log.info("%s: %d enviats, %d creats, %d actualitzats, %d errors", sobject, r["sent"],
                 r["created"], r["updated"], len(r["errors"]))

    mode = f"{target.name}, {'complet' if not since else f'incremental des de {since}'}"
    raw_counts = {"Account": len(clients), "Candidate__c": len(candidates),
                  "Placement__c": len(placements)}
    report = write_report(res, results, raw_counts, mode, started)
    log.info("Informe: %s", report.relative_to(ROOT))

    failed = any(r["errors"] for r in results.values())
    if not failed:
        state[state_key] = started  # només avança si tot ha anat bé
        save_state(state)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
