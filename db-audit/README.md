# DB audit - are the CDD's actions stored in the local DB?

QA check, one record per case: do an action in the app as a CDD, then read that record from the app's own local database, field by field. Results: [RESULTS.md](RESULTS.md), and field by field, captured or not, in [CDD-field-capture.xlsx](CDD-field-capture.xlsx).

## Where we left off (2026-11-11)

- **Done:** all 10 CDD cases, each checked in the DB (Cases 1-5 on 10 Nov, 6-10 on 11 Nov): registration + referral, delivery, ineligible, referral with Case 2's dates, consent No, Unable to Deliver, redose, revisit / edit, SMC Yes -> No, abandoned checklist. Details: [RESULTS.md](RESULTS.md).
- **Sheet:** [CDD-field-capture.xlsx](CDD-field-capture.xlsx), 153 rows: 126 captured, 2 not captured (`task_resource.delivery_comment` empty after "Delivery Successful", Cases 2 and 9), 3 correctly not saved, 22 not applicable, 0 not tested. 17 findings for the dev team (Findings sheet).
- **Open dev questions:** referral reason always SICK; delivery_comment column empty; checklist keys / date formats differ on the ineligible path; consent-No household stores member_count 1; redose stored with status VISITED; row_version / audit_modified_time unchanged on edit; head's edit form titled "Child's Details".
- **Sync NOT done (2026-11-11 12:36):** `flows/sync.yaml` hit "Session Expired"; the flow logged out (local data kept, as in D6) and signed in again, but Kaduna UAT answered **USER_ALREADY_LOGGED_IN** - `dis-qa-oct29` is signed in on another device. `emulator-5554` sits on the Login screen with that dialog; the Case 5-10 records are still on it, unsynced. Once the other session is ended: sign in, check the records in the DB viewer, then Sync Data (`flows/sync.yaml`). `HCM_DB_Audit` is stopped.
- **Watch out:** Claude Code's Maestro MCP (`maestro mcp` java process) restarts on its own and holds the device; stop it before CLI runs. A run can stall while the PC sleeps.
- **In git:** branch `db-audit-cdd` (pushed 2026-11-11), together with the Near by suite (`proximity/`); not merged into `main` yet. `db-audit/config/` stays local.

## How the local DB is read

The app keeps its data in `/data/data/org.egov.azm.gombe/app_flutter/db.sqlite` (Drift over SQLite), **encrypted with SQLCipher**. So a copy of the file cannot be opened without the key, and the key is not taken from the app. The Kaduna AZM `-db` build (2.2.122) has a **DB** card on the CDD's home screen: the Drift DB viewer. Opening any table, then the filter button, then the pencil gives **Edit Query**, a free SQL editor. That is how every check here reads the DB, inside the app and read-only (SELECT only).

| Path | What |
| --- | --- |
| `flows/home.yaml` | The app in front, on home: closes a "Sync failed" popup, answers a restarted app's boundary question, goes home through the side menu (Back ran past home and out of the app twice) |
| `flows/db-query-open.yaml` | Home -> DB -> household -> Filter -> Edit Query, emptied and focused |
| `flows/db-query-run.yaml` | Runs the SQL typed in and logs the single result cell as `DBROW|<label>|<text>` |
| `flows/register-household-child.yaml` | A household (head `NAME`) and one child (`CHILD`), through the Beneficiary ID suite's registration subflows |
| `flows/open-household.yaml` | Opens household `NAME` on Household Overview |
| `flows/add-child.yaml` | Adds child `CHILD` to household `NAME` (used when a registration stopped after the head, and for a second child) |
| `flows/consent-no.yaml` | Case 5: a new household with caregiver consent No and a reason |
| `flows/db-query.yaml` | First version, Maestro typing only - kept for reference; too slow for long SQL |
| `scripts/db_query.py` | One check: opens the editor, types the SQL with `adb shell input text` in 30-character pieces, checks the field holds exactly that SQL, runs it, prints the JSON |
| `scripts/screen.py` | Prints the texts on screen (`maestro hierarchy`), for working out taps |
| `scripts/db_snapshot.py` | Pulls the DB file off a rooted emulator - useful only with the SQLCipher key |
| `scripts/build_field_sheet.py` | Writes `CDD-field-capture.xlsx`: every field of the CDD screens (from the live form config) with what was entered, the table / column it went to and its status. The case results are in the script's `OBS` list; add a case there and run it again (`python db-audit\scripts\build_field_sheet.py`, needs openpyxl; LibreOffice, if installed, stores the Summary counts) |
| `config/` | The live form config (REGISTRATION v8, logged by the app 2026-11-02) and the English labels, the sheet's source for field names, types and conditions. **Local only, not in git** (client data, public repo): rebuild it from an app log with the FormConfig extractor, or ask for the copy |

## Running a check

```powershell
python -I db-audit\scripts\db_query.py c1-head "SELECT json_object('name',n.given_name,'dob',i.date_of_birth) AS j FROM name n JOIN individual i ON i.client_reference_id=n.individual_client_reference_id WHERE n.given_name='QAID-DB1-H'"
```

- **One row, one column.** The SQL must return a single column named `j`, usually `json_object(...)`, because the flow copies that one cell.
- **No `%`.** `adb input text` reads `%s` as a space; use `instr()` instead of `LIKE`.
- **Output.** Each check is kept in `artifacts/db-audit/queries/<time>-<label>.json`, as the SQL with its answer.

Typing is the slow part. Maestro's `inputText` types about 2 characters a second and stops after 120 s. `adb input text` is fast, but drops characters when it runs ahead of the field, hence the small pieces and the read-back.

## Setup used (2026-11-10)

- **Device:** emulator `HCM_Beneficiary_ID` (`emulator-5554`), signed in as `dis-qa-oct29`. Kaduna UAT allows one session per CDD, so a second device could not sign in.
- **Boundary:** Fangwani Health Clinic / Rigan Ori (`-Set HEALTH_FACILITY=... REGISTRATION_VILLAGE=...`).
- **Rootable emulator:** `HCM_DB_Audit` (`emulator-5558`, google_apis image) is kept for when dev provides the SQLCipher key. Sign `HCM_Beneficiary_ID` out first.

Every case writes real records to Kaduna UAT when the app syncs. Records are named `QAID-DB<case>-<role>`.
