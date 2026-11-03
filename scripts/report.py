"""Records test-plan case results and builds the report from them.

  python scripts/report.py record --case P1 --run-dir <dir> --exit-code 0 \
      --reallocated 1 --phone <serial> --user <cdd>
  python scripts/report.py build

record reads what the case's flow logged (the JsConsole lines in each
maestro.log under --run-dir), decides the result, appends it to
artifacts/results.csv and the IDs the case gave out to artifacts/ledger.csv,
then runs build. Recording a run folder again replaces its earlier rows.

  PASS        every expected result met
  FAIL        an expected result not met, the log check off, or a duplicate ID
  BLOCKED     a precondition was missing; nothing was judged
  INCOMPLETE  the run stopped before its checks (Maestro failed or lost the
              phone) - not a verdict on the app; re-run it build writes artifacts/report/results.xlsx and report.html
and the Result / Comments columns of TEST-CASES.md, from the latest result
of each case.

Flows talk to this script through console.log lines, one per fact:
  LEDGER|<id or UUID>|<person>|<household>   a person and the ID they got
  CHECK|PASS|<text>  or  CHECK|FAIL|<text>   one expected result, met or not
  BLOCKED|<text>                             a precondition was not met
  NOTE|<text>                                anything else worth a comment
"""

import argparse
import csv
import datetime
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "scripts" / "cases.csv"
RESULTS = ROOT / "artifacts" / "results.csv"
LEDGER = ROOT / "artifacts" / "ledger.csv"
REPORT_DIR = ROOT / "artifacts" / "report"
TRACKER = ROOT / "TEST-CASES.md"

RESULT_FIELDS = ["Case", "Result", "Comments", "RunDate", "Evidence"]
LEDGER_FIELDS = ["ID", "Person", "Household", "Case", "Phone", "CddUser", "RunDate"]
POOL_ID = re.compile(r"^\d{12}$")


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerows(rows)


TAGGED = re.compile(r"^([A-Za-z0-9]+):(CHECK|NOTE|BLOCKED)\|")


def flow_lines(run_dir, tag=""):
    """The flow's JsConsole messages, Maestro's reason when a step failed, and
    the last step started (all there is when Maestro loses the phone).

    With tag, only the lines tagged for that case ("X2:CHECK|..."), untagged;
    without, only the untagged ones. A part Maestro lost and run-case.ps1 ran
    again (a "<part>.lost-<n>" folder) keeps only its LEDGER lines: the IDs
    it gave out are real, its checks are repeated by the run that finished."""
    messages, failure, last_step = [], "", ""
    for log in sorted(Path(run_dir).rglob("maestro.log")):
        lost = ".lost-" in str(log)
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"JsConsole: (.*)$", line)
            if m:
                msg = m.group(1).strip()
                t = TAGGED.match(msg)
                if tag:
                    if t and t.group(1) == tag:
                        messages.append(msg[len(tag) + 1:])
                    continue
                if t or (lost and not msg.startswith("LEDGER|")):
                    continue
                messages.append(msg)
                continue
            if lost:
                continue
            # An optional step that timed out logs "CommandWarned: Assertion
            # is false" - not why the part stopped.
            if "CommandWarned" in line:
                continue
            m = re.search(r"(Assertion is false: .*|Element not found: .*)$", line)
            if m and not failure:
                failure = m.group(1).strip()
            m = re.search(r"onCommandFinished: (.*) FAILED$", line)
            if m and not failure:
                failure = "step failed: " + m.group(1).strip()
            m = re.search(r"onCommandStart: (.*) RUNNING$", line)
            if m:
                last_step = m.group(1).strip()
    return messages, failure, last_step


