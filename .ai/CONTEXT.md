# Project Context — Auto-maintained

> This file is updated by AI agents after significant work.
> It is the fastest way to get up to speed (read before anything else).
> Keep it under 80 lines. Remove stale info aggressively.
> Para contexto completo (QA agents, análisis): `ai-orch export`

## .ai/ Folder Index

| File | Purpose |
|------|---------|
| ORCHESTRATOR.md | CEO arrival protocol — read this FIRST |
| ALERTS.md | Active fires P0/P1/P2 — check before any feature work |
| DECISIONS.md | Why things are built the way they are |
| WHEELS.md | Catalog of tools in use + failed experiments |
| DISCUSSIONS.md | Handoff and asynchronous debate board |
| CONTEXT.md | This file — live project state |

---

## Current State (updated: 2026-07-13)

**What works right now:**
- All **13 commands** verified by smoke test on a clean project: `init`, `triage`, `check`, `hook-install`, `handoff`, `snapshot`, `update`, `action-add`, `action-resolve`, `analyze`, `qa`, `export`, `observe`.
- v0.3.0 architecture: logic split into 11 single-responsibility modules (`alerts`, `pending`, `context`, `decisions`, `analysis`, `gitops`, `lint`, `config`, `logs`, `models`, `handoff_ui`) — `main.py` is presentation-only (<500 lines).
- `aiorch._helpers` kept as frozen backward-compat re-export shim.
- Local logging: swallowed errors go to `.ai/logs/aiorch.log` (gitignored).
- 115 tests pass. No active alerts.
- Robust git missing detection in gitops module.
- Detailed warnings on missing context markers in update_context.
- Observability logger tracks initialization disable reasons and logs exceptions.
- Packaging configured via tool.setuptools.packages.find in pyproject.toml.
- CI workflows configured for Ubuntu and Windows with Python 3.10-3.12 and 80% coverage threshold.
- MIT License added. .env excluded from version control in .gitignore.

**What does NOT work yet:**
- (none)

**Most recently changed:**
- tests/test_cli.py - Fix hook-integration test: set encoding="utf-8" on the git commit subprocess calls (was decoding Rich's UTF-8 output as cp1252 on Windows, throwing an unraisable UnicodeDecodeError in the reader thread).
- README.md, docs/API.md, docs/TROUBLESHOOTING.md, docs/MULTI_AGENT_FAQ.md - Replace remaining broken `pip install ai-orchestrator` (PyPI unpublished) with the git-based install command; bump stale `actions/checkout@v4`/`setup-python@v4` examples to v7/v6.
- docs/API.md - Fix placeholder `yourorg` repo link; rewrite the "add to _helpers.py" contributing step to point at the real domain-module checklist (the shim is frozen, no new logic).
- RELEASE_v0.2.0.md - Mark as historical, fix the `snapshot` command description, drop the dead PyPI install block.
- docs/AI_ARCHITECTURE.md - Fix `get_logger` patch attribution (it's the `observe` CLI tests, not observability tests).
- README.md - Note that only `analyze`/`qa` latency+status are self-recorded; token/cost/eval columns are filled by callers' own `SupabaseLogger.log_run`.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Version | 0.3.0 |
| Python version | 3.10+ |
| Commands | 13 |
| Source modules | 13 + compat shim (`src/aiorch/`) |
| Tests | 115 (114 passing, 1 skipped) |
| Dependencies | typer>=0.26.8, rich>=15.0.0 (supabase optional) |
| Entry point | `ai-orch` |
| Template files | 9 (8 copied by init; ANALYSIS.md is runtime-only) |

---

## Next Block — Planned

- Fase 5 — Resync del .ai/ self-hosted
- Fase 6 — Exactitud de docs
- Fase 7 — docs/MANUAL.md (español) + barrido final

---

## Recommended Models for Next Block

**Primary**: claude-sonnet-4-6 (balanced capability and cost)

**For architecture/design decisions**: claude-opus-4-8 (with extended thinking)

**For documentation**: claude-haiku-4-5-20251001 (lightweight)

See `.ai/config.json` and ORCHESTRATOR.md for detailed model selection guide.

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
