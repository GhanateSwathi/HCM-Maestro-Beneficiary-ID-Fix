# Search by proximity ("Near by households") - test cases

Kaduna UAT, build `org.egov.azm.gombe` 2.2.122, CDD `dis-qa-oct29`, Fangwani Health Clinic / Rigan Ori. Written 2026-11-06.

**Reported issue:** on a clean phone with no data downloaded, a newly registered household shows under Near by households. After downloading Rigan Ori's data (153 households) and then registering a new household, the new one does not show, before or after sync. Some time later it shows, but some other households are then missing.

## 1. How the search works

Sources: the app's search config as Kaduna UAT served it (logged 2026-11-02 13:12, D6 run); the open-source HCM code (`egovernments/health-campaign-field-worker-app`, master); and strings in the 2.2.122 APK (the same "within" filter, bounding box, two-way paging and `[QueryPerf]` log are compiled in). **Assumption:** 2.2.122 uses the same code and config as these.

| # | Fact | Source |
| --- | --- | --- |
| F1 | Radius **5 km** in the 2026-11-02 config (`proximityRadius: 5`, read as kilometres). **Measured on 2.2.122 on 2026-11-06: about 85 m** - see B8 | Config; `query_builder.dart:770` |
| F2 | Results load **5 households per page**; at most **15** are kept; more load as you scroll down (or back up) | Config `pagination: {limit: 5, maxItems: 15}`, `triggerMode: bidirectional`; log `limit=5, maxItems=15` |
| F3 | **No sort order** - not by distance, not by date. Households come back in whatever order SQLite returns them | Config has no `orderBy` for this search |
| F4 | The filter is a **square box** of ±5 km, not a circle. Households in the corners, up to 7.07 km away, are included | `query_builder.dart:248-286` (the cross-table path has no exact-distance check) |
| F5 | The search centre is the **first GPS fix after the Search screen opens**. Later fixes are ignored until the screen is opened again | `proximity_search_widget.dart:89` |
| F6 | The switch is **disabled until there is a GPS fix** | `proximity_search_widget.dart:98-103` |
| F7 | Households whose address has **no lat/long** never match | SQL `BETWEEN` on NULL; `query_builder.dart:1114` |
| F8 | The config also asks for **the selected village** (`localityBoundaryCode`), but the widget replaces every data entry with the location filter. **With Near by on, the village filter is dropped** - households from other villages within 5 km show too | `proximity_search_widget.dart:216-227` |
| F9 | Every household the emulator registered was saved at its fixed GPS point (10.5221983, 7.4387983). Members added later were saved with **null** lat/long; the search is by household, so this should not matter | Our run logs, 2026-10-30 to 11-04 |

### Cause of the reported issue (confirmed on the emulator - see 1a)

Two bugs together:

1. **Paging (B1-B5).** Near by loads 5 households per page and stops at the first short page.
   - A **consent-No household** in range takes a slot without being shown, so the page comes back short and the list ends there. Every household after it - including the one just registered (always last, B5) - never shows (B1; cause proven by NB3 against the NB4 control).
   - Scrolling also skips households, shows some twice, and loses the top of the list (B2-B4).
2. **Radius of ~85 m, not 5 km (B8).** On a real phone, GPS drifts by tens of metres. A household registered a few steps away drops in and out of Near by from one fix to the next - "after some time I saw it, but others were missing".

The saved lat/long is correct, also while moving (moving check in 1a).

### 3-minute check on your phone (do this first)

Start from the failing state: data downloaded, new household H registered.

1. Search Beneficiary -> switch on **Near by households**. Count the cards on the first screen (expect 5).
2. Scroll down slowly to the very end, letting each page load. Note the position where H appears and the total number of households.
3. With Near by still on, type H's name.

| What you see | Meaning | Cases |
| --- | --- | --- |
| H appears further down the list | No sort + paging: H isn't missing, just not on screen. Bug: the newest or nearest household is not shown first | E1, E2, E5 |
| H never appears even at the end, but step 3 finds it | Paging skips households | E3, E4 |
| Step 3 does not find H, but it is found with Near by off | Location or filter problem | E7-E10, N5 |

Optional evidence (phone on USB): `adb logcat -s flutter | findstr /C:"QueryPerf" /C:"SEARCH_EVENT" /C:"REFRESH_SEARCH"` - each page fetch logs `[QueryPerf] household ... rows=N` and its offset.

## 1a. Confirmed on the emulator (2026-11-06)

