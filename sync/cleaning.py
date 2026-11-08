"""Neteja, validació i deduplicació de les dades de l'ERP abans d'enviar-les a Salesforce.

Tot són funcions pures (sense xarxa ni BD) perquè es puguin provar fàcilment amb pytest.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
NAME_PARTICLES = {"de", "del", "la", "i", "y", "da"}

STATUS_MAP = {
    "active": "Active", "actiu": "Active", "activo": "Active",
    "closed": "Closed", "finalitzat": "Closed", "cerrado": "Closed",
    "pending": "Pending", "pendent": "Pending", "pendiente": "Pending",
}


@dataclass
class Issue:
    entity: str
    erp_id: str
    field: str
    problem: str
    action: str


@dataclass
class CleanResult:
    clients: list[dict] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)
    placements: list[dict] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    merged: dict[str, str] = field(default_factory=dict)  # id duplicat -> id mestre


# ---------- Normalitzadors de camps ----------

def normalize_phone(raw: str | None) -> str | None:
    """Retorna el telèfon en format E.164 (+34XXXXXXXXX) o None si no és vàlid."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0034"):
        digits = digits[4:]
    elif digits.startswith("34") and len(digits) == 11:
        digits = digits[2:]
    if len(digits) == 9 and digits[0] in "6789":
        return f"+34{digits}"
    return None


def normalize_email(raw: str | None) -> str | None:
    if not raw:
        return None
    email = raw.strip().lower()
    return email if EMAIL_RE.match(email) else None


def normalize_id_doc(raw: str | None) -> str:
    """Treu espais, guions i punts d'un NIF/NIE/CIF i el passa a majúscules."""
    return re.sub(r"[\s.\-]", "", raw or "").upper()


def is_valid_nif(doc: str) -> bool:
    """Valida DNI (12345678Z) i NIE (X1234567L) amb la lletra de control."""
    m = re.fullmatch(r"([XYZ]?)(\d{7,8})([A-Z])", doc)
    if not m:
        return False
    prefix, number, letter = m.groups()
    if prefix:
        number = str("XYZ".index(prefix)) + number
    return NIF_LETTERS[int(number) % 23] == letter


def is_valid_cif(doc: str) -> bool:
    """Valida un CIF d'empresa (lletra + 7 dígits + control)."""
    m = re.fullmatch(r"([ABCDEFGHJNPQRSUVW])(\d{7})([0-9A-J])", doc)
    if not m:
        return False
    letter, digits, control = m.groups()
    d = [int(c) for c in digits]
    even = d[1] + d[3] + d[5]
    odd = sum(sum(divmod(2 * d[i], 10)) for i in (0, 2, 4, 6))
    expected = (10 - (even + odd) % 10) % 10
    expected_letter = "JABCDEFGHI"[expected]
    if letter in "ABEH":
        return control == str(expected)
    if letter in "KPQS":
        return control == expected_letter
    return control in (str(expected), expected_letter)


def normalize_name(raw: str | None) -> str:
    words = re.sub(r"\s+", " ", (raw or "").strip()).split(" ")
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        is_particle = lw in NAME_PARTICLES or lw.startswith(("d'", "l'"))
        out.append(lw if i > 0 and is_particle else lw[:1].upper() + lw[1:])
    return " ".join(out)


def normalize_company(raw: str | None) -> str:
    name = re.sub(r"\s+", " ", (raw or "").strip())
    name = re.sub(r"(?:,\s*|\s+)S\.?\s*L\.?\s*U?\.?$", " SL", name, flags=re.IGNORECASE)
    name = re.sub(r"(?:,\s*|\s+)S\.?\s*A\.?$", " SA", name, flags=re.IGNORECASE)
    base, _, suffix = name.rpartition(" ") if name.endswith((" SL", " SA")) else (name, "", "")
    return f"{normalize_name(base)} {suffix}".strip()


