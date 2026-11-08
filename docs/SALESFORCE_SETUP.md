# Configuració de Salesforce

Calcula entre 1 i 2 hores la primera vegada. Tot es fa des de **Setup → Object Manager**.

## 1. Crea un org gratuït

Registra't a la Developer Edition de Salesforce (developer.salesforce.com, apartat *Sign up*).
És gratuït i no caduca mentre l'utilitzis. Confirma l'email i entra.

## 2. Camps a `Account` (objecte estàndard)

| Etiqueta | API name | Tipus | Notes |
|---|---|---|---|
| ERP Id | `ERP_Id__c` | Text(20) | ✅ **Unique** i ✅ **External ID** |
| CIF | `CIF__c` | Text(9) | |
| Active Placements | `Active_Placements__c` | Number(6, 0) | Valor per defecte `0`. L'omple el trigger d'Apex |

## 3. Objecte `Candidate__c`

*Create → Custom Object*. Label `Candidate`, Record Name `Candidate Name` (Text).

| Etiqueta | API name | Tipus | Notes |
|---|---|---|---|
| ERP Id | `ERP_Id__c` | Text(20) | ✅ Unique, ✅ External ID |
| Email | `Email__c` | Email | |
| Phone | `Phone__c` | Phone | |
| NIF | `NIF__c` | Text(9) | |
| City | `City__c` | Text(80) | |
| Needs Review | `Needs_Review__c` | Checkbox | El marca la sincronització si hi ha dades dubtoses |
| Status | `Status__c` | Picklist | Valors `Available` (per defecte) i `Placed`. L'actualitza el Flow |

## 4. Objecte `Placement__c`

*Create → Custom Object*. Label `Placement`, Record Name `Placement Number`, tipus **Auto Number**,
format `PL-{0000}`.

| Etiqueta | API name | Tipus | Notes |
|---|---|---|---|
| ERP Id | `ERP_Id__c` | Text(20) | ✅ Unique, ✅ External ID |
| Account | `Account__c` | Lookup(Account) | |
| Candidate | `Candidate__c` | Lookup(Candidate) | |
| Position | `Position__c` | Text(100) | |
| Start Date | `Start_Date__c` | Date | |
| End Date | `End_Date__c` | Date | |
| Status | `Status__c` | Picklist | Valors `Pending`, `Active` i `Closed` |
| Hourly Rate | `Hourly_Rate__c` | Currency(16, 2) | |

> Si en crear un camp Salesforce et proposa un API name diferent, corregeix-lo perquè coincideixi
> exactament amb el de la taula. El codi en depèn.

## 5. Flow: estat del candidat

*Setup → Flows → New Flow → Record-Triggered Flow*

1. Objecte **Placement**. Es dispara **quan es crea o s'actualitza un registre**. Optimitza'l per a
   **Actions and Related Records**.
2. Afegeix un element **Decision** sobre `{!$Record.Status__c}`:
   - Branca *Active*: **Update Records**, objecte Candidate, filtre `Id = {!$Record.Candidate__c}`,
     `Status__c = Placed`.
   - Branca *Closed*: el mateix, amb `Status__c = Available`.
3. Desa'l amb el nom `Placement_Updates_Candidate_Status` i activa'l.

*Limitació coneguda (bon tema per a l'entrevista):* si un candidat té dos contractes actius i se'n
tanca un, el Flow el posarà a `Available` igualment. La solució seria comprovar abans si en té
algun altre d'actiu, amb un *Get Records* al Flow o amb Apex.

## 6. Trigger d'Apex

**Opció ràpida:** *Developer Console → File → New*. Enganxa-hi les dues classes de
`salesforce/force-app/main/default/classes/` i el trigger de `.../triggers/`. Després executa el test
des de *Test → New Run*.

**Opció professional (Salesforce CLI):**

```bash
cd salesforce
sf org login web --alias hrsync
sf project deploy start --target-org hrsync
sf apex run test --class-names PlacementTriggerHandlerTest --target-org hrsync --result-format human
```

## 7. Credencials per a la sincronització

Copia `.env.example` a `.env` i omple'l amb una de les dues opcions:

- **Usuari + contrasenya + security token.** El token el reps per email des de
  *(el teu avatar) → Settings → Reset My Security Token*. Si l'org té bloquejat aquest tipus
  d'inici de sessió, fes servir l'opció següent.
- **OAuth Client Credentials.** Crea una app connectada (o *External Client App*) amb el flux
  *Client Credentials* activat i un usuari d'execució assignat. Posa `SF_CONSUMER_KEY`,
  `SF_CONSUMER_SECRET` i `SF_DOMAIN` (per exemple `elteudomini-dev-ed.develop.my`).

Després executa:

```bash
python -m sync.run_sync --full
```

Quan acabi, comprova a Salesforce que tens 12 comptes, 60 candidats i 75 contractes, i que el camp
*Active Placements* dels comptes està omplert.
