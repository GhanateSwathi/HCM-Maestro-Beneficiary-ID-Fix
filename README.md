# HCM Maestro - Beneficiary ID Fix

Maestro (Android) automation for the **Beneficiary ID Fix – QA Test Plan** (2026-10-30): the fix for duplicate beneficiary IDs and UUIDs saved in place of pool IDs, Kaduna build 2.2.120.

| | |
| --- | --- |
| App | `org.egov.azm.gombe` 2.2.120 (label ADAMAWA-AZM) - the Kaduna fix build. From 2026-11-03 evening, X9, X9b and D5 again on `org.egov.azm.kebbi` 2.2.122 (KEBBI-AZM, Kebbi server) - see below |
| Device | From 2026-11-02: emulator `HCM_Beneficiary_ID` (Pixel 9 Pro XL, Android 16, 12 GB data), `emulator-5554` - see [The emulator](#the-emulator). Before: vivo V2059 phone, Android 13, serial `1361446350000MX` |
| User | One CDD (`HCM_CDD_USER_ID` in `.env`) |
| Cases | [TEST-CASES.md](TEST-CASES.md) - the 19 Phase A cases run, and X9b, with result, comments and the ID ledger |

## Where we left off (2026-11-04)

**All three cases that failed on 2.2.120 PASS on Kebbi 2.2.122: X9-122, D5-122 (2026-11-03) and X9b-122 (2026-11-04 10:38).** X9, X9b and D5 run again on Kebbi build 2.2.122 (`kebbi-azm-2.2.122-signed-android-id.apk`) - separate cases `X9-122`, `X9b-122`, `D5-122`, so the 2.2.120 FAILs below stay as evidence. Same two emulators, same flows. The build is a different app on a different server: `org.egov.azm.kebbi`, `kebbi-azm-central-hcm.digit.org` (tenant `kb`), CDD `ke-azm-cdd-01`, boundary ke Garadi Health Post / Tungar Yari. `.env` points at it now (both APKs kept: `HCM_APK_KADUNA`, `HCM_APK_KEBBI`).

| Case | Result | What it showed |
| --- | --- | --- |
| X9-122 | **PASS** | Online, same moment: A **041714103501**, B **101162421824** - different; N 600 → 599 on each; both synced; Search by ID finds each |
| D5-122 | **PASS** | Offline, same moment: A **101012915202**, B **101822411107** - different; N 599 → 598 on each; both synced |
| X9b-122 | **PASS** | 2026-11-04: both logged out; device 1 signed in at 10:41:32, device 2 at 10:42:28; at the same moment A **031272062343**, B **101321202316** - different; N 598 → 597 on each; both synced; Search by ID finds each. No re-fetch after the sign-ins: the button is greyed out at 598 of 600 on 2.2.122, so each device kept the pool it already held (on 2.2.120 that re-fetch is what handed both devices one pool). A first attempt (2026-11-03 19:59) was stopped by QA in part 3, before Save Beneficiary - nothing saved |

**Why it no longer duplicates** (question 6): each device now sends its own `deviceUuid` with its ID download - `8db6335da8f803fa` (emulator-5554) and `3ac5fc15fb2bf925` (emulator-5556), where 2.2.120 sent the build ID `BP22.250221.010` from both - and each got its **own 600 IDs: none in both pools** (compared from the dispatch responses in the logs, 18:40 and 18:58). Every ID the cases gave out came from its own device's pool.

**Next session - start here:**

1. Send questions 6-9 to the dev with the 2.2.120 and 2.2.122 evidence; add the `-122` results to the shared report.
2. Commit, if not done yet - the flow changes for the Kebbi form, the `-122` cases and their results.

To run on Kebbi again: start both emulators with the Kebbi host - `.\scripts\start-emulator.ps1 -UatHost kebbi-azm-central-hcm.digit.org`, then `.\scripts\start-emulator.ps1 -Avd HCM_Beneficiary_ID_2 -Port 5556 -UatHost kebbi-azm-central-hcm.digit.org` (close Chrome and Slack; free RAM was 1-2 GB with both up) - then `.\scripts\run-case.ps1 -Case X9-122` (or D5-122, X9b-122). Both emulators hold Kebbi IDs now (597 of 600 each, 2026-11-04), everything synced.

What changed to run Kebbi (all selectors take both builds' wording, so the Kaduna cases still run): the form is a different config ("version 3") - Register Beneficiary, Beneficiary Location / "Lat/Long *" / Save Location, Save Household Details, "Is head of family? *", Save Beneficiary; the logout dialog asks "…Are you sure you want to logout?"; `launch-app.yaml` relaunches when the app's start-up config request fails ("Internet not available. Try later." - the server dropped it once, 18:28); X9's start downloads as a try (the button is greyed out at 600 of 600 on 2.2.122); `run-case.ps1` records each device's `deviceUuid` in the result; `report.py` counts duplicates within one build only (each build has its own server and ID pool).

## 2.2.120 results (2026-11-03)

**Phase A is done: 17 PASS, 2 FAIL (X9, D5)** - and X9b, QA's variant of X9, FAIL too. The two-device cases ran on 2026-11-03 on both emulators at once - in lockstep, every step on both devices together, signed in as the same CDD (QA's decision; see [Running](#running)) - and **both gave one ID to two people**:

- **X9** (online): A on `emulator-5554` and B on `emulator-5556`, registered at the same moment, both got **121517171780** - the app's log at Submit, the card and the ledger agree on both devices. Both synced; the server accepted both (Data Synced Successfully). Search by ID on each device finds only its own household.
- **D5** (offline): in the run itself A ≠ B (121030208213, 121751162220), but A's **121030208213** had already gone to QAID-D5-B on `emulator-5556` in an attempt stopped at 12:32 (synced with the rest at 12:52) - device 1 handed out an ID device 2 had used, because each device skips only the IDs it used itself.
- **X9b** (QA's variant, sign-ins a minute apart): both log out; device 1 signs in at 14:55:50 and device 2 at 14:56:51, each re-fetching its IDs (596 of 600 on both); then A and B registered at the same moment both got **121212121234** - the minute between sign-ins changed nothing. Both synced.
- Why the two devices hold one pool: the app reports `deviceUuid` as the Android build ID, the same on both emulators (question 6), and both re-fetched the same 600 IDs. Whether phones with different build IDs get different pools is not tested.

Still open from 2.2.120:

1. Send questions 6 and 7 (below) to the dev with the X9 / D5 evidence (`artifacts/runs/20261103-120944-X9`, `…-123825-D5`).
2. Add X9, D5 and P6 (out of scope) to the shared report (Claude doc "Beneficiary ID Fix – QA Test Report (Phase A)") - not done yet.

To run the two-device cases again: close Chrome and Slack (two emulators take about 7 GB), `.\scripts\start-emulator.ps1`, then `.\scripts\start-emulator.ps1 -Avd HCM_Beneficiary_ID_2 -Port 5556`, then `.\scripts\run-case.ps1 -Case X9` (or D5). D5's start parts do not download IDs (Download Beneficiary IDs was greyed out - question 7); put `DOWNLOAD: "yes"` back once it answers again.

No server checks (Postman) - decided 2026-11-02. D12 (two CDDs) and S3 (server setting) stay out.

**The one-device cases** (2026-10-30 to 11-02): **17 PASS**. P1 ran on the phone on 2026-10-30; the other 16 ran on the emulator on 2026-11-02. P6 is out of scope from 2026-11-03 (see its row). The ledger holds 60 IDs (fixtures included) with **no duplicate** - no beneficiary-ID bug found. Results per case, with evidence, are in [TEST-CASES.md](TEST-CASES.md) and `artifacts/report/`.

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
| X9 | **FAIL** | Two emulators, one CDD, online, A and B registered at the same moment: **both got 121517171780**; both synced |
| X9b | **FAIL** | X9 with the sign-ins a minute apart, each device re-fetching its IDs: **both got 121212121234**; both synced |
| D5 | **FAIL** | Two emulators, one CDD, offline: A got **121030208213**, already given to QAID-D5-B on the other emulator; both synced |
| P6 | Out of scope | With 0 IDs the popup offers **only Download, no Skip** - Skip was removed on purpose (2026-11-03), so the case's precondition no longer exists. Its run (2026-11-02 18:44, then BLOCKED) is left out of the tracker; `cases/P6/` is kept for reference |

Two earlier runs were our automation's fault and are marked SUPERSEDED in `artifacts/results.csv`: P5 13:17 (`read-card.yaml` read the head's ID for every member - ledger rows corrected to the IDs on screen) and D1 13:39 (a check ran before E's ID reached it). Both were re-run and passed.

**Scope:** the 17 PASS cases above are the plan's Phase A cases that one device can run; the plan's other 28 cases (Phase B and C, dev setup, two devices or users, manual), and P6 from 2026-11-03, are out of this round and were removed from the tracker and `scripts/cases.csv` - they are still in the QA plan. P1b's way 4 (a dose) was not run: it needs stock (a "Stock Issued" notification of 2 AZM arrived at about 12:00).

**Later:** the same cases driven through android-mcp-bridge (`Downloads\android-mcp-bridge`), to compare with Maestro.

### App findings (not ID bugs)

1. **Raw localisation keys** on the no-connection dialog: open the app in airplane mode - title `CORE_COMMON_CONNECTION_LABEL`, text `CORE_COMMON_CONNECTION_CONTENT`, button `Core_common_ok` ([screenshot](artifacts/findings/offline-dialog-raw-localisation-keys.png)).
2. **Back closes the app** after a cold start: Registration & Delivery → village → type a name → Register New Beneficiary quickly, then system Back on Household Location - the app exits to the Android home screen (P3, every try). The log shows three routes popped at once around the Register tap. At normal speed Back returns to search.
3. **Auth token in logcat**: the app logs request bodies with `"authToken": …` in plain text (background sync). Anyone with USB debugging on a field phone can read it. (Our run logs hold it too - `artifacts/` is git-ignored.)

### On UAT / on the devices

All test households are in Rigan Ori under `dis-qa-oct29`, named `QAID-<case>-<letter>`, listed in `artifacts/ledger.csv`, and synced - including the six households with the three duplicate IDs (X9, X9b, D5). Both emulators were left after X9b (2026-11-03 15:12): signed in, synced, online - 595 of 600 IDs on each. The first emulator's fixtures (QAID-FIX-E1, E2) are on the server but no longer on the emulator - after a clear, the boundary step answers "Data found!" with Go To Home Screen, so download the boundary first before re-running P2, X1 or D2. The phone still holds the 2026-10-30 P1 data; sync it before it is used again.

### Questions for the dev

1. **Search screen reset (RC-03, RC-02 a)**: on 2.2.120 every way back to Search Beneficiary - system Back, the Overview's Back link, Back To Search - shows it emptied, and the Back link drops the Overview (no second search screen). P1, P2, X1 and D2's stale-screen paths cannot be reached. Is the reset the fix? Which steps still reproduce RC-03 / RC-02 (a), if any?
2. **`UPDATE_IDENTIFIER_STATUS` in the log**: no line is ever logged when an ID is checked or reallocated (only the form config naming the action, at sign-in). Under which tag and level does the build log it? Until then the plan's log check (P1, X1, D1 "reallocated") cannot run.
3. ~~"Total beneficiary IDs" falls with every ID used~~ - **withdrawn**: our flow read the available figure twice; the app shows Total 600.
4. **Config on UAT**: with 0 IDs the Low Beneficiary IDs popup shows only Download (no Skip) - **Skip was removed on purpose** (2026-11-03), so P6 is out of scope. Still open: is `REGISTRATION_kd_fix.json` already on UAT (then the config-phase cases can start), and how should QA make UUID ("No Beneficiary ID") people for the edit cases, now that Skip is gone?
5. **Session length**: UAT rejected the app's token about 40 minutes after sign-in ("Sync Up Failed / Session Expired", 401 InvalidAccessTokenException; also "Failed to check data in server" at the boundary step). Is that the intended token lifetime? A field user would have to log out and in to sync.
6. **`deviceUuid` is the Android build ID** (X9, 2026-11-03): the app logs each pool ID as `UniqueIdPoolModel(id: …, deviceUuid: BP22.250221.010, userUuid: <the CDD's>)` - `BP22.250221.010` is `ro.build.id`, the same on both emulators although their `android_id`s differ (`910e3e…`, `d222d5…`). Any two phones of one model on one OS update share it too. Does the server use `deviceUuid` to split a CDD's ID pool between devices? Both emulators re-fetched the same 600 IDs and gave A and B the same ID.
7. **Download Beneficiary IDs greyed out** (2026-11-03 12:30): on `emulator-5554` at 598 of 600, about 20 minutes after a Re-Fetch IDs, the button was not clickable; at 599-600 earlier the same day it answered "Limit exceeded" → Re-Fetch IDs. When is the download disabled, and for how long? (On Kebbi 2.2.122 it is greyed out at 600 of 600, 2026-11-03 19:17.)
8. **Download does nothing on a rejected session** (Kebbi 2.2.122, 2026-11-03 18:45): `ke-azm-cdd-01`'s token was rejected (401 on every request) and Download Beneficiary IDs did nothing - no dialog, no error, no "Session Expired"; the device stayed at 0 of 0. A field user would not know why. Should the app tell them to sign in again?
9. **Both sessions rejected when a second device signed in** (Kebbi 2.2.122, 2026-11-03): `emulator-5554` signed in at about 18:33; from 18:44:20 - just after `emulator-5556` first signed in as the same CDD - both devices got 401. After each signed in again (18:58, 19:09) both worked side by side, so it is not one session per user; and in X9b-122 (2026-11-04 10:41-10:42) device 2's sign-in left device 1's session working. Does the server end a user's sessions when a new device first signs in? (Someone else using the shared CDD then cannot be ruled out.)

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

**Two devices at the same time** (X9, D5): parts that share a stage number - `2-register-a.yaml` and `2-register-b@2.yaml` - run together, one per device, both signed in as the same CDD; the next stage starts when both are done. Each such part runs in its own PowerShell and its output is shown with the device in front (`[emulator-5556] …`); it is kept in `<part>\console.log`. Stages start together, so the two Submits land within seconds of each other (each Maestro run takes 5-15 s to start). Decided 2026-11-03 at QA's request: X9 no longer keeps the plan's order (device 1 syncs A before device 2 downloads).

Case order matters: X8 clears the app's data, so it runs last. (P6, out of scope since 2026-11-03, cleared it too and left the emulator with 0 IDs.)

## Report

| File | Holds |
| --- | --- |
| `artifacts/report/results.xlsx` | Results (PASS / FAIL / BLOCKED / NOT RUN with comments), ID ledger, Summary |
| `artifacts/report/report.html` | The same, as a page |
| [TEST-CASES.md](TEST-CASES.md) | Result and Comments filled in per case |

A case FAILs when any expected result is not met, when the log check finds the wrong number of `reallocated` lines, or when an ID it gave out is already in the ledger. BLOCKED means a precondition was missing (e.g. no IDs on the phone).

## The emulator

`HCM_Beneficiary_ID` was made on 2026-11-02 from the Pixel_9_Pro_XL AVD's settings with a 12 GB data partition (the old AVD had 467 MB free and refused the 67 MB APK; its other HCM apps were left alone). Fixture households for the cases that open "an existing household": QAID-FIX-E1 (`102152221020`, with member QAID-FIX-E1-M1 `104511139711`) and QAID-FIX-E2 (`106431618121`) - [flows/setup/emulator-fixtures.yaml](flows/setup/emulator-fixtures.yaml).

`HCM_Beneficiary_ID_2`, the second device for X9 and D5, has the same settings but a **6 GB** data partition (changed 2026-11-03; the original config is beside it as `config.ini.bak-20261103`). At 12 GB it never booted: the emulator checks for 1.2 × the partition free on C: (14.7 GB) and found 11.8 GB - `Not enough space to create userdata partition` in its log. The app needs 67 MB, so the size does not affect the cases. Both emulators run at 3 GB RAM (the emulator raises the AVD's 2 GB), so two need about 7 GB free.

What broke runs, and what answers it ([scripts/start-emulator.ps1](scripts/start-emulator.ps1) sets all of it):

- **Play Store updates** of Play Services killed the app mid-registration - Play Store is disabled on the emulator.
- **Heads-up notifications** (Auto Sync) covered the Back link - turned off.
- **GPU crash** (exit 139 in the host GPU layer) - started with `-gpu swiftshader_indirect`. It is slower: screens can take 15-30 s, so waits are long.
- **Dead network after a restart** - a quick-boot snapshot brought back a network with no route or DNS. Always cold boot (`-no-snapshot`), with `-dns-server` set.
- **adb drops the emulator** for a moment whenever a Maestro session starts; `run-case.ps1` runs such a part again.
- **"System UI isn't responding"** after a cold boot - `accept-system-dialogs.yaml` taps Wait.
- **Clipboard**: the emulator shares the PC's clipboard, and Gboard offers it as a paste suggestion - keep secrets off the clipboard while cases run (screenshots can show it).
- **Session expiry**: UAT rejected the app's token about 40 minutes after sign-in ("Sync Up Failed / Session Expired"); `sync-data.yaml` logs out and signs in again.
- **Two emulators on 16 GB** (2026-11-03): with both up and two Maestro runs going, free RAM fell to 0.5 GB and screens slowed - typing 9 characters took 38 s. What broke, and the answer: a search text landed garbled (`QAID-X9-A` as `QIDD-X9-A`) - `reg-search.yaml` types it again; Back pressed before home had drawn closed the app - `go-home.yaml` waits up to 6 s for home after each Back; a "Data Synced Successfully" came a minute after the sync - `sync-data.yaml` waits for a late one; a signed-in app showed its login screen for a moment on launch - `sign-in-cdd.yaml` waits 8 s before logging in (and for Allow Permissions, which also flashes by), and first waits for a screen that decides it - the app can be between screens; after a fresh login the boundary's "Data found!" offered Download / Proceed Without Downloading - `boundary-dialog.yaml` proceeds without; the download dialog ("Download in progress... 0/100") can take over 30 s to show - `download-ids.yaml` (try mode) waits 45 s. Close Chrome and Slack first.

## The test phone

- **Screen lock**: the phone has a PIN/pattern lock that adb cannot lift. `run.ps1` keeps the screen on while plugged in during a run and waits up to 10 minutes for an unlock. Turn on Developer options > Stay awake for a session.
- **Logging**: the phone logs at Error level only (`log.tag=E`). `run-case.ps1` raises the app's `flutter` tag to Verbose before each case; it resets when the phone restarts.
- **Boundary**: the app asks for Health Facility and Community after every restart; `subflows/common/home.yaml` answers with `.env`'s values.
- **Maestro run length**: every Maestro run on this phone ends after 5-7 minutes, whatever it does - mid-tap, with no error recorded (P1 at 5m18s and 5m57s, a read-only loop at 6m58s, 2026-10-30). Keep each flow under about 4 minutes; longer cases go in `cases/<case>/` as parts. Each part's `VAR|NAME|VALUE` lines reach the later parts as `-e NAME=VALUE`, and only the first part launches the app.
- **One Maestro client**: don't use the Maestro MCP tools (`/mcp` > maestro) while a case runs.

## Layout

| Folder | Holds |
| --- | --- |
| `cases/<case>/` | One folder per case (17, and P6 kept for reference), in parts (`1-…`, `2-…`; D11 `01-…`) that `run-case.ps1` runs in order |
| `flows/setup/` | Not cases: sign in, sign in and go home, the emulator's fixture households |
| `subflows/common/` | Launch, sign-in, home, boundary and system dialogs, sync, logout |
| `subflows/registration/` | Search, register a household (in parts), add member, consent No, back to search |
| `subflows/id/` | Case start, ID count, card IDs, download IDs, Search by ID, the ID book-keeping (`id.js`) |
| `subflows/cases/` | Steps one case repeats (P3's try, D2's three Backs, D11's rounds) |
| `scripts/` | Runners (`run-case.ps1`, `run.ps1`, `start-emulator.ps1`), the case list (`cases.csv`), the report builder |

Phases are tags: `phase-a` (new build, old config); P1 and X1 also carry `phase-b`, the plan's repeat once the config is on UAT.

## Test data

Every case writes real records to UAT. Test people are named `QAID-<case>-<letter>` (e.g. `QAID-P1-A`) so each ledger row traces back to its case. End each session with Sync Data.
