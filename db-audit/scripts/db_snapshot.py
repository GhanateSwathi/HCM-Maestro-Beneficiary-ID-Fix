"""Pull the HCM app's local database off a rooted emulator and summarise it.

    python -I db-audit/scripts/db_snapshot.py <serial> <label> [--schema]

Copies /data/data/<app>/app_flutter/db.sqlite with its -wal and -shm files
(the app runs SQLite in WAL mode: recent writes sit in the -wal file until a
checkpoint) into artifacts/db-audit/snapshots/<yyyyMMdd-HHmmss>-<label>/,
opens the copy, and prints the row count of every table. --schema also writes
schema.json (every table with its columns, types and primary key).

Needs root on the device (a google_apis emulator image: `adb root`); a
Play Store image or a phone cannot read another app's files. The app is
HCM_APP_ID from .env (org.egov.azm.gombe by default).
"""
import datetime
import json
import os
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def app_id():
    try:
        for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
            if line.startswith("HCM_APP_ID="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "org.egov.azm.gombe"


def adb(serial, *args, binary=False):
    r = subprocess.run(["adb", "-s", serial, *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def pull(serial, label):
    app = app_id()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(ROOT, "artifacts", "db-audit", "snapshots", f"{stamp}-{label}")
    os.makedirs(out, exist_ok=True)
    base = f"/data/data/{app}/app_flutter/db.sqlite"
    for suffix in ("", "-wal", "-shm"):
        data = adb(serial, "exec-out", "su", "0", "cat", base + suffix, binary=True) if False else \
            adb(serial, "exec-out", "cat", base + suffix, binary=True)
        if data.startswith(b"cat:"):
            continue
        with open(os.path.join(out, "db.sqlite" + suffix), "wb") as f:
            f.write(data)
    return out


def summarise(folder, schema=False):
    con = sqlite3.connect(os.path.join(folder, "db.sqlite"))
    tables = [r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    counts = {}
    for t in tables:
        counts[t] = con.execute(f'select count(*) from "{t}"').fetchone()[0]
    with open(os.path.join(folder, "counts.json"), "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=1)
    if schema:
        sch = {}
        for t in tables:
            cols = con.execute(f'pragma table_info("{t}")').fetchall()
            sch[t] = [{"column": c[1], "type": c[2], "notnull": bool(c[3]), "pk": bool(c[5])} for c in cols]
        with open(os.path.join(folder, "schema.json"), "w", encoding="utf-8") as f:
            json.dump(sch, f, indent=1)
    con.close()
    return counts


if __name__ == "__main__":
    serial, label = sys.argv[1], sys.argv[2]
    folder = pull(serial, label)
    counts = summarise(folder, schema="--schema" in sys.argv)
    print(folder)
    print(f"{len(counts)} tables, {sum(counts.values())} rows; non-empty: " +
          ", ".join(f"{t}={n}" for t, n in counts.items() if n))
