# Architecture Decisions — ai-orch (orquestador v1)

> Status values: Active | Superseded by DEC-XXX | Reversed

---

## [DEC-001] Typer over argparse/click for CLI framework

**Date**: 2026-06-01
**Status**: Active
**Context**: Needed a CLI framework for the 5 commands. Options: argparse (stdlib), click, typer.
**Decision**: Typer with type hints.
**Rationale**: Typer generates `--help` automatically from type hints, requires minimal boilerplate, and integrates naturally with Python 3.10+ type system. Rich integration is straightforward.
**Consequences**: Requires Python 3.10+. Slightly heavier than argparse but much better UX.
**Revisit when**: Python 3.9 support becomes needed.

---

## [DEC-002] Markdown files over database for `.ai/` context

**Date**: 2026-06-01
**Status**: Active
**Context**: AI agents need to read and write project context. Options: SQLite, JSON files, Markdown files.
**Decision**: Plain Markdown files (.ai/CONTEXT.md, ALERTS.md, etc.)
**Rationale**: Markdown is readable by any AI tool (Claude, Gemini, GPT) without tool calls. Human-readable in any editor. Works with git diff. No schema migrations.
**Consequences**: Parsing is fragile (regex-based). Cannot query across projects. Append-only updates can cause duplication.
**Revisit when**: Cross-project queries or structured queries become needed.

---

## [DEC-003] Pre-commit hook enforces .ai/ update on code changes

**Date**: 2026-06-01
**Status**: Active
**Context**: Agents frequently update code without updating the `.ai/CONTEXT.md`, causing context drift.
**Decision**: Block git commits if code files were staged but `.ai/` was not touched.
**Rationale**: Hard enforcement at commit time is the only reliable mechanism. Soft reminders get ignored.
**Consequences**: Adds friction to commits. Mitigated by `ai-orch handoff` which handles the update interactively.
**Revisit when**: A better context-sync mechanism exists (e.g., LSP hook, IDE plugin).

---

## [DEC-004] Merge conflict detection uses line-start regex

**Date**: 2026-06-05
**Status**: Active
**Context**: Original implementation used `"<<<<<<<" in content` which matched the string literal inside main.py itself, causing false positives.
**Decision**: Use `re.search(r'^<{7}', content, re.MULTILINE)` to require conflict markers at line start.
**Rationale**: Git conflict markers always appear at column 0. String literals containing `<<<<<<<` (as in this codebase) will not match.
**Consequences**: None — stricter match is correct behavior.
**Revisit when**: Never — this is the correct pattern.

---

## [DEC-005] Architecture review — scalability bottlenecks & technical debt

**Date**: 2026-06-05
**Status**: Active
**Context**: Architect-agent audit of `src/aiorch/{main.py, _helpers.py}`, templates, and tests for scalability, regex/I/O performance, subprocess error handling, and tech debt. Findings + prioritized optimizations below.

### 1. Code organization
- **Structure**: 2 source modules — `main.py` (494 lines, all CLI command bodies) and `_helpers.py` (254 lines, parsing/file logic). `__init__.py` is empty. Clean one-way dependency: `main` imports from `_helpers`; `_helpers` imports only stdlib. **No circular dependencies.**
- **Imports clean?** Mostly. `main.py` imports 8 helpers in one statement — fine. **No unused imports** detected in either module.
- **Scaling concern**: `main.py` will breach the 500-line CLAUDE.md cap with the next 1-2 commands (currently 494). Command bodies inline all parsing/file-mutation logic (e.g. `handoff` is ~170 lines doing CONTEXT/ALERTS/DECISIONS mutation directly instead of delegating to `_helpers`). **Recommendation**: extract per-file mutation logic (the CONTEXT.md/ALERTS.md inline blocks in `handoff`) into `_helpers`, and consider splitting commands into a `commands/` package once >2 more commands land. Note `handoff` duplicates `_insert_alert` logic that already exists in `_helpers.py` (lines 54-70) — dead-ish duplication.

### 2. Regex performance (10k+ line files)
- **`parse_alerts` / `parse_pending`**: iterate line-by-line, calling `re.search` per line with an **uncompiled, literal-string pattern**. Python caches the last 512 uncompiled patterns internally, so correctness is fine, but each call re-hashes the pattern. At 10k lines this is ~10k dict lookups — negligible (<5ms) but avoidable.
- **`check_staged_lint`** (hottest path): nested loop `for rule -> for line -> re.search(rule["pattern"], line)`. The pattern is **recompiled-by-cache on every line**. With R rules × L lines this is R×L lookups. For a 10k-line file with 10 rules that's 100k `re.search` calls on uncompiled patterns. **This is the one real regex bottleneck.**
- **`inject_snapshot`**: `re.sub(r"## Codebase Snapshot\n.*", ..., flags=re.DOTALL)` is `.*` greedy over the whole file — O(n) and fine, but DOTALL-greedy means it always clobbers everything after the header (intended here, but fragile if more sections are added below the snapshot).
- **`parse_lint_rules`**: `re.DOTALL` `.*?` lazy scans are fine for small WHEELS.md but are O(n²)-ish on pathological input; not a concern at realistic sizes.
- **Optimization**: pre-compile lint patterns once in `check_staged_lint` (`[re.compile(r["pattern"]) for r in rules]`) and compile the module-level ALERT/PENDING patterns as constants. **Estimated impact: check_staged_lint on a 10k-line file with 10 rules ~30-60ms → ~5-10ms (-80%); parse_* startup -2-5ms.**

