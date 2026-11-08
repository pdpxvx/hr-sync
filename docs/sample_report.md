# Informe de sincronització

- **Inici:** 2026-11-08T22:23:47+00:00
- **Mode:** dry-run, complet

## Volums

| Entitat | Registres ERP | Després de netejar | Enviats | Creats | Actualitzats | Errors |
|---|---|---|---|---|---|---|
| Clients | 15 | 12 | 12 | 0 | 0 | 0 |
| Candidats | 68 | 60 | 60 | 0 | 0 | 0 |
| Contractes | 80 | 75 | 75 | 0 | 0 | 0 |

## Qualitat de dades

| Entitat | Acció | Casos |
|---|---|---|
| candidate | descartat | 4 |
| candidate | fusionat | 8 |
| candidate | marcat per revisar | 4 |
| client | fusionat | 3 |
| placement | posat a Pending | 9 |
| placement | rebutjat | 5 |

## Detall d'incidències

| Entitat | Id ERP | Camp | Problema | Acció |
|---|---|---|---|---|
| client | CL-014 | cif | duplicat de CL-011 | fusionat |
| client | CL-015 | cif | duplicat de CL-004 | fusionat |
| client | CL-013 | cif | duplicat de CL-001 | fusionat |
| candidate | CA-036 | phone | telèfon invàlid: '12345' | descartat |
| candidate | CA-010 | nif | NIF invàlid: '38754377E' | marcat per revisar |
| candidate | CA-031 | email | email invàlid: 'anna.font31@example' | descartat |
| candidate | CA-023 | email | email invàlid: 'sergi.puig23@example' | descartat |
| candidate | CA-035 | nif | NIF invàlid: '90967191F' | marcat per revisar |
| candidate | CA-022 | phone | telèfon invàlid: '12345' | descartat |
| candidate | CA-029 | nif | NIF invàlid: '51663795T' | marcat per revisar |
| candidate | CA-056 | nif | NIF invàlid: '64807553V' | marcat per revisar |
| candidate | CA-062 | nif | duplicat de CA-025 | fusionat |
| candidate | CA-066 | email | duplicat de CA-047 | fusionat |
| candidate | CA-067 | email | duplicat de CA-020 | fusionat |
| candidate | CA-061 | name_phone | duplicat de CA-010 | fusionat |
| candidate | CA-068 | email | duplicat de CA-054 | fusionat |
| candidate | CA-063 | nif | duplicat de CA-013 | fusionat |
| candidate | CA-065 | nif | duplicat de CA-039 | fusionat |
| candidate | CA-064 | nif | duplicat de CA-059 | fusionat |
| placement | PL-007 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-012 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-016 | end_date | fi (2026-06-01) anterior a l'inici (2026-06-30) | rebutjat |
| placement | PL-020 | end_date | fi (2026-06-01) anterior a l'inici (2026-06-30) | rebutjat |
| placement | PL-022 | client_id | client inexistent: CL-999 | rebutjat |
| placement | PL-026 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-039 | client_id | client inexistent: CL-999 | rebutjat |
| placement | PL-043 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-046 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-063 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-067 | end_date | fi (2026-06-01) anterior a l'inici (2026-06-30) | rebutjat |
| placement | PL-072 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-075 | status | estat desconegut: '???' | posat a Pending |
| placement | PL-078 | status | estat desconegut: '???' | posat a Pending |