def run_date_of(run_dir):
    """When the run started, from its folder name (yyyyMMdd-HHmmss-<case>)."""
    m = re.search(r"(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})\d{2}", Path(run_dir).name)
    if m:
        return f"{m[1]}-{m[2]}-{m[3]} {m[4]}:{m[5]}"
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def rewrite_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def record(a):
    cases = {c["Case"]: c for c in read_csv(CASES)}
    if a.case not in cases:
        sys.exit(f"Unknown case {a.case} - see scripts/cases.csv.")
    run_date = run_date_of(a.run_dir)
    messages, failure, last_step = flow_lines(a.run_dir, a.tag)
    run_path = Path(a.run_dir).resolve()
    evidence = str(run_path.relative_to(ROOT)) if run_path.is_relative_to(ROOT) else a.run_dir

    # Recording a run again replaces what it recorded for this case before.
    # One run can hold two cases (X1 and X2), so the case is part of the key.
    def same(r):
        return r["Evidence"] == evidence and r["Case"] == a.case
    old = [r for r in read_csv(RESULTS) if same(r)]
    if old:
        rewrite_csv(RESULTS, RESULT_FIELDS, [r for r in read_csv(RESULTS) if not same(r)])
        stale = {(r["Case"], r["RunDate"]) for r in old}
        rewrite_csv(LEDGER, LEDGER_FIELDS, [r for r in read_csv(LEDGER) if (r["Case"], r["RunDate"]) not in stale])

    passed, failed, blocked, notes, people = [], [], [], [], []
    for msg in messages:
        parts = msg.split("|")
        kind = parts[0]
        if kind == "LEDGER" and len(parts) >= 4:
            # The 5th field, when there, is the device that gave the ID.
            people.append({"ID": parts[1].strip(), "Person": parts[2].strip(),
                           "Household": parts[3].strip(),
                           "Phone": parts[4].strip() if len(parts) >= 5 else ""})
        elif kind == "CHECK" and len(parts) >= 3:
            (passed if parts[1] == "PASS" else failed).append("|".join(parts[2:]))
        elif kind == "BLOCKED":
            blocked.append("|".join(parts[1:]))
        elif kind == "NOTE":
            notes.append("|".join(parts[1:]))

    # Log check: the reallocated lines the case expects (scripts/cases.csv).
    # A log with no UPDATE_IDENTIFIER_STATUS line at all says nothing about
    # reallocation - the build does not log it - so the check is reported as
    # not run rather than failed.
    expected = cases[a.case]["Reallocated"].strip()
    log_note = f"Log: {a.id_lines} UPDATE_IDENTIFIER_STATUS line(s), {a.reallocated} reallocated"
    if expected:
        log_note += f" (expected {expected})"
        if a.id_lines == 0:
            log_note += " - log check not run, no UPDATE_IDENTIFIER_STATUS line in this run's log"
        elif a.reallocated != int(expected):
            failed.append(f"Log check - expected {expected} reallocated line(s), found {a.reallocated}")

    # The ID each form carried at Submit (the search screen's pre-loaded ID,
    # from the app's CONDITION_EVAL log line - see run-case.ps1), against the
    # ID the person was saved with. A form offered an ID already saved for
    # someone else is the stale-screen bug reproduced; saving a different ID
    # is the fix catching it.
    offered = dict(kv.split("=", 1) for kv in a.offered.split(";") if "=" in kv)
    saved = {p["Person"]: p["ID"] for p in people}
    if offered:
        parts = []
        for name, oid in offered.items():
            person = next((p for p in saved if p == name or p.startswith(name + " ")), None)
            text = f"{name} offered {oid}"
            owner = next((p for p, sid in saved.items() if sid == oid and p != person), None)
            if owner:
                text += f" (the ID saved for {owner})"
            if person and saved[person] != oid:
                text += f", saved as {saved[person]}"
            parts.append(text)
        notes.append("At Submit - " + "; ".join(parts))

    # ID ledger: a 12-digit ID already given to someone else is a duplicate,
    # and the case that made the second row fails.
    earlier = read_csv(LEDGER)
    seen = {}
    for row in earlier:
        if POOL_ID.match(row["ID"]):
            seen.setdefault(row["ID"], f'{row["Person"]} ({row["Case"]})')
    for p in people:
        if POOL_ID.match(p["ID"]):
            if p["ID"] in seen and not seen[p["ID"]].startswith(p["Person"] + " "):
                failed.append(f'Duplicate ID {p["ID"]}: {p["Person"]} got the ID already given to {seen[p["ID"]]}')
            seen.setdefault(p["ID"], f'{p["Person"]} ({a.case})')

    # A flow that stopped without a failed check never reached its expected
    # results: that is the automation's failure, not the app's.
    if blocked:
        result = "BLOCKED"
    elif failed:
        result = "FAIL"
    elif a.exit_code != 0:
        result = "INCOMPLETE"
    else:
        result = "PASS"

    # Every expected result is in the comment, met or not, with what was
    # found - a PASS shows its evidence too.
    comments = []
    if result == "BLOCKED":
        comments += blocked
    comments += [f"NOT MET - {t}" for t in failed]
    comments += [f"Met - {t}" for t in passed]
    if result == "INCOMPLETE":
        reason = ("Maestro: " + failure) if failure else \
            f"Maestro lost the phone during step '{last_step}'"
        comments.append(f"Run stopped before its checks - {reason}. Not a verdict on the app; re-run")
    elif a.exit_code != 0 and failure and not blocked:
        comments.append("Maestro: " + failure)
    comments += notes
    comments.append(log_note)

    append_csv(RESULTS, RESULT_FIELDS, [{
        "Case": a.case, "Result": result, "Comments": ". ".join(c.rstrip(".") for c in comments) + ".",
        "RunDate": run_date, "Evidence": evidence,
    }])
    append_csv(LEDGER, LEDGER_FIELDS, [dict(p, Case=a.case, Phone=p["Phone"] or a.phone, CddUser=a.user,
                                            RunDate=run_date)
                                       for p in people])
    print(f"{a.case}: {result}")
    build()


