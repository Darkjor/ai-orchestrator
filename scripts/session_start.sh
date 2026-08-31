#!/bin/sh
# ai-orch SessionStart hook — prints a compact arrival brief into the session context.
#
# WHY not `ai-orch triage`: triage runs the project's configured test command
# (up to 30s) and renders Rich tables. A session-start hook must be instant and
# plain-text, so this reads the .ai/ files directly through aiorch's own parsers.
#
# Contract: exit 0 ALWAYS, and print NOTHING in a project that has no .ai/ folder.
# stdout from a SessionStart hook is injected into Claude's context, so noise here
# is a tax on every single session.

[ -d ".ai" ] || exit 0

PY=""
for c in python3 python; do
  command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }
done

if [ -z "$PY" ]; then
  echo "ai-orch: .ai/ context folder present. Run \`ai-orch triage\` for the arrival brief."
  exit 0
fi

"$PY" - <<'PYEOF' 2>/dev/null || echo "ai-orch: .ai/ context folder present. Run \`ai-orch triage\` for the arrival brief."
import os
import sys

try:
    from aiorch.alerts import parse_alerts
    from aiorch.pending import parse_pending
except ImportError:
    print("ai-orch: .ai/ folder found but the CLI is not installed.")
    print('Install it with: pip install "git+https://github.com/Darkjor/ai-orchestrator.git@master"')
    sys.exit(0)

alerts = parse_alerts(os.path.join(".ai", "ALERTS.md"))
pending = parse_pending(os.path.join(".ai", "PENDING.md"))

out = ["ai-orch: this project keeps cross-session context in .ai/."]

by_sev = {}
for a in alerts:
    by_sev.setdefault(a["severity"], []).append(a)

if by_sev.get("P0"):
    out.append("")
    out.append("P0 — BLOCKING. Handle these before the requested task, or say why you cannot:")
    out += [f"  [{a['id']}] {a['title']}" for a in by_sev["P0"]]

for sev in ("P1", "P2"):
    if by_sev.get(sev):
        titles = "; ".join(f"{a['id']} {a['title']}" for a in by_sev[sev][:3])
        more = f" (+{len(by_sev[sev]) - 3} more)" if len(by_sev[sev]) > 3 else ""
        out.append(f"{sev}: {titles}{more}")

if not alerts:
    out.append("No open alerts.")

if pending:
    titles = "; ".join(f"{p['id']} {p['title']}" for p in pending[:3])
    more = f" (+{len(pending) - 3} more)" if len(pending) > 3 else ""
    out.append(f"Pending manual actions (human-only work): {titles}{more}")

out.append("")
out.append("Read .ai/CONTEXT.md for where the last session stopped and .ai/WHEELS.md")
out.append("for approaches already ruled out. Use /ai-orch:arrival for the full protocol.")
out.append("")
out.append("Before you finish: `ai-orch sync --note \"what you did, where you stopped\"`.")
out.append("It never prompts and reads the changed files from git. The pre-commit guard")
out.append("blocks code commits that leave .ai/ stale, so this is not optional.")

print("\n".join(out))
PYEOF

exit 0
