# Active Alerts — ai-orch (orquestador v1)

> P0 = blocks everything. Fix before ANY new feature work.
> P1 = important, fix this session if related to your task.
> P2 = noted, address in planned work.
> RESOLVED = kept for history.
>
> If you discover a new issue: add it here immediately, don't wait until you're done.

---

## P0 — Blocking

(none)

---

## P1 — Important

(none)

---

## P2 — Noted

(none)

---

## RESOLVED

### [ALERT-001] Triage false positive on merge conflict detection — RESOLVED 2026-06-05

**Severity**: P2
**Discovered**: 2026-06-05
**Impact**: `triage` reported fake merge conflict in `src/aiorch/main.py` because substring match found its own string literals.
**Fix**: `re.search(r'^<{7}', content, re.MULTILINE)` — requires markers at line start.

---

## Adding a New Alert

Copy this template:

```markdown
### [ALERT-XXX] Short description
**Severity**: P0 / P1 / P2
**Status**:   Open
**Owner**:    None / [AI name] / [human name]
**Discovered**: YYYY-MM-DD
**Impact**: What breaks or is degraded
**Fix**: Exact steps to resolve
**Blocked by**: (optional) other alert ID
```