def latest_results():
    latest = {}
    for row in read_csv(RESULTS):
        latest[row["Case"]] = row
    return latest


def build():
    cases = read_csv(CASES)
    latest = latest_results()
    ledger = read_csv(LEDGER)
    counts = {}
    for row in ledger:
        if POOL_ID.match(row["ID"]):
            counts[row["ID"]] = counts.get(row["ID"], 0) + 1
    rows = []
    for c in cases:
        r = latest.get(c["Case"], {})
        rows.append({"Case": c["Case"], "Name": c["Name"], "Phase": c["Phase"],
                     "Result": r.get("Result", "NOT RUN"), "Comments": r.get("Comments", ""),
                     "RunDate": r.get("RunDate", ""), "Evidence": r.get("Evidence", "")})
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_xlsx(rows, ledger, counts)
    write_html(rows, ledger, counts)
    write_tracker(rows, ledger, counts)
    print(f"Report: {REPORT_DIR / 'results.xlsx'} and {REPORT_DIR / 'report.html'}")


def summary(rows):
    order = ["PASS", "FAIL", "BLOCKED", "INCOMPLETE", "NOT RUN"]
    return [(k, sum(1 for r in rows if r["Result"] == k)) for k in order]


def write_xlsx(rows, ledger, counts):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    fills = {"PASS": "C6EFCE", "FAIL": "FFC7CE", "BLOCKED": "FFEB9C", "INCOMPLETE": "DDEBF7", "NOT RUN": "EDEDED"}
    bold = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")

    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(["#", "Case", "Phase", "Result", "Comments", "Run date", "Evidence"])
    for r in rows:
        ws.append([r["Case"], r["Name"], r["Phase"], r["Result"], r["Comments"], r["RunDate"], r["Evidence"]])
        ws.cell(ws.max_row, 4).fill = PatternFill("solid", fgColor=fills[r["Result"]])
    for col, width in zip("ABCDEFG", (6, 40, 8, 10, 90, 17, 45)):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap
    for cell in ws[1]:
        cell.font = bold
    ws.freeze_panes = "A2"

    wl = wb.create_sheet("ID ledger")
    wl.append(["ID", "Person", "Household", "Case", "Phone", "CDD user", "Run date", "Duplicate"])
    for row in ledger:
        dup = counts.get(row["ID"], 0) > 1
        wl.append([row["ID"], row["Person"], row["Household"], row["Case"], row["Phone"], row["CddUser"],
                   row["RunDate"], "YES" if dup else ""])
        if dup:
            for cell in wl[wl.max_row]:
                cell.fill = PatternFill("solid", fgColor=fills["FAIL"])
    for col, width in zip("ABCDEFGH", (16, 18, 18, 7, 18, 16, 17, 10)):
        wl.column_dimensions[col].width = width
    for cell in wl[1]:
        cell.font = bold
    wl.freeze_panes = "A2"

    wsum = wb.create_sheet("Summary")
    wsum.append(["Result", "Cases"])
    for k, n in summary(rows):
        wsum.append([k, n])
    wsum.append(["Total", len(rows)])
    for cell in wsum[1]:
        cell.font = bold

    wb.save(REPORT_DIR / "results.xlsx")