def parse_date(raw: str | None) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime((raw or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw: str | None) -> float | None:
    try:
        return round(float(str(raw).replace(",", ".")), 2)
    except (TypeError, ValueError):
        return None


# ---------- Neteja per entitat ----------

def _merge_into(master: dict, dup: dict) -> None:
    """Omple els camps buits del registre mestre amb els del duplicat."""
    for k, v in dup.items():
        if master.get(k) in (None, "") and v not in (None, ""):
            master[k] = v


def _finalize_groups(masters: list[dict], entity: str, res: CleanResult) -> list[dict]:
    """Cada grup de duplicats conserva l'id ERP més antic (identitat estable a Salesforce),
    però amb els valors del registre modificat més recentment."""
    for rec in masters:
        group = rec.pop("_group")
        kinds = rec.pop("_kinds", {})
        canonical = min(group)
        rec["erp_id"] = canonical
        for other in sorted(group):
            if other != canonical:
                res.merged[other] = canonical
                res.issues.append(Issue(entity, other, kinds.get(other, "?"),
                                        f"duplicat de {canonical}", "fusionat"))
    return sorted(masters, key=lambda r: r["erp_id"])


def clean_clients(raw: list[dict], res: CleanResult) -> None:
    by_cif: dict[str, dict] = {}
    # Es processa del més recent al més antic: el primer de cada grup aporta els valors
    for r in sorted(raw, key=lambda r: r["updated_at"], reverse=True):
        cif = normalize_id_doc(r["cif"])
        rec = {"erp_id": r["id"], "name": normalize_company(r["name"]), "cif": cif,
               "city": normalize_name(r["city"]), "updated_at": r["updated_at"]}
        if not is_valid_cif(cif):
            res.issues.append(Issue("client", r["id"], "cif", f"CIF invàlid: {r['cif']!r}",
                                    "marcat per revisar"))
        if cif in by_cif:
            master = by_cif[cif]
            _merge_into(master, rec)
            master["_group"].append(r["id"])
            kinds = master.setdefault("_kinds", {})
            kinds[r["id"]] = "cif"
            kinds.setdefault(master["erp_id"], "cif")
            continue
        rec["_group"] = [r["id"]]
        by_cif[cif] = rec
    res.clients = _finalize_groups(list(by_cif.values()), "client", res)


def clean_candidates(raw: list[dict], res: CleanResult) -> None:
    masters: list[dict] = []
    index: dict[tuple, dict] = {}  # ("nif", x) / ("email", x) / ("name_phone", x) -> mestre
    for r in sorted(raw, key=lambda r: r["updated_at"], reverse=True):
        nif = normalize_id_doc(r["nif"])
        email = normalize_email(r["email"])
        phone = normalize_phone(r["phone"])
        needs_review = False
        if r["email"] and r["email"].strip() and not email:
            res.issues.append(Issue("candidate", r["id"], "email",
                                    f"email invàlid: {r['email'].strip()!r}", "descartat"))
            needs_review = True
        if r["phone"] and not phone:
            res.issues.append(Issue("candidate", r["id"], "phone",
                                    f"telèfon invàlid: {r['phone']!r}", "descartat"))
            needs_review = True
        nif_ok = is_valid_nif(nif)
        if nif and not nif_ok:
            res.issues.append(Issue("candidate", r["id"], "nif", f"NIF invàlid: {r['nif']!r}",
                                    "marcat per revisar"))
            needs_review = True

        rec = {"erp_id": r["id"], "first_name": normalize_name(r["first_name"]),
               "last_name": normalize_name(r["last_name"]), "email": email, "phone": phone,
               "nif": nif or None, "city": normalize_name(r["city"]),
               "needs_review": needs_review, "updated_at": r["updated_at"]}

        # Claus de coincidència, de la més fiable a la menys
        keys = []
        if nif_ok:
            keys.append(("nif", nif))
        if email:
            keys.append(("email", email))
        if phone:
            keys.append(("name_phone", f"{rec['first_name']} {rec['last_name']}|{phone}".lower()))

        match = next(((k, index[k]) for k in keys if k in index), None)
        if match:
            (kind, _), master = match
            _merge_into(master, rec)
            if nif_ok and not is_valid_nif(master["nif"] or ""):
                master["nif"] = nif  # un NIF vàlid guanya sobre un d'invàlid, sigui més antic o no
            master["needs_review"] = master["needs_review"] or needs_review
            master["_group"].append(r["id"])
            kinds = master.setdefault("_kinds", {})
            kinds[r["id"]] = kind
            kinds.setdefault(master["erp_id"], kind)
            target = master
        else:
            rec["_group"] = [r["id"]]
            masters.append(rec)
            target = rec
        for k in keys:  # el duplicat pot aportar claus noves al grup
            index.setdefault(k, target)
    res.candidates = _finalize_groups(masters, "candidate", res)


def clean_placements(raw: list[dict], res: CleanResult) -> None:
    client_ids = {c["erp_id"] for c in res.clients}
    candidate_ids = {c["erp_id"] for c in res.candidates}
    for r in raw:
        pid = r["id"]
        client_id = res.merged.get(r["client_id"], r["client_id"])
        candidate_id = res.merged.get(r["candidate_id"], r["candidate_id"])
        if client_id not in client_ids:
            res.issues.append(Issue("placement", pid, "client_id",
                                    f"client inexistent: {r['client_id']}", "rebutjat"))
            continue
        if candidate_id not in candidate_ids:
            res.issues.append(Issue("placement", pid, "candidate_id",
                                    f"candidat inexistent: {r['candidate_id']}", "rebutjat"))
            continue
        start, end = parse_date(r["start_date"]), parse_date(r["end_date"])
        if not start:
            res.issues.append(Issue("placement", pid, "start_date",
                                    f"data invàlida: {r['start_date']!r}", "rebutjat"))
            continue
        if end and end < start:
            res.issues.append(Issue("placement", pid, "end_date",
                                    f"fi ({end}) anterior a l'inici ({start})", "rebutjat"))
            continue
        status = STATUS_MAP.get((r["status"] or "").strip().lower())
        if not status:
            res.issues.append(Issue("placement", pid, "status",
                                    f"estat desconegut: {r['status']!r}", "posat a Pending"))
            status = "Pending"
        res.placements.append({
            "erp_id": pid, "client_id": client_id, "candidate_id": candidate_id,
            "position": r["position"], "start_date": start.isoformat(),
            "end_date": end.isoformat() if end else None, "status": status,
            "hourly_rate": parse_amount(r["hourly_rate"]), "updated_at": r["updated_at"],
        })


def clean_all(clients: list[dict], candidates: list[dict], placements: list[dict]) -> CleanResult:
    res = CleanResult()
    clean_clients(clients, res)
    clean_candidates(candidates, res)
    clean_placements(placements, res)  # depèn dels anteriors per resoldre duplicats
    return res
