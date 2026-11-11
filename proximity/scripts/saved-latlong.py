"""Read the lat/long each test household was saved with, from the app's log.

proximity/PROXIMITY-CASES.md moving check: the Household Location page shows only the
fix's accuracy, so the saved coordinates are read from the request bodies the
app logs when it syncs (Sync Data). For every individual whose given name
starts with PREFIX, prints the latitude/longitude of their address, and
compares it with the expected point when EXPECT is given.

    python -I proximity/scripts/saved-latlong.py <device-logcat.txt> QAID-NB2- [NAME=lat,lon ...]
"""
import math
import re
import sys

path, prefix = sys.argv[1], sys.argv[2]
expect = {}
for a in sys.argv[3:]:
    name, ll = a.split("=")
    lat, lon = (float(x) for x in ll.split(","))
    expect[name] = (lat, lon)


def km(a, b):
    p = math.pi / 180
    x = (math.sin((b[0] - a[0]) * p / 2) ** 2
         + math.cos(a[0] * p) * math.cos(b[0] * p) * math.sin((b[1] - a[1]) * p / 2) ** 2)
    return 2 * 6371.0 * math.atan2(math.sqrt(x), math.sqrt(1 - x))


text = []
with open(path, encoding="utf-8", errors="replace") as f:
    for line in f:
        m = re.search(r"I/flutter\s*\(\s*\d+\): (.*)$", line)
        if m:
            text.append(m.group(1).rstrip())

found = {}
name = None
for line in text:
    g = re.search(r'"givenName": "([^"]*)"', line)
    if g:
        name = g.group(1).strip()
        continue
    if name and name.startswith(prefix):
        la = re.search(r'"latitude": (null|-?[\d.]+)', line)
        if la:
            found.setdefault(name, {"lat": la.group(1)})
            continue
        lo = re.search(r'"longitude": (null|-?[\d.]+)', line)
        if lo and name in found and "lon" not in found[name]:
            found[name]["lon"] = lo.group(1)
            name = None

print(f"{'household head':<22} {'saved lat':>12} {'saved lon':>12}   check")
for n in sorted(found):
    lat, lon = found[n]["lat"], found[n].get("lon", "?")
    key = n.replace(prefix, "")
    verdict = ""
    if key in expect and lat not in ("null", "?") and lon not in ("null", "?"):
        d = km(expect[key], (float(lat), float(lon))) * 1000
        verdict = f"{'OK' if d <= 50 else 'WRONG'} - {d:.0f} m from where the phone was"
    elif lat == "null":
        verdict = "NO COORDINATES"
    print(f"{n:<22} {lat:>12} {lon:>12}   {verdict}")
missing = [k for k in expect if prefix + k not in found]
if missing:
    print("Not in this log:", ", ".join(missing))