def write_html(rows, ledger, counts):
    e = html.escape
    tiles = "".join(f'<div class="tile {k.replace(" ", "-").lower()}"><b>{n}</b><span>{k}</span></div>'
                    for k, n in summary(rows))
    body = "".join(
        f'<tr><td>{e(r["Case"])}</td><td>{e(r["Name"])}</td><td>{e(r["Phase"])}</td>'
        f'<td><span class="badge {r["Result"].replace(" ", "-").lower()}">{e(r["Result"])}</span></td>'
        f'<td>{e(r["Comments"])}</td><td>{e(r["RunDate"])}</td><td>{e(r["Evidence"])}</td></tr>'
        for r in rows)
    led = "".join(
        f'<tr class="{"dup" if counts.get(x["ID"], 0) > 1 else ""}"><td>{e(x["ID"])}</td><td>{e(x["Person"])}</td>'
        f'<td>{e(x["Household"])}</td><td>{e(x["Case"])}</td><td>{e(x["Phone"])}</td><td>{e(x["CddUser"])}</td>'
        f'<td>{e(x["RunDate"])}</td><td>{"YES" if counts.get(x["ID"], 0) > 1 else ""}</td></tr>'
        for x in ledger) or '<tr><td colspan="8">No IDs recorded yet.</td></tr>'
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Beneficiary ID Fix Results</title>
<style>
:root {{ --bg:#fff; --fg:#1d2329; --muted:#5b6670; --line:#d9dee3; --pass:#1e7b34; --pass-bg:#e3f4e6;
  --fail:#b3261e; --fail-bg:#fbe4e2; --blocked:#8a5a00; --blocked-bg:#fdf1d8; --notrun:#5b6670; --notrun-bg:#eef0f2;
  --incomplete:#1f5a8a; --incomplete-bg:#e3eef8; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#15191d; --fg:#e6e9ec; --muted:#9aa4ad; --line:#2c333a;
  --pass:#7bd88f; --pass-bg:#1b3322; --fail:#ff9a92; --fail-bg:#3d1f1d; --blocked:#f2c66d; --blocked-bg:#3a2f16;
  --notrun:#9aa4ad; --notrun-bg:#24292e; --incomplete:#8cc4f2; --incomplete-bg:#1a2c3d; }} }}
body {{ margin:0; padding:24px 16px; background:var(--bg); color:var(--fg); font:14px/1.45 system-ui, sans-serif; }}
main {{ max-width:1200px; margin:0 auto; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:28px 0 8px; }}
.sub {{ color:var(--muted); margin:0 0 16px; }}
.tiles {{ display:flex; flex-wrap:wrap; gap:8px; }}
.tile {{ border:1px solid var(--line); border-radius:8px; padding:8px 14px; min-width:90px; }}
.tile b {{ display:block; font-size:22px; }} .tile span {{ color:var(--muted); font-size:12px; }}
.wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; }}
th, td {{ border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }}
th {{ font-size:12px; color:var(--muted); font-weight:600; }}
.badge {{ font-weight:600; font-size:12px; padding:2px 8px; border-radius:10px; white-space:nowrap; }}
.pass {{ color:var(--pass); background:var(--pass-bg); }} .fail {{ color:var(--fail); background:var(--fail-bg); }}
.blocked {{ color:var(--blocked); background:var(--blocked-bg); }} .not-run {{ color:var(--notrun); background:var(--notrun-bg); }}
.incomplete {{ color:var(--incomplete); background:var(--incomplete-bg); }}
tr.dup td {{ background:var(--fail-bg); }}
</style></head><body><main>
<h1>Beneficiary ID Fix - QA results</h1>
<p class="sub">Kaduna fix build 2.2.120 (org.egov.azm.gombe) &middot; generated {stamp}</p>
<div class="tiles">{tiles}</div>
<h2>Results</h2>
<div class="wrap"><table><thead><tr><th>#</th><th>Case</th><th>Phase</th><th>Result</th><th>Comments</th><th>Run date</th><th>Evidence</th></tr></thead>
<tbody>{body}</tbody></table></div>
<h2>ID ledger</h2>
<div class="wrap"><table><thead><tr><th>ID</th><th>Person</th><th>Household</th><th>Case</th><th>Phone</th><th>CDD user</th><th>Run date</th><th>Duplicate</th></tr></thead>
<tbody>{led}</tbody></table></div>
</main></body></html>
"""
    (REPORT_DIR / "report.html").write_text(page, encoding="utf-8")


def write_tracker(rows, ledger, counts):
    """Fills TEST-CASES.md's Result and Comments columns for cases that ran,
    and its ID ledger table (the rows under the table's header, from
    artifacts/ledger.csv; a duplicate ID is marked)."""
    if not TRACKER.exists():
        return
    by_case = {r["Case"]: r for r in rows if r["Result"] != "NOT RUN"}
    out = []
    in_ledger = False
    for line in TRACKER.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_ledger = line.strip() == "## ID ledger"
        if in_ledger and line.startswith("| ") and not line.startswith("| ID ") and not line.startswith("| ---"):
            continue  # an old ledger row: written afresh below
        cells = line.split(" | ")
        m = re.match(r"^\| (\w+)$", cells[0]) if cells else None
        if m and m.group(1) in by_case and len(cells) == 6:
            r = by_case[m.group(1)]
            note = f'{r["Comments"]} Run {r["RunDate"]}, {r["Evidence"]}'.replace("|", "/")
            cells[4] = r["Result"]
            cells[5] = note + " |"
            line = " | ".join(cells)
        out.append(line)
        if in_ledger and line.startswith("| ---"):
            for x in ledger:
                pid = x["ID"] + (" (DUPLICATE)" if counts.get(x["ID"], 0) > 1 else "")
                out.append(f'| {pid} | {x["Person"]} | {x["Household"]} | {x["Case"]} | {x["Phone"]} | '
                           f'{x["CddUser"]} | {x["RunDate"]} |')
    TRACKER.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--case", required=True)
    r.add_argument("--run-dir", required=True)
    r.add_argument("--exit-code", type=int, required=True)
    r.add_argument("--reallocated", type=int, required=True)
    r.add_argument("--id-lines", type=int, required=True)
    r.add_argument("--offered", default="", help="name=id;name=id - the ID each form carried at Submit")
    r.add_argument("--phone", default="")
    r.add_argument("--user", default="")
    r.add_argument("--tag", default="", help="record only the lines tagged for this case (X2 inside X1)")
    sub.add_parser("build")
    a = p.parse_args()
    record(a) if a.cmd == "record" else build()


if __name__ == "__main__":
    main()