`emulator-5554`, `org.egov.azm.gombe` 2.2.122 (`kaduna-azm-signed-db-2.2.122.apk`), fresh install, `dis-qa-oct29`, Fangwani Health Clinic / Rigan Ori, **Data found! → Download: 153/153 records**. GPS at C (10.5222, 7.4388), the spot where this emulator registered about 45 QAID households on 2026-11-02 to 11-04. Evidence: `artifacts/proximity/runs/20261106-NB1/`. Lists were recorded screen by screen with `proximity/scripts/nearby-list.py`.

| # | Bug | Evidence |
| --- | --- | --- |
| **B1** | **Near by (no name) shows only 3 households and stops.** It lists QAID-FIX-E1, QAID-FIX-E2 and QAID-X4-B; scrolling to the end loads nothing more (no spinner). At least 18 households are in range: with Near by on, `QAID` typed lists 18+ and `QAID-P5` finds P5-A. **This is QA's report:** QAID-NB1-A, registered at this spot at 14:06, was not in the list | `3-nearby/baseline-before-register.json`, `6-nearby-after-a/list.json`, `6-nearby-after-a/nearby-on-no-name.png` |
| **B2** | **Scrolling down skips households.** With Near by on and `QAID` typed, the list jumps from QAID-P5-A straight to QAID-D5-A; P5-B, P5-C, X8-A, X8-B, X9-A and X9-B are never shown on the way down | `8-nearby-name-QAID-slow/list.json` frames 7 → 8 |
| **B3** | **Scrolling back up shows households that were skipped, and duplicates.** P5-B, P5-C, X8-A/B and X9-A/B appear only on the way up; QAID-X9-B shows twice on one screen | same, frames 14-18 (X9-B twice in frame 15) |
| **B4** | **The top of the list can't be reached again.** After scrolling down, scrolling all the way up stops at QAID-D11-2B / D1-A; FIX-E1, FIX-E2, X4-B, P2-A, X3-A, X5-A and D6-A/B never come back | same, frames 0 and 21-25 |
| **B5** | **No sort order: the newest household is always last.** QAID-NB1-A (registered last) is at the very bottom, not near the top, although it is the nearest (0 m) | same, frame 8 |
| B6 | The Household Location page shows only the fix's accuracy ("5.00 meters"), not the latitude/longitude, so the worker can't check what is saved | `20261106-NB2/C-1-location` |
| B7 | System Back on Household Location closes the app to the Android home screen (README app finding 2, still on 2.2.122) | 2026-11-06 14:22, after `proximity/cases/NB2/open-location.yaml` |
| **B8** | **The radius in use is about 85 m, not 5 km.** From QAID-NB2-C's saved point, Near by + its name finds it at 0, 10, 30, 60 and 80 m north, but **not at 90, 100, 250, 500 or 750 m**. Households 1 km and 4.9 km away are not near by. The 2026-11-02 config said `proximityRadius: 5` (km); today's config was not in the log - ask the dev what value is live. With ~85 m, normal GPS drift (indoors 20-100 m) moves households in and out of Near by | `20261106-NB2/probe-*m`, `Z-check-from-centre` |

| **B9** | **Near by keeps searching around where Search was opened.** Search opened at C, the GPS moved 10 km north with the screen open, then Near by on + `QAID-NB2`: NB2-C is listed (the old spot), NB2-10KM is not. Switching Near by off and on doesn't refresh it (the C households are still listed); only leaving Search and opening it again does. A worker walking from compound to compound with the screen open sees the wrong households | `20261106-NB2/E09-stale-centre` (`e09-stale-centre.png`, `e09-after-toggle.png`) |
| **B10** | **Switching Near by off clears the typed name.** `QAID-NB2` typed, Near by off then on: the field is empty and the plain Near by list shows | `20261106-NB2/E09-stale-centre/.../e09-after-toggle.png` |

### B1 root cause in the code (traced 2026-11-06)

Sources: HCM app master (`digit_flow_builder`, `digit_crud_bloc`), whose code is compiled into 2.2.122; the live Kaduna search config (logged 2026-11-02 13:12, `20261102-125010-D6/4-register-b`, lines ~20430-20540).

1. **The query takes 5 households, in no particular order, including memberless ones.** Near by runs a household search with the location filter on `address`, `LIMIT 5 OFFSET 0`, and no `ORDER BY`.
   - Config: `searchConfig: {primary: household, pagination: {limit: 5, maxItems: 15}}`, no `orderBy`.
   - Code: `search_executor.dart:373-414`; `query_builder.dart:1024-1026`.
   - Rows come back in table order, so a new household is last.
   - Nothing in the SQL needs the household to have members, so a consent-No household counts as one of the 5.
