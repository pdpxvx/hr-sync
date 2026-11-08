"""Mapeig ERP -> Salesforce i destinacions d'escriptura (Salesforce real o dry-run)."""
from __future__ import annotations

import json
import os
from pathlib import Path

EXTERNAL_ID = "ERP_Id__c"

# Ordre important: els contractes referencien comptes i candidats, que han d'existir abans
SOBJECT_ORDER = ("Account", "Candidate__c", "Placement__c")


def to_account(c: dict) -> dict:
    return {EXTERNAL_ID: c["erp_id"], "Name": c["name"], "CIF__c": c["cif"],
            "BillingCity": c["city"]}


def to_candidate(c: dict) -> dict:
    # Status__c NO s'envia: el gestiona el Flow de Salesforce, no l'ERP
    return {EXTERNAL_ID: c["erp_id"], "Name": f"{c['first_name']} {c['last_name']}",
            "Email__c": c["email"], "Phone__c": c["phone"], "NIF__c": c["nif"],
            "City__c": c["city"], "Needs_Review__c": c["needs_review"]}


def to_placement(p: dict) -> dict:
    # Les relacions es resolen per External ID: no cal saber l'Id intern de Salesforce
    return {EXTERNAL_ID: p["erp_id"],
            "Account__r": {EXTERNAL_ID: p["client_id"]},
            "Candidate__r": {EXTERNAL_ID: p["candidate_id"]},
            "Position__c": p["position"], "Start_Date__c": p["start_date"],
            "End_Date__c": p["end_date"], "Status__c": p["status"],
            "Hourly_Rate__c": p["hourly_rate"]}


class DryRunTarget:
    """No toca Salesforce: escriu el que s'enviaria a output/<objecte>.json."""

    name = "dry-run"

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

    def upsert(self, sobject: str, records: list[dict]) -> dict:
        path = self.out_dir / f"{sobject}.json"
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"sent": len(records), "created": 0, "updated": 0, "errors": []}


class SalesforceTarget:
    """Escriu a Salesforce amb la Bulk API, fent upsert per External ID."""

    name = "salesforce"

    def __init__(self):
        from simple_salesforce import Salesforce  # import tardà: el dry-run no ho necessita

        if os.getenv("SF_CONSUMER_KEY"):
            # OAuth Client Credentials (app connectada). SF_DOMAIN = "elteudomini.my"
            self.sf = Salesforce(consumer_key=os.environ["SF_CONSUMER_KEY"],
                                 consumer_secret=os.environ["SF_CONSUMER_SECRET"],
                                 domain=os.environ["SF_DOMAIN"])
        else:
            self.sf = Salesforce(username=os.environ["SF_USERNAME"],
                                 password=os.environ["SF_PASSWORD"],
                                 security_token=os.environ["SF_SECURITY_TOKEN"],
                                 domain=os.getenv("SF_DOMAIN", "login"))

    def upsert(self, sobject: str, records: list[dict]) -> dict:
        if not records:
            return {"sent": 0, "created": 0, "updated": 0, "errors": []}
        results = getattr(self.sf.bulk, sobject).upsert(records, EXTERNAL_ID, batch_size=2000)
        summary = {"sent": len(records), "created": 0, "updated": 0, "errors": []}
        for rec, res in zip(records, results):
            if res.get("success"):
                summary["created" if res.get("created") else "updated"] += 1
            else:
                summary["errors"].append({"erp_id": rec[EXTERNAL_ID], "errors": res.get("errors")})
        return summary


def has_credentials() -> bool:
    return bool(os.getenv("SF_CONSUMER_KEY") or os.getenv("SF_USERNAME"))
