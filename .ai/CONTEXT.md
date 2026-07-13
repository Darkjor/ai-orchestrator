# Project Context — ai-orch (orquestador v1)

**Last updated**: 2026-07-13
**Updated by**: Claude Code (Antigravity)

---

## What works right now

- All **13 commands** verified by smoke test on a clean project: `init`, `triage`,
  `check`, `hook-install`, `handoff`, `snapshot`, `update`, `action-add`,
  `action-resolve`, `analyze`, `qa`, `export`, `observe`
- v0.3.0 architecture: logic split into 11 single-responsibility modules
  (`alerts`, `pending`, `context`, `decisions`, `analysis`, `gitops`, `lint`,
  `config`, `logs`, `models`, `handoff_ui`) — `main.py` is presentation-only (<500 lines)
- `aiorch._helpers` kept as frozen backward-compat re-export shim
- Local logging: swallowed errors go to `.ai/logs/aiorch.log` (gitignored)
- 101 tests pass. No active alerts.
- Robust git missing detection in gitops module.
- Detailed warnings on missing context markers in update_context.
- Observability logger tracks initialization disable reasons and logs exceptions.
- Packaging configured via tool.setuptools.packages.find in pyproject.toml.
- CI workflows configured for Ubuntu and Windows with Python 3.10-3.12 and 80% coverage threshold.
- MIT License added. .env excluded from version control in .gitignore.

---

## Most recently changed

- LICENSE - Add MIT license.
- pyproject.toml - Declare package search parameters, add Python 3.12 classifier and pytest-cov.
- .gitignore - Explicitly ignore .env files.
- .github/workflows/ci.yml - Expand test matrix to Windows and Ubuntu, add coverage checks.
- src/aiorch/handoff_ui.py - Extract interactive handoff wizard UI from main.py to keep main.py < 500 lines.
- src/aiorch/main.py - Import and delegate handoff command to handoff_ui.py, clean unused imports.
- docs/AI_ARCHITECTURE.md - Document handoff_ui.py module in map and diagrams.
- src/aiorch/gitops.py - Catch OSError in run_git_commit if git is missing.
- src/aiorch/context.py - Log warning in update_context when expected markers are missing.
- src/aiorch/observability.py - Implement disabled_reason attribute and log swallowed exceptions.
- src/aiorch/__init__.py - Sync package version to 0.3.0.
- tests/ - Add unit tests for git missing, marker warnings, and observability logging.

---

## Key numbers

| Metric | Value |
|--------|-------|
| Version | 0.3.0 |
| Python version | 3.10+ |
| Commands | 13 |
| Source modules | 13 + compat shim (`src/aiorch/`) |
| Tests | 101 (all passing) |
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
- `src/aiorch/handoff_ui.py`: run_handoff_wizard
- `src/aiorch/lint.py`: parse_lint_rules, check_staged_lint
- `src/aiorch/logs.py`: get_local_logger
- `src/aiorch/main.py`: init, _print_model_recommendations, _run_configured_tests, triage, check, hook_install, handoff, snapshot, update, action_add, action_resolve, analyze, qa, export, observe
- `src/aiorch/models.py`: Alert, AlertDraft, PendingAction, ActionDraft, DecisionDraft, LintRule, LintViolation, ProjectMetrics
- `src/aiorch/observability.py`: SupabaseLogger, get_logger
- `src/aiorch/pending.py`: ensure_pending_file, parse_pending, next_action_id, insert_action, resolve_action