### 3. File I/O patterns (N+1)
- **`triage` is the worst offender**: `os.walk(".")` reads **every** .py/.md/.json/etc file in the repo with `f.read()` into memory to regex-scan for conflict markers — an N+1 full-repo read on every triage. On a large monorepo this is the dominant cost. Mitigations available: (a) shell out to `git grep -n '^<<<<<<<'` (uses git's index, far faster, skips ignored files for free), or (b) stream lines and early-exit instead of `content = f.read()`.
- **`triage` opens `.ai/config.json` twice** (lines 85 and 149) — redundant double parse of the same file. **Batch into one read.**
- **`check_staged_lint`**: one `git show :<path>` subprocess **per staged file** — genuine N+1 subprocess spawn. For a commit staging 50 files that's 50 process launches. Could batch via `git diff --cached` once, but acceptable for typical commit sizes.
- General pattern: every helper re-opens its target file (`parse_alerts`, then `_insert_alert` re-reads same file in `handoff` flow). Read-once/pass-content would remove redundant reads but adds coupling — low priority.

### 4. JSON / config parsing & regex caching
- `config.json` parsed with stdlib `json.load` — fine. The issue is it's **parsed twice in triage** (see §3). No caching of compiled regexes anywhere; all patterns are inline literals. **Recommendation**: module-level `_ALERT_RE = re.compile(...)`, `_PENDING_RE`, `_ACTION_RE` etc., and a single config read in triage. **Estimated impact: -2-5ms startup, removes one disk read per triage.**

### 5. Subprocess calls — error handling
- Calls: `git diff --cached --name-only` (triage, check), `git show :path` (lint), `git add .` + `git commit` (handoff), and `subprocess.run(test_cmd, shell=True)` (triage).
- **Good**: most wrap in `try/except Exception` and degrade gracefully (`pass` / Exit(0)).
- **Concerns**:
  - `subprocess.run(test_cmd, shell=True)` runs **arbitrary config-sourced command with shell=True** — command injection surface if config.json is untrusted. Acceptable for a dev tool the user owns, but worth a doc note.
  - `handoff` git block catches bare `Exception` and only prints — a failed `git add .`/`commit` is swallowed; user may believe commit succeeded. Should surface non-zero exit distinctly.
  - Several `except Exception: pass` blocks hide real errors (e.g. encoding failures in the conflict scan). Acceptable but noisy-silent.
  - No timeouts on any subprocess — a hanging `test_command` blocks triage indefinitely. **Add `timeout=` to the test run.**

### 6. Technical debt
- **No TODO/FIXME in actual code** (only `-XXX` template placeholders, which are intentional).
- **No dead code / unused imports** in source.
- **Duplication**: `handoff`'s inline ALERTS.md insertion (main.py ~364-389) duplicates `_insert_alert`/`_next_alert_id` in `_helpers.py`, which `handoff` does **not** use — drift risk (e.g. handoff asks user for a manual alert ID instead of using `_next_alert_id`).
- **500-line guard**: `main.py` at 494/500 — imminent breach.
- **`triage` config double-read** and the empty repeated `config_path = os.path.join(...)` reassignment (lines 81 and 146) are minor smells.
- **Untested paths**: `check_staged_lint`, `parse_pending`, snapshot injection have logic complexity but I only confirmed `parse_lint_rules`/init/triage/check are exercised in `tests/test_cli.py`.

### Prioritized optimizations
1. **(High)** Replace `triage` full-repo `os.walk` conflict scan with `git grep -n '^<<<<<<<' ` (or stream+early-exit). Impact: O(repo-bytes) → near-O(diff); biggest win on large repos.
2. **(High)** Pre-compile lint regex patterns once in `check_staged_lint`. Impact: -80% on large staged files.
3. **(Med)** Read `config.json` once in `triage` (currently parsed twice). Impact: -1 disk read + -1 JSON parse per triage.
4. **(Med)** Add `timeout=` to the `shell=True` test subprocess; surface handoff git failures via return code.
5. **(Low)** Hoist ALERT/PENDING/ACTION regexes to module-level `re.compile` constants. Impact: -2-5ms startup.
6. **(Low)** Make `handoff` reuse `_insert_alert`/`_next_alert_id` from `_helpers` to kill duplication, and extract handoff's CONTEXT mutation into `_helpers` before `main.py` crosses 500 lines.

**Decision**: Findings recorded for the developer/performance tasks (#2, #5). No code changes made in this review pass.
**Rationale**: Architecture-only audit; implementation deferred to owning tasks.
**Consequences**: §3.1 (triage full-repo read) and §2 (lint recompile) are the only changes that matter at 10k-line scale; the rest are micro-optimizations.
**Revisit when**: `main.py` exceeds 500 lines or triage latency becomes user-visible on a large repo.
