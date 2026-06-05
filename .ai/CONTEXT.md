# Project Context — Auto-maintained

> This file is updated by AI agents after significant work.
> It is the fastest way to get up to speed (read before anything else).
> Keep it under 80 lines. Remove stale info aggressively.

## .ai/ Folder Index

| File | Purpose |
|------|---------|
| ORCHESTRATOR.md | CEO arrival protocol — read this FIRST |
| TRIAGE.md | Universal health check — run on every arrival |
| ALERTS.md | Active fires P0/P1/P2 — check before any feature work |
| DECISIONS.md | Why things are built the way they are |
| CONTEXT.md | This file — live project state |

---

## Current State (updated: 2026-06-05, Block 2)

**What works right now:**
- Open Godot 4 → Import `client/` → F5 → "Jugar Demo (sin servidor)"
- WASD movement, camera follows correctly
- 5 monsters with real HP: Wolf / Troll / Orc / Dragon / Demon
- Click or F to attack, Z/X/C/V for spells (Fireball/Heal/Lightning/Shield)
- Death + 3s respawn to safe zone
- Monster patrol AI (random walk every 2.5s)
- XP + level-up system
- Inventory popup (I key)

**What does NOT work yet:**
- Server (Docker needs VT-x in BIOS — currently disabled on dev machine)
- Real multiplayer (no server = no other players)
- Real pixel art (73 placeholder PNGs — Gemini task TASK-001 pending)
- Nakama auth/social not implemented

**Most recently changed:**
- `client/scripts/world/world_demo.gd` — spells, inventory, uses MonsterManager
- `client/scripts/world/monster_manager.gd` — new: patrol AI + combat
- `AI_TASKS.md` — task board (TASK-001 sprites open, TASK-003 Go tests open)

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Git commits | 2 (Block 1: 22585d0, Block 2: 24548f8) |
| GDScript files | ~15 |
| Go server files | ~20 |
| Placeholder sprites | 73 PNGs |
| DB tables | 12 |
| Monsters in demo | 5 |
| Spells in demo | 4 |

---

## Next Block (Block 3) — Planned

- Integrate real sprites into demo (replace Polygon2D with Sprite2D)
- Go server: `go mod tidy` + first local run (needs Go installed or VT-x for Docker)
- Basic multiplayer: see other players' positions
- Persistent character save (local JSON until server is up)

---

## How to Update This File

Update after:
- Any Block commit
- Any significant bug fix
- Any new system added
- Any blocker resolved or discovered

Update the "Current State", "Most recently changed", and "Key Numbers" sections.
Keep it concise. This file should never exceed 80 lines.
