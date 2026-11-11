# HCM Maestro - Search by proximity

Maestro (Android) cases for **Near by households** (search by proximity) in Search Beneficiary. This suite is separate from the Beneficiary ID Fix suite in the [root README](../README.md). It reuses the root's `subflows/`, `scripts/run.ps1` and `.env`.

| | |
| --- | --- |
| App | `org.egov.azm.gombe` **2.2.122** (label ADAMAWA-AZM), `kaduna-azm-signed-db-2.2.122.apk` |
| Server | Kaduna UAT, `kaduna-central-hcm.digit.org`, tenant `kd` |
| User | CDD `dis-qa-oct29`, Fangwani Health Clinic / Rigan Ori (153 households in the download) |
| Device | `emulator-5554` (`HCM_Beneficiary_ID`); GPS set with `adb emu geo fix <lon> <lat>` |
| Cases | [PROXIMITY-CASES.md](PROXIMITY-CASES.md) - 41 cases (positive, negative, edge), bugs B1-B10, root cause, results |

## Layout

| Path | What |
| --- | --- |
| `proximity/PROXIMITY-CASES.md` | Cases, bugs, root cause, results |
| `proximity/run.ps1` | Runs one flow with the Kaduna app and boundary (wraps `scripts/run.ps1`) |
| `proximity/cases/NB1/` | Boundary + download, home + IDs + Search, register A, `reopen-search.yaml` (used by every case) |
| `proximity/cases/NB2/` | Register-and-check while moving, check from the centre, radius probe, stale centre (E-09), location page |
| `proximity/cases/NB3/` | Consent-No household; Near by on (optionally a name typed). NB4 reused these at a second spot |
| `proximity/cases/NB5/` | QA's manual case: register Swathi Ghanate, back to Search, Near by on; then type the name |
| `proximity/cases/NB6/` | Clean start, part 0: sync, then log out before the storage is cleared |
| `proximity/scripts/nearby-list.py` | Records every card in the result list while swiping down, then up |
| `proximity/scripts/saved-latlong.py` | Reads each household's saved lat/long from the upload log |
| `artifacts/proximity/runs/` | Run output (not committed: Maestro logs hold the typed password) |

## Running

`.env` supplies the sign-in. `HCM_CDD_USER_ID` and `HCM_CDD_PASSWORD` must be the Kaduna CDD (`dis-qa-oct29`). The runner sets `HCM_APP_ID`, `HEALTH_FACILITY` and `REGISTRATION_VILLAGE` to the Kaduna values for every run, so `.env` can keep the ID-fix suite's boundary.

```powershell
# One part; output to artifacts\proximity\runs\<yyyyMMdd>-NB5\1-register-and-nearby
.\proximity\run.ps1 -Flow proximity\cases\NB5\1-register-and-nearby.yaml -Set 'NAME=Swathi','LAST_NAME=Ghanate'
.\proximity\run.ps1 -Flow proximity\cases\NB5\2-type-name.yaml -Set 'NAME=Swathi','LAST_NAME=Ghanate'

# Move the emulator's GPS (longitude first), then reopen Search
adb -s emulator-5554 emu geo fix 7.4388 10.5222

# Record the Near by list on screen (7 s per swipe)
python -I proximity\scripts\nearby-list.py emulator-5554 artifacts\proximity\runs\list.json 7
```

Variables some flows need (`-Set`):
- `NAME` (register, consent-No, location page); `KEY` (register-and-check)
- `TARGET`, `DIST` (radius probe); `TYPE` (NB3 Near by on, optional)

The **clean start** (NB6) is:
1. Part 0.
2. `adb shell pm clear org.egov.azm.gombe`.
3. Sign in.
4. NB1 parts 1-2.
5. NB5 parts 1-2.

Kaduna UAT refuses a second session (root README, question 10). Sign the emulator out before QA signs in elsewhere as `dis-qa-oct29`, and the other way round.

## Where we left off (2026-11-06)

QA's report is reproduced: after downloading Rigan Ori (153 households), a newly registered household is not shown under Near by.

- **QA's clean-start case FAILs (NB6, 16:24-16:40).** Steps: sync and log out, clear storage, sign in, download Rigan Ori, register **Swathi Ghanate** with consent Yes (ID 152122513211), go back to Search, switch on Near by. Only QAID-FIX-E1, FIX-E2 and X4-B are listed. With "Swathi" typed, she is listed. Same in NB5 (16:14, ID 161221817591).
- **B1 cause, traced in the code and proven on the device.**
  - Near by fetches 5 households per page, unsorted.
  - The card builder then drops households with no active member, such as consent No (`wrapper_builder.dart:71-74`).
  - It counts cards, not rows (`flow_crud_bloc.dart:116-118`), and `hasMoreDown = loadedCount >= 5` (`search_state_manager.dart:128`). A short page therefore ends the list, and no later household loads.
  - NB3: a consent-No household + 5 normal, and the 5th never shows. NB4 control: 6 normal, all show.
  - Details in [PROXIMITY-CASES.md](PROXIMITY-CASES.md), "B1 root cause in the code".
- **Other bugs:**
  - B2-B4: scrolling skips, duplicates and loses the top. These also happen with a name typed; cause not traced.
  - B5: no sort, the newest household is last.
  - B6: the location page shows no lat/long.
  - B7: Back on Household Location closes the app.
  - B8: the radius in use is about 85 m, not 5 km.
  - B9: the centre stays where Search was opened.
  - B10: Near by off clears the typed name.
- **Saved lat/long:** correct for the households registered while moving, 0 to 10 km apart.
- **Download:** Rigan Ori still downloads 153. Today's synced households, including the 16:14 Swathi Ghanate, are not included.

Emulator state:
- `emulator-5554` runs `org.egov.azm.gombe` 2.2.122; 2.2.120 was uninstalled with QA's OK.
- Storage was cleared for NB6, then the emulator signed in as `dis-qa-oct29` and downloaded Rigan Ori.
- Swathi Ghanate (152122513211) was registered after that. Run Sync Data before the next storage clear: NB6 part 0 does it.
- Test households:
  - QAID-NB1-A and QAID-NB2-C/1KM/4K9/5K1/10KM.
  - QAID-NB3-X (consent No) and NB3-1..5 at 10.2524, 7.4388.
  - QAID-NB4-1..6 at 10.7920, 7.4388.

Next:
1. Send the dev the B1 cause and fix options. Either decide "more pages" from rows fetched, or put the member filter in the SQL query; also sort nearest first.
2. Ask the dev about B8 (live `proximityRadius`), and whether the download list is refreshed on a schedule (still 153).
3. Not run yet: E-06 (order after kill/relaunch), E-07 (after re-download), E-10 (another village nearby).
