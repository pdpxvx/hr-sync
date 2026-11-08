"""Genera dades de prova "brutes" a l'ERP, com les que es troben a la vida real.

Problemes que s'hi injecten a propòsit:
  - clients duplicats (mateix CIF, nom escrit diferent)
  - candidats duplicats (mateix NIF o mateix email amb majúscules/espais)
  - telèfons en 5 formats diferents, i alguns invàlids
  - NIFs amb la lletra de control incorrecta
  - emails mal formats
  - estats de contracte en català, castellà i anglès
  - dates en dos formats, i contractes amb data de fi anterior a la d'inici
  - contractes que apunten a clients que no existeixen
  - imports amb coma decimal

Executa:  python -m erp.seed
"""
import random
import unicodedata
from datetime import date, datetime, timedelta, timezone

from erp.db import DB_PATH, connect

NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
FIRST_NAMES = ["Anna", "Jordi", "Marta", "Pau", "Laia", "Marc", "Núria", "Oriol", "Clara", "Pol",
               "Júlia", "Arnau", "Paula", "Sergi", "Aina", "David", "Laura", "Àlex", "Carla", "Joan"]
LAST_NAMES = ["Puig", "Serra", "Vila", "Font", "Soler", "Roca", "Pujol", "Casas", "Riera", "Costa",
              "Garcia", "Martínez", "López", "Sala", "Ferrer", "Comas", "Planas", "Masó", "de la Fuente"]
CITIES = ["Girona", "Salt", "Figueres", "Olot", "Banyoles", "Blanes", "Lloret de Mar", "Palafrugell"]
COMPANIES = ["Industrias del Ter", "Logística Empordà", "Càrnies Garrotxa", "Plàstics Gironès",
             "Hotel Costa Brava", "Metal·lúrgica Fluvià", "Alimentària Selva", "Transports Onyar",
             "Embalatges Ripollès", "Química Baix Ter", "Fusteria Vall d'en Bas", "Tèxtil Besalú"]
POSITIONS = ["Operari/ària de producció", "Mosso/a de magatzem", "Carretoner/a", "Administratiu/va",
             "Cambrer/a de pisos", "Soldador/a", "Tècnic/a de manteniment", "Conductor/a C+E"]
STATUSES = ["Active", "ACTIVE", "actiu", "Activo", "closed", "Finalitzat", "Cerrado", "pending",
            "pendent", "???"]


def to_ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().replace(" ", "")


def nif_for(number: int) -> str:
    return f"{number:08d}{NIF_LETTERS[number % 23]}"


def cif_for(letter: str, number: int) -> str:
    d = [int(c) for c in f"{number:07d}"]
    even = d[1] + d[3] + d[5]
    odd = sum(sum(divmod(2 * d[i], 10)) for i in (0, 2, 4, 6))
    control = (10 - (even + odd) % 10) % 10
    return f"{letter}{number:07d}{control}"


