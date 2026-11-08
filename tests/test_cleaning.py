import pytest

from sync.cleaning import (clean_all, is_valid_cif, is_valid_nif, normalize_company,
                           normalize_email, normalize_name, normalize_phone, parse_amount)


@pytest.mark.parametrize("raw", ["612345678", "+34 612 345 678", "0034612345678",
                                 "612-34-56-78", "(612) 345678", "34612345678"])
def test_phone_formats_are_normalized(raw):
    assert normalize_phone(raw) == "+34612345678"


@pytest.mark.parametrize("raw", ["12345", "512345678", "", None, "+44 20 7946 0958"])
def test_invalid_phones(raw):
    assert normalize_phone(raw) is None


def test_email():
    assert normalize_email("  Anna.Puig@Example.COM ") == "anna.puig@example.com"
    assert normalize_email("anna.puig@example") is None


@pytest.mark.parametrize("doc,ok", [("12345678Z", True), ("12345678A", False),
                                    ("X1234567L", True), ("X1234567T", False), ("ABC", False)])
def test_nif(doc, ok):
    assert is_valid_nif(doc) is ok


def test_cif():
    assert is_valid_cif("B12345674")
    assert not is_valid_cif("B12345675")


def test_names():
    assert normalize_name("  JOAN   DE LA FUENTE ") == "Joan de la Fuente"
    assert normalize_company("INDUSTRIAS DEL TER, S.L.") == "Industrias del Ter SL"
    assert normalize_company("Hotel Costa Brava sl") == "Hotel Costa Brava SL"


def test_amount_with_decimal_comma():
    assert parse_amount("12,50") == 12.5
    assert parse_amount("abc") is None


def _cand(id_, updated, **kw):
    base = {"id": id_, "first_name": "Anna", "last_name": "Puig", "email": "",
            "phone": "", "nif": "", "city": "Girona", "updated_at": updated}
    return {**base, **kw}


def test_duplicates_keep_oldest_id_and_newest_values():
    res = clean_all(
        [],
        [_cand("CA-001", "2026-01-01", nif="12345678Z", phone="612345678", city="Salt"),
         _cand("CA-009", "2026-05-01", nif="12345678-z", email="ANNA@EXAMPLE.COM")],
        [],
    )
    assert len(res.candidates) == 1
    c = res.candidates[0]
    assert c["erp_id"] == "CA-001"            # identitat estable
    assert c["city"] == "Girona"              # valor del registre més recent
    assert c["email"] == "anna@example.com"   # aportat pel duplicat
    assert c["phone"] == "+34612345678"       # aportat per l'original
    assert res.merged == {"CA-009": "CA-001"}


def test_valid_nif_wins_over_invalid_one():
    res = clean_all([], [_cand("CA-001", "2026-05-01", nif="12345678A", phone="612345678"),
                         _cand("CA-002", "2026-01-01", nif="12345678Z", phone="612345678")], [])
    assert res.candidates[0]["nif"] == "12345678Z"
    assert res.candidates[0]["needs_review"] is True


def test_placements_follow_merged_ids_and_reject_bad_rows():
    clients = [{"id": "CL-1", "name": "Acme SL", "cif": "B12345674", "city": "Girona",
                "updated_at": "2026-01-01"}]
    candidates = [_cand("CA-1", "2026-01-01", nif="12345678Z"),
                  _cand("CA-2", "2026-02-01", nif="12345678Z")]
    row = {"client_id": "CL-1", "position": "Operari", "hourly_rate": "11,5",
           "updated_at": "2026-03-01"}
    placements = [
        {**row, "id": "PL-1", "candidate_id": "CA-2", "start_date": "01/03/2026",
         "end_date": "2026-04-01", "status": "actiu"},
        {**row, "id": "PL-2", "candidate_id": "CA-1", "start_date": "2026-06-30",
         "end_date": "2026-06-01", "status": "Active"},
        {**row, "id": "PL-3", "candidate_id": "CA-1", "client_id": "CL-999",
         "start_date": "2026-01-01", "end_date": "", "status": "Active"},
    ]
    res = clean_all(clients, candidates, placements)
    assert [p["erp_id"] for p in res.placements] == ["PL-1"]
    p = res.placements[0]
    assert p["candidate_id"] == "CA-1"   # redirigit al mestre
    assert p["start_date"] == "2026-03-01"
    assert p["status"] == "Active"
    assert p["hourly_rate"] == 11.5
    rejected = {i.erp_id for i in res.issues if i.action == "rebutjat"}
    assert rejected == {"PL-2", "PL-3"}
