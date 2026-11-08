from sync.salesforce import SalesforceTarget, to_placement


def test_placement_uses_external_id_relationships():
    payload = to_placement({"erp_id": "PL-1", "client_id": "CL-1", "candidate_id": "CA-1",
                            "position": "Operari", "start_date": "2026-03-01",
                            "end_date": None, "status": "Active", "hourly_rate": 11.5,
                            "updated_at": "x"})
    assert payload["Account__r"] == {"ERP_Id__c": "CL-1"}
    assert payload["Candidate__r"] == {"ERP_Id__c": "CA-1"}
    assert "Account__c" not in payload


class FakeBulkObject:
    def upsert(self, records, external_id, batch_size):
        assert external_id == "ERP_Id__c"
        return [{"success": True, "created": True},
                {"success": True, "created": False},
                {"success": False, "errors": [{"message": "REQUIRED_FIELD_MISSING"}]}]


class FakeSF:
    class bulk:
        Account = FakeBulkObject()


def test_upsert_summary_counts_created_updated_and_errors():
    target = SalesforceTarget.__new__(SalesforceTarget)  # sense connectar a Salesforce
    target.sf = FakeSF()
    out = target.upsert("Account", [{"ERP_Id__c": "A"}, {"ERP_Id__c": "B"}, {"ERP_Id__c": "C"}])
    assert (out["created"], out["updated"]) == (1, 1)
    assert out["errors"][0]["erp_id"] == "C"
