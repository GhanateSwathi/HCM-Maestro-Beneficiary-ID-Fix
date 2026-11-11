"""Print the texts on the device's screen, top to bottom (maestro hierarchy).

    python -I db-audit/scripts/screen.py [emulator-5554] [--bounds]

For looking at a screen while authoring flows without the Maestro MCP
(which cannot share the device with the CLI). Status-bar items are left out.
"""
import json
import os
import subprocess
import sys

JDK = r"C:\Program Files\Amazon Corretto\jdk17.0.20_10"


def texts(node, out):
    attrs = node.get("attributes", {})
    t = attrs.get("text") or attrs.get("accessibilityText") or attrs.get("hintText") or ""
    rid = attrs.get("resource-id", "")
    if t and "systemui" not in rid:
        out.append((attrs.get("bounds", ""), t))
    for c in node.get("children", []):
        texts(c, out)


def read(device):
    """[(bounds, text)] for every text on screen, top to bottom."""
    env = dict(os.environ, JAVA_HOME=JDK, MAESTRO_CLI_NO_ANALYTICS="1", MAESTRO_CLI_ANALYSIS_NOTIFICATION_DISABLED="true")
    env["PATH"] = os.path.join(JDK, "bin") + os.pathsep + env["PATH"]
    maestro = os.path.join(os.path.expanduser("~"), ".maestro", "bin", "maestro.bat")
    # A running `maestro mcp` server (Claude Code's Maestro MCP) holds the
    # device, and `hierarchy` then hangs - for 10 minutes on 2026-11-11.
    # Stop that java process and run again.
    try:
        r = subprocess.run([maestro, "--device", device, "hierarchy"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=90)
    except subprocess.TimeoutExpired:
        sys.exit("maestro hierarchy hung for 90 s - is a `maestro mcp` java process running? Stop it and retry.")
    start = r.stdout.find("{")
    tree = json.loads(r.stdout[start:])
    out = []
    texts(tree, out)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    device = args[0] if args else "emulator-5554"
    for b, t in read(device):
        print((f"{b:28} " if "--bounds" in sys.argv else "") + t.replace("\n", " / "))


if __name__ == "__main__":
    main()