2. **The card builder then drops households without an active member.** The live config's `wrapperConfig` has a top-level filter: a `HouseholdMemberModel` joined on `householdClientReferenceId` with `isDeleted == false`. `WrapperBuilder.build()` skips any household that fails it (`wrapper_builder.dart:71-74`). A consent-No household has no members, so 5 rows become 4 cards (3 at C, where 2 of the first 5 rows have no member; one is QAID-X4-A).
3. **The app counts cards, not rows.** On the first load, `loadedCount = newWrapper.length`, the number of cards built (`flow_crud_bloc.dart:116-118`; also line 221 for later pages).
4. **A short count means "end of list".** `hasMoreDown = loadedCount >= limit` (`search_state_manager.dart:128`, also line 133), so 3 or 4 cards against 5 gives `false`.
5. **No further page is ever requested.** `prepareLoadDown()` returns null when `hasMoreDown` is false ("Cannot load down - no more data", `search_state_manager.dart:465-471`). Everything after the first 5 rows, including the household just registered, is never loaded.

**Why typing a name works:** the name filter is on the individual, so the SQL only returns households that have a person, and memberless households never take a slot. NB3 at F: consent-No + 5 normal, the 5th missing. Control NB4: 6 normal, all shown.

**Why it showed on a clean phone:** with only your own household(s) in range, no memberless household is among the first 5 rows.

**Fix options for the dev:**
- (a) Decide `hasMoreDown` from the number of rows the query returned (or the total count), not the number of cards.
- (b) Apply the "has an active member" condition in the SQL (a cross-table filter), so the page and the cards agree.
- (c) Also order Near by by distance (B5).

B2-B4 (skips, duplicates and the lost top while scrolling with a name typed) also happen when no household is dropped, so they have a further cause in the two-way window and offset handling. That is not traced yet.

### B1 root cause: a consent-No household in range cuts the list short

Controlled test at an empty spot F (30 km south of C), `artifacts/proximity/runs/20261106-NB3/` (`nb3.log`):

| Step at F | In the plain Near by list right after registering? |
| --- | --- |
| QAID-NB3-X saved with **consent No** (household with no members) | - |
| QAID-NB3-1, -2, -3, -4 (normal) | yes, each |
| **QAID-NB3-5** (normal) | **no** - the list shows NB3-1 to -4 and stops; scrolling loads nothing |
| Control: Near by + `QAID-NB3` typed | all 5 listed |

Near by loads 5 households per page. The consent-No household fills one of the first 5 slots but is not shown (it has no members to show). So the first page shows 4. **The app reads a short page as "no more results" and never loads page 2**, so the 5th household never shows.

The same happens at C: consent-No QAID-X4-A (2026-11-02, case X4) sits just before QAID-X4-B, and the plain list stops at X4-B with 3 shown.

**Control (E-04)** at a second empty spot G (30 km north of C, no consent-No household), `artifacts/proximity/runs/20261106-NB4/` (`nb4.log`):
- 6 normal households, QAID-NB4-1 to -6.
- Each was in the plain Near by list right after registering.
- The list shows all 6; the 6th loads as page 2.

So paging works until a household that isn't shown takes a slot in a page.

In the field, every consent-No (refused) household within range can push a just-registered household out of Near by. Typing a name avoids it, because the name filter leaves out households without members.

### Moving check (QA's request): lat/long saved correctly, Near by right after registering

The GPS was moved between registrations (`adb emu geo fix`), without restarting the app. Search Beneficiary was reopened at the same spot right after each registration, and Near by switched on. Evidence: `artifacts/proximity/runs/20261106-NB2/` (`moving.log`; saved lat/long read from the upload log with `proximity/scripts/saved-latlong.py`).

| Household | ID | GPS when registered | Saved lat, long | Saved = actual? | In the plain Near by list at once? | Found by name, Near by on? |
| --- | --- | --- | --- | --- | --- | --- |
| QAID-NB2-C | 152221510108 | C 10.522200, 7.438800 | 10.5221983, 7.4387983 | **yes** (0 m) | **no** - B1 (45 others at this spot) | yes |
| QAID-NB2-1KM | 161124117218 | 1 km N | 10.5311917, 7.4387983 | **yes** (0 m) | yes (the only one in range) | yes |
| QAID-NB2-4K9 | 154311151422 | 4.9 km N | 10.5662667, 7.4387983 | **yes** (0 m) | yes | yes |
| QAID-NB2-5K1 | 152137216415 | 5.1 km N | 10.568065, 7.4387983 | **yes** (0 m) | yes | yes |
| QAID-NB2-10KM | 157181715910 | 10 km N | 10.6121317, 7.4387983 | **yes** (0 m) | yes | yes |

