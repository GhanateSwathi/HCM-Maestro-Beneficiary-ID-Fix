"""Record every household on the Search Beneficiary result list, in order.

proximity/PROXIMITY-CASES.md E-01 / E-03: with the result list on screen (e.g. Near
by households switched on), scrolls down to the end and then back to the
top, reading each household card's name from the screen (uiautomator).
Prints the order seen each way, and any household seen twice or only one
way. The list loads 5 households per page as it scrolls (and drops pages
beyond 15), so each swipe waits for the page to load.

    python -I proximity/scripts/nearby-list.py [serial] [out.json]

A household card is the row with an "Open" button; its name is the label
to the left of that button on the same row.
"""
import json
import re
import subprocess
import sys
import time

SERIAL = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
OUT = sys.argv[2] if len(sys.argv) > 2 else None
# One page loads in well under a second ([QueryPerf] on 2.2.120), but the
# software-rendered emulator draws slowly: at 3 s a sweep stopped before
# pages that arrived later (2026-11-06 14:12).
SWIPE_WAIT_S = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
STILL_LIMIT = 4         # this many swipes without a new household = the end
FRAMES = []             # every screen read: (direction, [names top to bottom])


def adb(*args):
    return subprocess.run(["adb", "-s", SERIAL, *args], capture_output=True, check=True).stdout


def screen_households():
    adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
    xml = adb("exec-out", "cat", "/sdcard/ui.xml").decode("utf-8", "replace")
    nodes = []
    for m in re.finditer(r"<node [^>]*>", xml):
        n = m.group(0)
        desc = (re.search(r'content-desc="([^"]*)"', n) or [None, ""])[1]
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
        if b:
            nodes.append((desc, tuple(int(x) for x in b.groups())))
    opens = [bb for d, bb in nodes if d == "Open"]
    names = []
    for d, (x1, y1, x2, y2) in nodes:
        if not d or d == "Open" or "&#10;" in d:
            continue
        cy = (y1 + y2) / 2
        for (ox1, oy1, ox2, oy2) in opens:
            if oy1 <= cy <= oy2 and x2 <= ox1:
                names.append((d, int(cy)))
                break
    return [n for n, _ in sorted(names, key=lambda t: t[1])]


def sweep(direction):
    """Scroll one way to the end; return households in the order first seen."""
    seen, still = [], 0
    while still < STILL_LIMIT:
        on_screen = screen_households()
        FRAMES.append((direction, on_screen))
        new = [n for n in on_screen if n not in seen]
        seen += new
        still = 0 if new else still + 1
        if direction == "down":
            adb("shell", "input", "swipe", "672", "2300", "672", "1100", "700")
        else:
            adb("shell", "input", "swipe", "672", "1100", "672", "2300", "700")
        time.sleep(SWIPE_WAIT_S)
    return seen


def main():
    t0 = time.strftime("%H:%M:%S")
    down = sweep("down")
    up = sweep("up")
    result = {
        "started": t0,
        "down": down,
        "up": up,
        "down_count": len(down),
        "up_count": len(up),
        "only_down": [n for n in down if n not in up],
        "only_up": [n for n in up if n not in down],
        "frames": FRAMES,
    }
    print(f"Scrolled down: {len(down)} households")
    for i, n in enumerate(down, 1):
        print(f"  {i:3}. {n}")
    print(f"Scrolled back up: {len(up)} households (first seen on the way up: {up[:3]} ...)")
    print("Seen only going down:", result["only_down"] or "none")
    print("Seen only going up:", result["only_up"] or "none")
    if OUT:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