def messy_phone(rng: random.Random, digits: str) -> str:
    fmt = rng.choice([
        lambda d: d,
        lambda d: f"+34 {d[:3]} {d[3:6]} {d[6:]}",
        lambda d: f"0034{d}",
        lambda d: f"{d[:3]}-{d[3:5]}-{d[5:7]}-{d[7:]}",
        lambda d: f"({d[:3]}) {d[3:]}",
    ])
    return fmt(digits)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def build(rng: random.Random):
    base_time = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    tick = lambda: iso(base_time + timedelta(minutes=rng.randint(0, 40_000)))  # noqa: E731

    clients = []
    for i, name in enumerate(COMPANIES, start=1):
        cif = cif_for(rng.choice("AB"), rng.randint(1_000_000, 9_999_999))
        clients.append({"id": f"CL-{i:03d}", "name": f"{name} SL", "cif": cif,
                        "city": rng.choice(CITIES), "updated_at": tick()})
    # Duplicats: mateix CIF, nom i format diferents
    for n, src in enumerate(rng.sample(clients, 3), start=len(clients) + 1):
        clients.append({"id": f"CL-{n:03d}", "name": src["name"].upper().replace(" SL", ", S.L."),
                        "cif": f"{src['cif'][0]}-{src['cif'][1:]}".lower(),
                        "city": f"  {src['city'].upper()} ", "updated_at": tick()})

    candidates = []
    for i in range(1, 61):
        fn, ln = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        phone_digits = rng.choice("67") + "".join(rng.choice("0123456789") for _ in range(8))
        nif = nif_for(rng.randint(10_000_000, 99_999_999))
        email = f"{to_ascii(fn)}.{to_ascii(ln)}{i}@example.com".lower()
        candidates.append({"id": f"CA-{i:03d}", "first_name": fn, "last_name": ln, "email": email,
                           "phone": messy_phone(rng, phone_digits), "nif": nif,
                           "city": rng.choice(CITIES), "updated_at": tick()})
    # Duplicats per NIF (nom en majúscules, telèfon en un altre format, sense email)
    n = len(candidates)
    for src in rng.sample(candidates, 5):
        n += 1
        digits = "".join(c for c in src["phone"] if c.isdigit())[-9:]
        candidates.append({**src, "id": f"CA-{n:03d}", "first_name": src["first_name"].upper(),
                           "last_name": src["last_name"].upper(), "email": "",
                           "phone": messy_phone(rng, digits), "nif": src["nif"].lower(),
                           "updated_at": tick()})
    # Duplicats per email (amb majúscules i espais, sense NIF)
    for src in rng.sample(candidates[:60], 3):
        n += 1
        candidates.append({**src, "id": f"CA-{n:03d}", "email": f"  {src['email'].upper()} ",
                           "nif": "", "updated_at": tick()})
    # Errors de qualitat
    for c in rng.sample(candidates[:60], 4):
        good = c["nif"]
        wrong = NIF_LETTERS[(NIF_LETTERS.index(good[-1]) + 1) % 23]
        c["nif"] = good[:-1] + wrong
    for c in rng.sample(candidates[:60], 2):
        c["email"] = c["email"].replace(".com", "")
    for c in rng.sample(candidates[:60], 2):
        c["phone"] = "12345"

    placements = []
    cand_ids = [c["id"] for c in candidates]
    client_ids = [c["id"] for c in clients]
    for i in range(1, 81):
        start = date(2026, 1, 1) + timedelta(days=rng.randint(0, 300))
        end = start + timedelta(days=rng.randint(14, 180))
        start_s = start.isoformat() if rng.random() < 0.7 else start.strftime("%d/%m/%Y")
        end_s = end.isoformat() if rng.random() < 0.7 else end.strftime("%d/%m/%Y")
        rate = round(rng.uniform(9.5, 18.0), 2)
        placements.append({
            "id": f"PL-{i:03d}", "client_id": rng.choice(client_ids),
            "candidate_id": rng.choice(cand_ids), "position": rng.choice(POSITIONS),
            "start_date": start_s, "end_date": end_s, "status": rng.choice(STATUSES),
            "hourly_rate": str(rate).replace(".", ",") if rng.random() < 0.4 else str(rate),
            "updated_at": tick(),
        })
    for p in rng.sample(placements, 3):  # data de fi anterior a la d'inici
        p["start_date"], p["end_date"] = "2026-06-30", "2026-06-01"
    for p in rng.sample(placements, 2):  # client inexistent
        p["client_id"] = "CL-999"

    return clients, candidates, placements


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()
    rng = random.Random(42)  # determinista: sempre les mateixes dades
    clients, candidates, placements = build(rng)
    with connect() as conn:
        for table, rows in (("clients", clients), ("candidates", candidates),
                            ("placements", placements)):
            cols = list(rows[0].keys())
            conn.executemany(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                [tuple(r[c] for c in cols) for r in rows],
            )
    print(f"ERP creat a {DB_PATH}: {len(clients)} clients, {len(candidates)} candidats, "
          f"{len(placements)} contractes")


if __name__ == "__main__":
    main()
