# Project Context — ai-orch (orquestador v1)

**Last updated**: 2026-07-26
**Updated by**: Claude Code (Opus 5), while bootstrapping the "saas negocios chiquitos" project

---

## What works right now

- All **13 commands** verified by smoke test on a clean project: `init`, `triage`,
  `check`, `hook-install`, `handoff`, `snapshot`, `update`, `action-add`,
  `action-resolve`, `analyze`, `qa`, `export`, `observe`
- v0.3.0 architecture: logic split into 10 single-responsibility domain modules
  (`alerts`, `pending`, `context`, `decisions`, `analysis`, `gitops`, `lint`,
  `config`, `logs`, `models`) — `main.py` is presentation-only (<500 lines)
- `aiorch._helpers` kept as frozen backward-compat re-export shim
- Local logging: swallowed errors go to `.ai/logs/aiorch.log` (gitignored)
- The guard's exempt-paths whitelist (used by `check`) is now configurable via
  `.ai/config.json` → `guard.exempt_paths` (list of `fnmatch` globs), instead of
  the old hardcoded `docs/`, `.gitignore`, `pyproject.toml`. When the field is
  absent, behavior is unchanged (same default list) — existing projects aren't
  affected. This was needed because the hardcoded whitelist blocked every commit
  in non-Python repos (e.g. Next.js) that touch code without touching `.ai/`.
- `resolve_action()` no longer swallows `---` separators or `*(none)*`
  placeholders into the moved block when resolving the last action in a section
  — it was corrupting `PENDING.md`'s structure on every resolve (visible in this
  repo's own `.ai/PENDING.md` before the fix).
- 96 tests pass (93 + 3 regression tests for the two fixes above). No active alerts.

---

## Most recently changed

- `src/aiorch/pending.py` — `resolve_action()` block-end boundary now also stops
  at a line that strips to exactly `---` or `*(none)*`, not just the next heading.
- `src/aiorch/main.py` — `check`'s guard whitelist reads `guard.exempt_paths` from
  `.ai/config.json` (fnmatch globs), falling back to the previous hardcoded list.
- `src/aiorch/templates/config.json` — documents the new `guard.exempt_paths`
  field with the default list as its example value.
- `tests/test_modules.py`, `tests/test_cli.py` — regression coverage for both fixes.
- .github/workflows/ci.yml - CI now runs on push to master (was develop-only)
- README.md - Install section documents the real path: pip install git+...@v0.3.0 and update via pip install -U git+...@master
- src/aiorch/ - domain-module split (10 modules), TypedDict contracts, local logging
- docs/AI_ARCHITECTURE.md - master context map for AI agents

---

## Key numbers

| Metric | Value |
|--------|-------|
| Version | 0.3.0 |
| Python version | 3.10+ |
| Commands | 13 |
| Source modules | 12 + compat shim (`src/aiorch/`) |
| Tests | 96 (all passing) |
| Dependencies | typer>=0.9.0, rich>=13.0.0 (supabase optional) |
| Entry point | `ai-orch` |
| Template files | 9 (8 copied by init; ANALYSIS.md is runtime-only) |

---

## Stack

- Language: Python 3.11
- CLI framework: Typer 0.26.7
- Terminal UI: Rich 13.x
- Observability (optional): Supabase (`agent_runs` table)
- Tests: pytest

---

## Known environment gotcha

The editable install of `ai-orchestrator` is machine-global. On 2026-06-10 the
`.pth` was found pointing to a DIFFERENT folder (`Escritorio/generacion/src`),
so imports/tests silently exercised that copy. Fixed with `pip install -e .`
from this repo. If imports behave strangely, check
`python -c "import aiorch; print(aiorch.__file__)"` first.

---

## Next steps

- Publish v0.3.0 (dist/ currently holds the 0.2.0 wheel)
- Consider `ai-orch status` dashboard command
- Optional: CI markdownlint for docs

---

## Codebase Snapshot

- `src/aiorch/alerts.py`: parse_alerts, all_alert_ids, next_alert_id, insert_alert
- `src/aiorch/analysis.py`: parse_analysis_status, set_analysis_status, collect_project_metrics, write_analysis_report, qa_cross_check
- `src/aiorch/config.py`: load_config
- `src/aiorch/context.py`: update_section, update_context, generate_snapshot, inject_snapshot, bundle_context
- `src/aiorch/decisions.py`: append_decision, count_decisions
- `src/aiorch/gitops.py`: GitCommandError, get_staged_files, has_merge_conflicts, scan_conflict_files, find_secret_files, run_git_commit, write_git_hook
- `src/aiorch/lint.py`: parse_lint_rules, check_staged_lint
- `src/aiorch/logs.py`: get_local_logger
- `src/aiorch/main.py`: init, _print_model_recommendations, _run_configured_tests, triage, check, hook_install, handoff, snapshot, update, action_add, action_resolve, analyze, qa, export, observe
- `src/aiorch/models.py`: Alert, AlertDraft, PendingAction, ActionDraft, DecisionDraft, LintRule, LintViolation, ProjectMetrics
- `src/aiorch/observability.py`: SupabaseLogger, get_logger
- `src/aiorch/pending.py`: ensure_pending_file, parse_pending, next_action_id, insert_action, resolve_action
