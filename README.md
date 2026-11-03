# HCM Maestro - Beneficiary ID Fix

Maestro (Android) automation for the **Beneficiary ID Fix – QA Test Plan** (2026-10-30): the fix for duplicate beneficiary IDs and UUIDs saved in place of pool IDs, Kaduna build 2.2.120.

| | |
| --- | --- |
| App | `org.egov.azm.gombe` 2.2.120 (label ADAMAWA-AZM) - the Kaduna fix build |
| Device | From 2026-11-02: emulator `HCM_Beneficiary_ID` (Pixel 9 Pro XL, Android 16, 12 GB data), `emulator-5554` - see [The emulator](#the-emulator). Before: vivo V2059 phone, Android 13, serial `1361446350000MX` |
| User | One CDD (`HCM_CDD_USER_ID` in `.env`) |
| Cases | [TEST-CASES.md](TEST-CASES.md) - the 18 Phase A cases run, with result, comments and the ID ledger |

## Where we left off (2026-11-02)

**Next session - start here: the two-device cases X9 and D5**, on two identical emulators (same AVD settings, build, CDD and boundary). Everything is written; nothing has run yet.

1. Close heavy apps first: two emulators need about 6 GB of free RAM (9.4 GB was free once Chrome and Slack were closed).
2. `.\scripts\start-emulator.ps1` (HCM_Beneficiary_ID → `emulator-5554`), then `.\scripts\start-emulator.ps1 -Avd HCM_Beneficiary_ID_2 -Port 5556` (→ `emulator-5556`). The second one's very first boot is slow - it had not finished within 10 minutes on 2026-11-02 19:28; give it time. The script installs the app (`HCM_APK` in `.env`) when it is missing.
3. `.\scripts\run-case.ps1 -Case X9`, then `.\scripts\run-case.ps1 -Case D5`. Parts named `…@2.yaml` run on `DEVICE_ID_2`; ledger rows name the device.
4. D5 syncs both devices at the end, as the plan says (decided 2026-11-02): if A and B get the same ID, that duplicate goes to the server and the case FAILs - the cross-device gap only the server setting can close.
5. Afterwards: add X9 and D5 to the shared report (Claude doc "Beneficiary ID Fix – QA Test Report (Phase A)") and to this section.

No server checks (Postman) - decided 2026-11-02. D12 (two CDDs) and S3 (server setting) stay out.

**Phase A is done** for every case one device can run: **17 PASS, 1 BLOCKED (P6)**. P1 ran on the phone on 2026-10-30; the other 17 ran on the emulator on 2026-11-02. The ledger holds 60 IDs (fixtures included) with **no duplicate** - no beneficiary-ID bug found. Results per case, with evidence, are in [TEST-CASES.md](TEST-CASES.md) and `artifacts/report/`.

| Case | Result | What it showed |
| --- | --- | --- |
| P1, P1b, D1, P5 | PASS | Every person from one search screen, in a row, or after each way back to search, got a different ID; N available dropped by exactly 1 per person |
| P2, X1, D2 | PASS (ID checks only) | The stale or older search screen the case is about **does not exist on 2.2.120** - every way back to Search Beneficiary shows it reset (see question 1). Their IDs are unique |
| P3 | PASS | 5 cold starts with a fast Register tap: no Low Beneficiary IDs popup |
| P4 | PASS | RC-15: Re-Fetch IDs before X synced left X's ID used (568 → 568 of 600); Y ≠ X |
| X2 | PASS | The Acknowledgement's Token ID is the ID saved on the card (also every member in P1b, P5) |
| X3, X4 | PASS | An abandoned form (Back or app killed) and a consent-No household use no ID |
| X5 | PASS | A double-tapped Submit saves one household |
| X6 | PASS | Offline: 3 people, 3 IDs; the sync afterwards succeeds |
| X8 | PASS | After sync + clear data + Re-Fetch: 546 of 600 - the 54 synced IDs left out; B got a new one |
| D6 | PASS | Logging out and back in keeps used IDs used (592 → 592) |
| D11 | PASS | Killed right after Submit, 3 rounds: A always saved with an ID and N 1 lower; B never A's ID |
| P6 | **BLOCKED** | With 0 IDs the popup offers **only Download, no Skip** - the new config's behaviour. The UUID ("No Beneficiary ID") people P6 makes could not be made (question 4) |

Two earlier runs were our automation's fault and are marked SUPERSEDED in `artifacts/results.csv`: P5 13:17 (`read-card.yaml` read the head's ID for every member - ledger rows corrected to the IDs on screen) and D1 13:39 (a check ran before E's ID reached it). Both were re-run and passed.

**Scope:** the 18 cases above are the plan's Phase A cases that one device can run; the plan's other 28 cases (Phase B and C, dev setup, two devices or users, manual) are out of this round and were removed from the tracker and `scripts/cases.csv` - they are still in the QA plan. P1b's way 4 (a dose) was not run: it needs stock (a "Stock Issued" notification of 2 AZM arrived at about 12:00).

**Later:** the same cases driven through android-mcp-bridge (`Downloads\android-mcp-bridge`), to compare with Maestro.

### App findings (not ID bugs)

1. **Raw localisation keys** on the no-connection dialog: open the app in airplane mode - title `CORE_COMMON_CONNECTION_LABEL`, text `CORE_COMMON_CONNECTION_CONTENT`, button `Core_common_ok` ([screenshot](artifacts/findings/offline-dialog-raw-localisation-keys.png)).
2. **Back closes the app** after a cold start: Registration & Delivery → village → type a name → Register New Beneficiary quickly, then system Back on Household Location - the app exits to the Android home screen (P3, every try). The log shows three routes popped at once around the Register tap. At normal speed Back returns to search.
3. **Auth token in logcat**: the app logs request bodies with `"authToken": …` in plain text (background sync). Anyone with USB debugging on a field phone can read it. (Our run logs hold it too - `artifacts/` is git-ignored.)

### On UAT / on the devices

All test households are in Rigan Ori under `dis-qa-oct29`, named `QAID-<case>-<letter>`, listed in `artifacts/ledger.csv`, and synced. The emulator was last left after P6: app data cleared, signed in, **0 IDs**, no UUID people. Its fixtures (QAID-FIX-E1, E2) are on the server but no longer on the emulator - after a clear, the boundary step answers "Data found!" with Go To Home Screen, so download the boundary first before re-running P2, X1 or D2. The phone still holds the 2026-10-30 P1 data; sync it before it is used again.

### Questions for the dev

1. **Search screen reset (RC-03, RC-02 a)**: on 2.2.120 every way back to Search Beneficiary - system Back, the Overview's Back link, Back To Search - shows it emptied, and the Back link drops the Overview (no second search screen). P1, P2, X1 and D2's stale-screen paths cannot be reached. Is the reset the fix? Which steps still reproduce RC-03 / RC-02 (a), if any?
2. **`UPDATE_IDENTIFIER_STATUS` in the log**: no line is ever logged when an ID is checked or reallocated (only the form config naming the action, at sign-in). Under which tag and level does the build log it? Until then the plan's log check (P1, X1, D1 "reallocated") cannot run.
3. ~~"Total beneficiary IDs" falls with every ID used~~ - **withdrawn**: our flow read the available figure twice; the app shows Total 600.
4. **Config on UAT**: with 0 IDs the Low Beneficiary IDs popup shows only Download (no Skip) - the new config's behaviour. Is `REGISTRATION_kd_fix.json` already on UAT? If so the config-phase cases can start; and how should QA make UUID ("No Beneficiary ID") people for the edit cases, now that Skip is gone?
5. **Session length**: UAT rejected the app's token about 40 minutes after sign-in ("Sync Up Failed / Session Expired", 401 InvalidAccessTokenException; also "Failed to check data in server" at the boundary step). Is that the intended token lifetime? A field user would have to log out and in to sync.

## Setup

1. Install the [Maestro CLI](https://docs.maestro.dev) and Java 17 (the runners pin `C:\Program Files\Amazon Corretto\jdk17.0.20_10`).
2. Copy `.env.example` to `.env` and fill in the values (`DEVICE_ID=emulator-5554` for the emulator).
3. Start the emulator with `.\scripts\start-emulator.ps1` - it waits until the emulator can reach UAT. (For the phone instead: USB debugging on, `adb devices` lists it, `DEVICE_ID` = its serial.)

## Running

```powershell
.\scripts\start-emulator.ps1                       # cold-boot the emulator and wait for UAT
.\scripts\run-case.ps1 -Case P1                    # one case, with the log check and the report
.\scripts\run-case.ps1 -Case D6 -Resume artifacts\runs\<run> -From 3-relogin   # carry on a stopped run
.\scripts\run.ps1 -Flow flows\setup\cdd-home.yaml  # sign in and go home (before a -Resume)
python .\scripts\report.py build                   # rebuild the report from results so far
```

`run-case.ps1` records the device's log around the case, counts its `UPDATE_IDENTIFIER_STATUS` / `reallocated` lines against [scripts/cases.csv](scripts/cases.csv), and records the result. Each run writes to `artifacts/runs/<yyyyMMdd-HHmmss>-<case>/`. A part Maestro loses (no failed check, a connection error) is run again up to twice - its first attempt is kept as `<part>.lost-<n>`. X1 also records X2 (lines tagged `X2:`).

Case order matters: X8 and P6 clear the app's data, so they run last, P6 the very last (it leaves the emulator with 0 IDs).

## Report

| File | Holds |
| --- | --- |
| `artifacts/report/results.xlsx` | Results (PASS / FAIL / BLOCKED / NOT RUN with comments), ID ledger, Summary |
| `artifacts/report/report.html` | The same, as a page |
| [TEST-CASES.md](TEST-CASES.md) | Result and Comments filled in per case |

A case FAILs when any expected result is not met, when the log check finds the wrong number of `reallocated` lines, or when an ID it gave out is already in the ledger. BLOCKED means a precondition was missing (e.g. no IDs on the phone).

## The emulator

`HCM_Beneficiary_ID` was made on 2026-11-02 from the Pixel_9_Pro_XL AVD's settings with a 12 GB data partition (the old AVD had 467 MB free and refused the 67 MB APK; its other HCM apps were left alone). Fixture households for the cases that open "an existing household": QAID-FIX-E1 (`102152221020`, with member QAID-FIX-E1-M1 `104511139711`) and QAID-FIX-E2 (`106431618121`) - [flows/setup/emulator-fixtures.yaml](flows/setup/emulator-fixtures.yaml).

What broke runs, and what answers it ([scripts/start-emulator.ps1](scripts/start-emulator.ps1) sets all of it):

- **Play Store updates** of Play Services killed the app mid-registration - Play Store is disabled on the emulator.
- **Heads-up notifications** (Auto Sync) covered the Back link - turned off.
- **GPU crash** (exit 139 in the host GPU layer) - started with `-gpu swiftshader_indirect`. It is slower: screens can take 15-30 s, so waits are long.
- **Dead network after a restart** - a quick-boot snapshot brought back a network with no route or DNS. Always cold boot (`-no-snapshot`), with `-dns-server` set.
- **adb drops the emulator** for a moment whenever a Maestro session starts; `run-case.ps1` runs such a part again.
- **"System UI isn't responding"** after a cold boot - `accept-system-dialogs.yaml` taps Wait.
- **Clipboard**: the emulator shares the PC's clipboard, and Gboard offers it as a paste suggestion - keep secrets off the clipboard while cases run (screenshots can show it).
- **Session expiry**: UAT rejected the app's token about 40 minutes after sign-in ("Sync Up Failed / Session Expired"); `sync-data.yaml` logs out and signs in again.

## The test phone

- **Screen lock**: the phone has a PIN/pattern lock that adb cannot lift. `run.ps1` keeps the screen on while plugged in during a run and waits up to 10 minutes for an unlock. Turn on Developer options > Stay awake for a session.
- **Logging**: the phone logs at Error level only (`log.tag=E`). `run-case.ps1` raises the app's `flutter` tag to Verbose before each case; it resets when the phone restarts.
- **Boundary**: the app asks for Health Facility and Community after every restart; `subflows/common/home.yaml` answers with `.env`'s values.
- **Maestro run length**: every Maestro run on this phone ends after 5-7 minutes, whatever it does - mid-tap, with no error recorded (P1 at 5m18s and 5m57s, a read-only loop at 6m58s, 2026-10-30). Keep each flow under about 4 minutes; longer cases go in `cases/<case>/` as parts. Each part's `VAR|NAME|VALUE` lines reach the later parts as `-e NAME=VALUE`, and only the first part launches the app.
- **One Maestro client**: don't use the Maestro MCP tools (`/mcp` > maestro) while a case runs.

## Layout

| Folder | Holds |
| --- | --- |
| `cases/<case>/` | One folder per case (18), in parts (`1-…`, `2-…`; D11 `01-…`) that `run-case.ps1` runs in order |
| `flows/setup/` | Not cases: sign in, sign in and go home, the emulator's fixture households |
| `subflows/common/` | Launch, sign-in, home, boundary and system dialogs, sync, logout |
| `subflows/registration/` | Search, register a household (in parts), add member, consent No, back to search |
| `subflows/id/` | Case start, ID count, card IDs, download IDs, Search by ID, the ID book-keeping (`id.js`) |
| `subflows/cases/` | Steps one case repeats (P3's try, D2's three Backs, D11's rounds) |
| `scripts/` | Runners (`run-case.ps1`, `run.ps1`, `start-emulator.ps1`), the case list (`cases.csv`), the report builder |

Phases are tags: `phase-a` (new build, old config); P1 and X1 also carry `phase-b`, the plan's repeat once the config is on UAT.

## Test data

Every case writes real records to UAT. Test people are named `QAID-<case>-<letter>` (e.g. `QAID-P1-A`) so each ledger row traces back to its case. End each session with Sync Data.
