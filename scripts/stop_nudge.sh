#!/bin/sh
# ai-orch Stop hook — reminds the agent to record the session before it ends.
#
# WHY this nudges instead of writing: running `ai-orch sync` automatically here
# would record only the file list git already knows. The valuable half — where
# you stopped and why — is the half a machine cannot supply, and a hollow
# handoff is worse than none: it occupies the slot the real one would have and
# teaches the next agent the file is not worth reading. So the hook asks; the
# agent still writes.
#
# LOOP SAFETY — read before changing anything here. Claude Code has NO built-in
# counter that auto-allows a Stop hook after N blocks, so a hook that blocks on
# a condition the agent cannot clear would trap the session forever. Two
# defences, both required:
#   1. The marker file is written BEFORE the block is emitted, so a crash
#      between the two cannot produce a second nudge.
#   2. SessionStart deletes the marker, making this exactly one nudge per
#      session no matter what happens afterwards.
# Every other path exits 0 (allow). Fail-open is the only correct direction:
# a nudge that silently does not fire costs a stale note; a nudge that will not
# release costs the whole session.

[ -d ".ai" ] || exit 0

MARKER=".ai/logs/.stop-nudged"
[ -f "$MARKER" ] && exit 0

command -v git >/dev/null 2>&1 || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

STATUS=$(git status --porcelain 2>/dev/null) || exit 0
[ -z "$STATUS" ] && exit 0

# Did the session touch code without touching the context folder?
# `grep -c` already prints 0 on no match, so no `|| echo 0` fallback: that
# would append a second number, break the numeric test, and — because stdout
# IS the hook protocol here — corrupt the JSON below.
PATHS=$(printf '%s\n' "$STATUS" | cut -c4- | grep -v '^$')
CODE=$(printf '%s\n' "$PATHS" | grep -vc '^\.ai/')
CONTEXT=$(printf '%s\n' "$PATHS" | grep -c '^\.ai/')

[ "$CODE" -eq 0 ] && exit 0
[ "$CONTEXT" -gt 0 ] && exit 0

# Marker first — see LOOP SAFETY above.
mkdir -p ".ai/logs" 2>/dev/null || exit 0
: > "$MARKER" 2>/dev/null || exit 0

cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "permissionDecision": "block",
    "permissionDecisionReason": "Uncommitted code changes with no .ai/ update.",
    "additionalContext": "This session changed code but did not record anything in .ai/. Before finishing, run:\n\n  ai-orch sync --note \"<what you did and exactly where you stopped>\"\n\nThe note is the part that matters and the part only you can write: the precise stopping point, the decision not yet made, the approach you ruled out. Git already knows which files changed. If there is genuinely nothing worth recording (no code change of substance), say so in one line and finish. This reminder fires at most once per session.",
    "systemMessage": "ai-orch: session not recorded yet"
  }
}
JSON
exit 0
