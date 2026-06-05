# Architecture Decisions — Nexus RPG

> Read this BEFORE proposing changes to the architecture.
> If your change conflicts with a decision here, understand the rationale first.
> Disagreeing is OK — but add a new entry explaining why the decision should change.

---

## Format

```
## [DEC-XXX] Short title
Date:        YYYY-MM-DD
Status:      Active | Superseded by DEC-XXX | Reversed
Context:     Why did this decision need to be made?
Decision:    What was decided?
Rationale:   Why this option over alternatives?
Consequences: What are the trade-offs?
Revisit when: Condition that would trigger reconsideration
```

---

## [DEC-001] JSON over Protobuf for network protocol
**Date**: 2026-06-04
**Status**: Active
**Context**: Network message format needed for TCP game server. Speed vs. dev ergonomics tradeoff.
**Decision**: TCP + 4-byte Big Endian length prefix + JSON body for all client↔server messages.
**Rationale**:
- Protobuf requires `protoc` compilation step, generated Go+GDScript stubs, added build complexity
- JSON is human-readable for debugging, works natively in GDScript (JSON.parse_string)
- Speed is adequate for alpha (< 100 concurrent players expected in test phase)
**Consequences**: ~3x larger message payloads than Protobuf. `game.proto` exists but stub only.
**Revisit when**: Concurrent player count exceeds 500 OR measured latency > 100ms

---

## [DEC-002] Polygon2D rendering instead of Sprite2D nodes
**Date**: 2026-06-04
**Status**: Active
**Context**: Client development started with zero pixel art assets.
**Decision**: All game visuals in `world_demo.gd` and `monster_manager.gd` built with
`Polygon2D`, `ColorRect`, and `Label` nodes — zero external image dependencies.
**Rationale**:
- Unblocks all client-side feature development without waiting for art
- Demo is fully playable and testable from day one
- Sprites are a visual layer, not an architectural dependency
**Consequences**: Visual quality is minimal (geometric shapes). Sprite2D integration deferred to Block 3.
**Revisit when**: `AI_TASKS.md` TASK-001 (pixel art sprites) is marked Done

---

## [DEC-003] Offline-first demo architecture
**Date**: 2026-06-04
**Status**: Active
**Context**: Docker/server unavailable on dev machine (VT-x BIOS disabled — see ALERTS.md ALERT-001).
**Decision**: All gameplay logic in `world_demo.gd` works 100% standalone — no network required.
Combat, XP, inventory, respawn, spells all run client-side for the demo.
**Rationale**: Can't block client development on an external blocker with no ETA.
**Consequences**:
- world_demo.gd has game logic that will eventually be server-authoritative
- Risk of client/server logic divergence — mitigate by keeping server as the source of truth for production
**Revisit when**: ALERT-001 (Docker) resolved → migrate logic to server, demo becomes a thin client

---

## [DEC-004] Block-based commit strategy with `[Block N]` tags
**Date**: 2026-06-05
**Status**: Active
**Decision**: Large work units committed as atomic blocks with `[Block N]` in message.
Each block commit message contains full description of what changed.
**Rationale**:
- Any AI can run `git log` and understand project history in < 2 minutes
- Blocks are rollback-safe units — can revert a full block if needed
- Consistent with AI handoff — block number maps to PROGRESS.md state
**Revisit when**: Team size > 3 people (consider feature branches instead)

---

## [DEC-005] MonsterManager as extracted Node2D child
**Date**: 2026-06-05
**Status**: Active
**Context**: world_demo.gd was approaching 500 lines in Block 2.
**Decision**: Monster logic extracted to `monster_manager.gd` (class MonsterManager extends Node2D).
Interface via Callable injection: `setup(tile_fn, notify_fn)` + signals.
**Rationale**:
- Keeps world_demo.gd under 500 lines
- MonsterManager is independently testable
- Callable injection avoids tight coupling
**Consequences**: MAP constant duplicated in both files (see ALERT-005). Minor tech debt.
**Revisit when**: Block 3 — extract to shared `GameConstants.gd` autoload

---

## [DEC-006] .ai/ folder as universal AI orchestrator
**Date**: 2026-06-05
**Status**: Active
**Decision**: `.ai/` contains ORCHESTRATOR.md, TRIAGE.md, ALERTS.md, DECISIONS.md, CONTEXT.md.
Any AI reads `.ai/ORCHESTRATOR.md` first and follows CEO arrival protocol.
Project-specific content isolated to: Project Quick-Read block, ALERTS.md, DECISIONS.md.
**Rationale**:
- Universal template: copy `.ai/` to any project, update 3 fields, immediately operational
- Prevents AI agents from skipping triage and diving into features while P0 fires burn
- DECISIONS.md prevents future AIs from "fixing" intentional choices
**Revisit when**: Template is reused in 3+ projects — evaluate what's truly universal vs. RPG-specific

---

*Add new decisions chronologically. Never delete old ones — supersede them instead.*
