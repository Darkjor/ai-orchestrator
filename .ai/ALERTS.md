# Active Alerts — Nexus RPG

> P0 = blocks everything. Fix before ANY new feature work.
> P1 = important, fix this session if related to your task.
> P2 = noted, address in planned work.
> RESOLVED = kept for history.
>
> If you discover a new issue: add it here immediately, don't wait until you're done.

---

## P0 — Blocking

### [ALERT-001] Docker requires VT-x/AMD-V — server cannot start
**Severity**: P0
**Status**:   Open
**Owner**:    None — needs a human to fix (BIOS setting)
**Discovered**: 2026-06-04
**Impact**:
- Full server stack unusable: PostgreSQL, Redis, Nakama, Go game server
- Multiplayer is impossible
- Character persistence is impossible
- go.sum never validated through Docker build

**Fix (human required)**:
1. Restart PC → enter BIOS (F2 / Del / F10 at boot)
2. Find: Intel Virtualization Technology (VT-x) OR AMD-V / SVM Mode
3. Set to **Enabled** → Save & Exit
4. In Windows (Admin PowerShell):
   ```
   dism /online /enable-feature /featurename:VirtualMachinePlatform /all
   dism /online /enable-feature /featurename:Microsoft-Hyper-V-All /all
   shutdown /r /t 0
   ```
5. After reboot: Docker Desktop should start normally

**Workaround**: Godot client runs 100% offline — `F5 → "Jugar Demo"`. All Block 1-2 features work without server.

**Blocked tasks**: TASK-003 (Go tests), server integration, multiplayer

---

## P1 — Important

### [ALERT-002] go.sum is empty — Go server won't build outside Docker
**Severity**: P1
**Status**:   Open
**Owner**:    None
**Discovered**: 2026-06-04
**Impact**: `cd server && go build` fails with missing module graph.
**Fix**:
```bash
# Option A: install Go locally
winget install GoLang.Go
cd server && go mod tidy

# Option B: fix ALERT-001 first (Docker does go mod download in build stage)
```
**Blocked by**: ALERT-001 (Option B)

---

### [ALERT-003] Nakama custom game modules not implemented
**Severity**: P1
**Status**:   Open
**Owner**:    None
**Discovered**: 2026-06-04
**Impact**: Auth, marketplace, chat use default Nakama behavior. No game logic.
**Location**: `nakama/data/` — currently empty
**Fix**: Implement Go runtime modules for: custom auth, matchmaking, marketplace hooks
**Blocked by**: ALERT-001 (can't run Nakama without Docker)

---

## P2 — Noted

### [ALERT-004] 73 placeholder sprites — visual quality
**Severity**: P2
**Status**:   In Progress — TASK-001 assigned to image AI
**Owner**:    See `AI_TASKS.md` TASK-001
**Impact**:   Visual quality only. Game runs fine with Polygon2D rendering.
**Fix**:      Complete TASK-001 (replace PNGs with real pixel art)

---

### [ALERT-005] MonsterManager.gd duplicates MAP constant from world_demo.gd
**Severity**: P2
**Status**:   Open
**Impact**:   If MAP changes in world_demo.gd, monster_manager.gd needs manual sync.
**Fix**:      In Block 3+, extract MAP to a shared `GameConstants.gd` autoload.
**File**:     `client/scripts/world/monster_manager.gd` line 8

---

## RESOLVED

*(none yet — first resolutions go here with date)*

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