From C afterwards (Near by + `QAID-NB2`): only NB2-C listed. 1KM and 4K9 were expected (within 5 km) but are **not listed** - B8. 5K1 and 10KM are not listed, as expected.

**So:**
- Location capture is right, also while moving.
- Right after registering, the new household shows under Near by **only when few households are in range** - just like QA's clean phone.
- Where many households are in range (C), it doesn't show (B1).
- Anything more than ~85 m away never shows (B8).

**Why QA saw "missing, then it showed, then others were missing":** B1 hides everything after the first page. Typing a name narrows the list, so a named household shows. While scrolling, B2-B4 skip some households, show others twice, and drop the top of the list. What you see depends on how you scrolled and what you typed. The location filter itself is correct for these records: from 50 km away, Near by + `QAID-P5` finds nothing (`4-reopen-50km`); from C it finds P5-A.

**Workaround for the field until fixed:** switch Near by on **and type the household head's name**. Results then fit in one page and the location filter applies.

## 2. Test data

Use the emulator's GPS to put households at exact distances. Set the point with `adb -s emulator-5554 emu geo fix <lon> <lat>` before capturing Household Location, then go back to the centre C before searching. Name households `QAID-NB-<case>-<letter>`.

| Point | Distance from C | In box | In 5 km circle | `geo fix` (lon lat) |
| --- | --- | --- | --- | --- |
| C (centre) | 0 | yes | yes | `7.438800 10.522200` |
| 50 m N | 0.05 km | yes | yes | `7.438800 10.522650` |
| 1 km N | 1.0 km | yes | yes | `7.438800 10.531193` |
| 4.9 km N | 4.9 km | yes | yes | `7.438800 10.566267` |
| 5.0 km N | 5.0 km | yes | yes (edge) | `7.438800 10.567166` |
| 5.1 km N | 5.1 km | no | no | `7.438800 10.568065` |
| 4.9 km E | 4.9 km | yes | yes | `7.483620 10.522200` |
| 5.1 km E | 5.1 km | no | no | `7.485450 10.522200` |
| Corner NE | 6.36 km | **yes** | **no** | `7.479962 10.562669` |
| 7 km NE | 7.35 km | no | no | `7.486365 10.568965` |
| 10 km N | 10 km | no | no | `7.438800 10.612132` |

On a real phone use real distances (walk or drive), or register at the office and search from 5+ km away.

## 3. Test cases

Priority: **P1** = run before the release (aimed at the reported issue); P2 = run if time allows; P3 = later.

### Positive

| ID | Pri | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| P-01 | P1 | Clean install, nothing downloaded | Register H at C -> Search -> Near by on | H listed (QA saw: pass) |
| P-02 | P1 | Rigan Ori downloaded (153) | Register H at C -> Search -> Near by on -> scroll to the end | **H listed** (QA saw: fail) |
| P-03 | P1 | As P-02 | Sync Data -> Search -> Near by on | H listed |
| P-04 | P1 | As P-02 | Near by on + type H's name | H listed |
| P-05 | P2 | Clean install | Households at 50 m, 1 km, 4.9 km N, 4.9 km E -> search from C | All 4 listed |
| P-06 | P2 | Clean install | Household at exactly 5.0 km N | Listed (`<=` radius) |
| P-07 | P1 | Airplane mode | Register H offline -> Near by on (no sync) | H listed (search is on the phone's own data) |
| P-08 | P2 | 3 households in range (fewer than 5) | Near by on | All 3 on the first screen |
| P-09 | P2 | Household registered on another device in range, then downloaded here | Near by on | Listed |
| P-10 | P2 | H has 3 members | Near by on | H appears once (one card per household, not per member) |
| P-11 | P1 | Near by on | Switch Near by off | List goes back to the normal search; H findable by name |
| P-12 | P2 | Search opened at C; phone moved 10 km | Close Search, open it again -> Near by on | Results are for the new position |
| P-13 | P2 | H has members added after registration (members have null lat/long, F9) | Near by on | H still listed |

### Negative

| ID | Pri | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| N-01 | P1 | Household at 5.1 km N, another at 5.1 km E | Near by on at C | Neither listed |
| N-02 | P2 | Household at 10 km N | Near by on at C | Not listed |
| N-03 | P1 | Location off | Open Search | Switch disabled; the user is told why (check whether any message shows) |
| N-04 | P2 | Location permission denied for the app | Open Search | Switch disabled; message or prompt to allow location |
| N-05 | P1 | Rigan Ori downloaded | Count the downloaded households whose lat/long is empty or 0,0 (Household Overview, or the DB in this "-db" build) | Each one is never listed under Near by (F7). Report the count - field records without GPS can't be found this way |
| N-06 | P2 | H deleted | Near by on | H not listed |
| N-07 | P2 | Near by on | Type a name that exists only 10 km away | No results; clear "no match" state |
| N-08 | P2 | No households within 5 km | Near by on | Empty state, no error or endless spinner |
| N-09 | P3 | Household in another project, in range | Near by on | Not listed |

### Edge (most likely to explain the issue)

| ID | Pri | Precondition | Steps | Expected |
| --- | --- | --- | --- | --- |
| E-01 | **P1** | Rigan Ori downloaded + H registered | Near by on -> scroll to the end; write down every household in order | Every household within 5 km appears **exactly once**; total = households in range; H is among them |
| E-02 | **P1** | As E-01 | Note H's position. Repeat with H2, H3 registered one after another | Each new household reachable. **Ask product:** should the newest or nearest be first? Today there is no order (F3) |
| E-03 | **P1** | 16+ households in range | Scroll down past 15 (top ones are trimmed), then scroll back to the top | No household skipped or shown twice, either way; the first 5 match the first screen before scrolling |
| E-04 | **P1** | Exactly 6 households in range, on a tall screen where 5 cards may fit without scrolling | Near by on -> try to scroll | The 6th loads. Risk: if the list can't scroll, "load more" never fires |
| E-05 | P1 | Households at 0 m (H), 1 km and 4.9 km | Near by on | **Ask product:** nearest first? Today no order (F3) |
| E-06 | **P1** | Rigan Ori downloaded + H | Same Near by search 3 times: (a) at once, (b) after reopening Search, (c) after killing and relaunching the app | Same households in the same order |
| E-07 | **P1** | Rigan Ori downloaded + H synced | Note the first 15 -> Sync Data (or download Rigan Ori again) -> Near by on | Same set; nobody drops out. Tests "later H showed, others went missing" |
| E-08 | P2 | Household at Corner NE (6.36 km) | Near by on at C | Per code it **is listed** (F4). A bug if "5 km" means a circle - confirm with the dev |
| E-09 | P1 | Search opened at C | Without leaving Search, move the GPS 10 km -> switch Near by on (and off/on) | Per code results stay centred on C (F5). Decide whether that is acceptable |
| E-10 | P1 | Household within 5 km but in another Fangwani village; Rigan Ori selected | Near by on | Config says village filter; code drops it (F8): **expect it listed**. Confirm the intended behaviour |
| E-11 | **P1** | Near by on | Register H from this Search screen -> return to Search | Near by still on (or clearly off); list refreshed and includes H |
| E-12 | P2 | Near by on | Switch on/off/on quickly | Final list matches the final switch state; no stale or mixed results |
| E-13 | P2 | Near by on | Turn on Search by ID, enter H's ID | Defined behaviour: H found, or Near by turned off (confirm) |
| E-14 | P2 | Near by on + name typed | Switch Near by off | Name filter kept; results for the name only (code removes only the Near by filter) |
| E-15 | P2 | 153 households in range | Near by on, scroll through all | No freeze or crash; each page < 1 s (`[QueryPerf]`) |
| E-16 | P2 | 5 households at the same point (C) | Near by on | All 5 listed |
| E-17 | P2 | H at C | Edit H's location to 10 km N -> Near by at C; edit back | Drops out, then returns |
| E-18 | P2 | Household Location "Lat/Long" | Capture with low accuracy (100 m+), or enter swapped or 0,0 values if the field can be edited | Swapped or 0,0 values are refused, or the household is never "near by" - record which |
| E-19 | P3 | Near by on mid-scroll | Kill app -> relaunch -> Search -> Near by | List rebuilt from the top; nothing missing |

## 4. Open questions for the dev / product

1. Should Near by households be **sorted by distance** (nearest first)? With 5 per page and no order, a household standing next to the worker can be on page 30. (F3)
2. Should Near by **keep the village filter**? The config asks for it; the widget drops it. (F8)
3. Is the radius meant as a circle? The household search uses a square, so it reaches 7.07 km at the corners. (F4)
4. Should the search centre update while the screen is open? Today it is the first fix only. (F5)

## 5. Results

| ID | Date | Device | Result | Notes |
| --- | --- | --- | --- | --- |
| P-01 | 2026-11-06 | QA phone | PASS | Reported by QA |
| P-02 | 2026-11-06 | QA phone | FAIL | Reported by QA: H not listed after downloading 153; later listed, others missing |
| P-02 | 2026-11-06 14:08 | emulator-5554 | **FAIL** | After downloading 153: QAID-NB1-A (ID 152215121414) registered at C is not in the Near by list (3 households shown) - B1 |
| P-04 | 2026-11-06 14:09 | emulator-5554 | PASS | Near by on + `QAID-NB1` finds NB1-A |
| E-01 | 2026-11-06 14:00, 14:09 | emulator-5554 | **FAIL** | Plain Near by: 3 households, no more pages - B1 |
| E-03 | 2026-11-06 14:16 | emulator-5554 | **FAIL** | Down skips 6, up shows them plus a duplicate, top unreachable - B2, B3, B4 |
| E-05 | 2026-11-06 14:16 | emulator-5554 | FAIL (if nearest-first is required) | Oldest first; the newest and nearest is last - B5 |
| E-11 | 2026-11-06 14:08 | emulator-5554 | PASS | Back from Household Overview: Search reset, Near by off, field empty |
| N-02 | 2026-11-06 14:05 | emulator-5554 | PASS | 50 km from C: Near by + `QAID-P5` finds nothing |
| Moving | 2026-11-06 14:25-14:42 | emulator-5554 | PASS (lat/long) | 5 households at 0 / 1 / 4.9 / 5.1 / 10 km: each saved at exactly the phone's position |
| P-05 | 2026-11-06 14:43 | emulator-5554 | **FAIL** | From C: households 1 km and 4.9 km away not listed - B8 |
| N-01 | 2026-11-06 14:43 | emulator-5554 | PASS | From C: 5.1 km and 10 km not listed |
| P-06 / E-08 | - | - | NOT RUN | Moot until the radius is settled (B8) |
| Radius | 2026-11-06 14:45-14:58 | emulator-5554 | **FAIL** | Found at 80 m, not at 90 m - B8 |
| E-09 | 2026-11-06 15:06 | emulator-5554 | **FAIL** | Moved 10 km with Search open: Near by still searches the old spot, also after off/on - B9 |
| E-14 | 2026-11-06 15:07 | emulator-5554 | **FAIL** | Near by off/on cleared the typed name - B10 |
| B1 cause | 2026-11-06 15:09-15:36 | emulator-5554 | **FAIL** | Consent-No household + 5 normal at F: the 5th never shows in plain Near by; shows with the name typed |
| E-04 | 2026-11-06 15:37-15:58 | emulator-5554 | PASS | 6 normal households at G, no consent-No: all 6 listed, page 2 loads (control for B1) |
| P-02 clean start (QA's steps) | 2026-11-06 16:24-16:40 | emulator-5554 | **FAIL** | Sync + logout → **storage cleared** → sign in → Rigan Ori downloaded (dialog total 153) → **Swathi Ghanate, consent Yes** (ID 152122513211) → Back to Search → Near by on: only QAID-FIX-E1, FIX-E2, X4-B; Swathi Ghanate missing. "Swathi" typed with Near by on: listed. `artifacts/proximity/runs/20261106-NB6/` - B1 |
| Download | 2026-11-06 16:30 | emulator-5554 | Observation | The download still totals 153 (as at 13:55) and left out households synced to Rigan Ori today: the 16:14 Swathi Ghanate (161221817591) is not on the device. Ask the dev whether the download list is refreshed on a schedule |
| P-02 (QA's manual steps) | 2026-11-06 16:14-16:19 | emulator-5554 | **FAIL** | Rigan Ori downloaded → registered **Swathi Ghanate** (ID 161221817591) at C → Back to Search → Near by on: only QAID-FIX-E1, FIX-E2, X4-B listed, Swathi Ghanate missing (scrolled to the end). Same screen, "Swathi" typed: Swathi Ghanate listed (the only one - other downloaded "swathi" records are far away). `artifacts/proximity/runs/20261106-NB5/` - B1 |
