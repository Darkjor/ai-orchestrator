# Troubleshooting Guide

Common issues and solutions when using `ai-orch`.

## Installation & Setup

### Issue: `ai-orch: command not found`

**Cause:** `ai-orch` is not in your PATH.

**Solutions:**

1. **Verify installation:**
   ```bash
   pip show ai-orchestrator
   ```
   If nothing is printed, the package isn't installed.

2. **Reinstall:**
   ```bash
   pip install -U "git+https://github.com/Darkjor/ai-orchestrator.git@master"
   ```

3. **Use module form (fallback):**
   ```bash
   python -m aiorch.main --help
   ```

4. **Add to PATH (if using editable install):**
   ```bash
   python -m pip install -e .
   ```

---

### Issue: `Error: .ai/ orchestrator folder not found`

**Cause:** You haven't run `ai-orch init` yet.

**Solution:**

```bash
cd your-project-root
ai-orch init
```

This creates the `.ai/` folder with 8 context files:
- ORCHESTRATOR.md
- CONTEXT.md
- ALERTS.md
- DECISIONS.md
- DISCUSSIONS.md
- WHEELS.md
- PENDING.md
- config.json

Verify it worked:

```bash
ls -la .ai/
```

---

### Issue: `Permission denied` when running `ai-orch`

**Cause (Linux/Mac):** File permissions are too restrictive.

**Solution:**

```bash
# Check Python location
which python3

# Run with explicit python
python3 -m aiorch.main init
```

---

## Configuration Issues

### Issue: `triage` fails with "Could not run test command"

**Cause:** The `test_command` in `.ai/config.json` is invalid or doesn't exist.

**Solution:**

1. **Check your command:**
   ```bash
   cat .ai/config.json | grep test_command
   ```

2. **Test it manually:**
   ```bash
   # If it says: "pytest tests/" — run this
   pytest tests/
   
   # If it says: "npm test" — run this
   npm test
   ```

3. **Fix config.json if needed:**
   ```bash
   # Edit manually
   nano .ai/config.json
   
   # Or use ai-orch update
   ai-orch update --section "Configuration" --value "- test_command: pytest tests/ -v"
   ```

4. **Disable test command (temporary):**
   Remove `"test_command"` from `.ai/config.json` entirely.

---

### Issue: `JSON parsing error` in triage output

**Cause:** `.ai/config.json` contains invalid JSON.

**Symptoms:**
```
[yellow][WARN] Warning: Could not run test command...
```

**Solution:**

1. **Validate JSON syntax:**
   ```bash
   python3 -m json.tool .ai/config.json
   ```

2. **Common errors:**
   - Trailing comma: `"key": "value",}` ← Remove the comma before `}`
   - Missing quotes: `{key: value}` ← Add quotes: `{"key": "value"}`
   - Single quotes: `{'key': 'value'}` ← Use double quotes

3. **Use online validator:** https://jsonlint.com/

4. **Regenerate from template:**
   ```bash
   # Backup old config
   mv .ai/config.json .ai/config.json.bak
   
   # Copy fresh template
   cp node_modules/ai-orchestrator/templates/config.json .ai/
   # OR get from source repo
   ```

---

## Git & Pre-commit Hooks

### Issue: `ai-orch check` fails with "Staged files detected but .ai/ not updated"

**Cause:** You modified code but didn't update `.ai/CONTEXT.md` (or other `.ai/` files).

**Solution:**

Option 1: Update `.ai/` files before committing

```bash
ai-orch handoff  # Interactive wizard to update context

# OR manually update
ai-orch update --section "Current State" --value "- Made async database queries"
ai-orch update --section "Most recently changed" --value "- src/db.py"

# Then add .ai/ to staging
git add .ai/
git commit -m "docs: update context after database optimization"
```

Option 2: Disable the guard temporarily

```bash
git commit --no-verify  # Skips pre-commit hook
```

**Note:** This is not recommended — the guard exists to prevent context drift.

---

### Issue: Pre-commit hook doesn't run on Windows

**Cause:** Git on Windows may use CRLF line endings, which breaks shell scripts.

**Solution:**

1. **Reinstall the hook with correct line endings:**
   ```bash
   ai-orch hook-install
   ```

2. **Or set git to use LF:**
   ```bash
   git config core.safecrlf false
   git config core.eol lf
   ```

3. **Manually ensure hook is executable:**
   ```bash
   # In Git Bash or WSL
   chmod +x .git/hooks/pre-commit
   ```

4. **Use WSL or Git Bash:**
   The hook requires a Unix shell. Use:
   - Git Bash (Windows)
   - WSL (Windows)
   - Native bash/zsh (Linux/Mac)

---

### Issue: Hook installed but doesn't execute

**Cause:** Hook file isn't executable or shell isn't available.

**Solution:**

1. **Verify hook exists:**
   ```bash
   cat .git/hooks/pre-commit
   ```

2. **Make executable:**
   ```bash
   chmod +x .git/hooks/pre-commit
   ```

3. **Test manually:**
   ```bash
   .git/hooks/pre-commit
   # Should print: [OK] AI orchestrator context update verified.
   ```

4. **If test fails, run ai-orch directly:**
   ```bash
   ai-orch check
   ```

---

### Issue: Lint rule blocking legitimate code

**Cause:** A rule in `.ai/WHEELS.md` is too aggressive.

**Example:**
```
Pattern: `console\`  # Matches any use of "console" including "console_output"
```

**Solution:**

1. **Refine the pattern:**
   ```markdown
   ### [LINT-001] No debug logs
   **Pattern**: `console\.log\(`   # More specific: only console.log()
   **Files**: *.js, *.ts
   **Message**: Remove console.log before committing.
   ```

2. **Exclude your file:**
   ```markdown
   **Files**: *.js, *.ts, !config/*.js   # Excludes config/ directory
   ```

3. **Remove the rule temporarily:**
   ```bash
   # Comment it out in .ai/WHEELS.md
   # ### [LINT-001] ...
   ```

4. **Override on commit:**
   ```bash
   git commit --no-verify
   # (Only if rule is wrong — update WHEELS.md afterward)
   ```

---

## Handoff Wizard

### Issue: `handoff` prompts feel confusing

**Cause:** The wizard has many optional fields.

**Solution:**

Use defaults by pressing Enter:

```bash
ai-orch handoff

# Press Enter through all prompts
What type of work? → feature (default)
What was accomplished? → (empty, press Enter)
What files changed? → (empty, press Enter)
Add alert? → n
Add decision? → n
Git commit? → n
```

You can always update `.ai/` files manually afterward:

```bash
ai-orch update --section "Current State" --value "Your notes here"
git add .ai/ && git commit -m "docs: session notes"
```

---

### Issue: Handoff doesn't create a git commit

**Cause:** You selected "n" when asked "Do you want to... commit?"

**Solution:**

Manually create the commit:

```bash
git add .ai/
git commit -m "[3] feat: Implemented authentication module"
```

Or re-run handoff and select "y" when asked about the commit.

---

## Alert & Action Management

### Issue: Alert appears in both P0 and RESOLVED sections

**Cause:** Duplicate alert entries or improper formatting.

**Solution:**

1. **Check ALERTS.md formatting:**
   ```bash
   cat .ai/ALERTS.md | grep -n "ALERT-XXX"
   ```

2. **Remove duplicate (keep one):**
   ```bash
   nano .ai/ALERTS.md
   # Delete the duplicate line
   ```

3. **Ensure correct section structure:**
   ```markdown
   ## P0 — Blocking
   ### [ALERT-001] Issue
   ...

   ## RESOLVED
   ### [ALERT-001] Issue
   ```

**Note:** Alerts should appear in only ONE section at a time.

---

### Issue: `action-add` fails with "Section not found"

**Cause:** `.ai/PENDING.md` doesn't have a section for your action type.

**Solution:**

1. **Check available sections:**
   ```bash
   cat .ai/PENDING.md | grep "^##"
   # Should show: Database, Infrastructure, Other
   ```

2. **Use correct type:**
   ```bash
   ai-orch action-add "Task" --type db      # Correct
   ai-orch action-add "Task" --type infra   # Correct
   ai-orch action-add "Task" --type other   # Correct
   ai-orch action-add "Task" --type custom  # WRONG
   ```

3. **Manually add missing section to PENDING.md:**
   ```markdown
   ## Other

   (none)
   ```

---

### Issue: `action-resolve` says "not found"

**Cause:** Action ID doesn't exist or is misspelled.

**Solution:**

1. **List all open actions:**
   ```bash
   ai-orch triage | grep -A5 "Pending Manual Actions"
   ```

2. **Use exact ID:**
   ```bash
   ai-orch action-resolve DB-001     # Correct
   ai-orch action-resolve db-001     # WRONG (case-sensitive)
   ai-orch action-resolve DB001      # WRONG (missing hyphen)
   ```

3. **Verify action is still pending:**
   ```bash
   grep "### \[DB-001\]" .ai/PENDING.md
   ```

   If not found, it may already be marked as Done.

---

## Codebase Snapshots

### Issue: `snapshot` command produces empty output

**Cause:** Source directory contains no Python files, or path is wrong.

**Solution:**

1. **Check directory exists:**
   ```bash
   ls -la src/  # or whatever you passed with --src
   ```

2. **Verify Python files exist:**
   ```bash
   find src/ -name "*.py" | head
   ```

3. **Use correct path:**
   ```bash
   ai-orch snapshot --src src         # Correct
   ai-orch snapshot --src ./src       # Also works
   ai-orch snapshot --src lib         # Uses lib/ instead of src/
   ```

4. **Check for syntax errors:**
   ```bash
   python3 -m py_compile src/module.py
   ```

   If you get `SyntaxError`, the file has invalid Python and won't be scanned.

---

### Issue: Snapshot includes unwanted modules

**Cause:** `generate_snapshot()` walks all files in the target directory.

**Solution:**

1. **Use `.gitignore` to exclude:**
   ```
   # .gitignore
   src/generated/      # Won't be included in snapshot
   src/__pycache__/
   src/.venv/
   ```

2. **Or specify a different source:**
   ```bash
   ai-orch snapshot --src src/core   # Only scan src/core/
   ```

3. **Manually edit the snapshot:**
   Edit the "## Codebase Snapshot" section in `.ai/CONTEXT.md` directly.

---

## File Access Issues

### Issue: Cannot write to `.ai/` files (permission denied)

**Cause:** File permissions or filesystem restriction.

**Solution:**

1. **Check permissions:**
   ```bash
   ls -la .ai/
   ```

2. **Make writable:**
   ```bash
   chmod 644 .ai/*
   ```

3. **Check disk space:**
   ```bash
   df -h .
   ```

4. **Try direct edit:**
   ```bash
   nano .ai/CONTEXT.md
   ```

---

### Issue: CONTEXT.md encoding error after update

**Cause:** File contains non-UTF-8 characters.

**Solution:**

1. **Check encoding:**
   ```bash
   file .ai/CONTEXT.md
   # Should say: UTF-8 Unicode (with BOM or without)
   ```

2. **Convert to UTF-8:**
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 .ai/CONTEXT.md > .ai/CONTEXT.md.tmp
   mv .ai/CONTEXT.md.tmp .ai/CONTEXT.md
   ```

3. **Or regenerate:**
   ```bash
   rm .ai/CONTEXT.md
   ai-orch init  # This will warn and not overwrite, so manually delete .ai/
   rm -rf .ai/
   ai-orch init
   ```

---

## Multi-agent Scenarios

### Issue: Another agent's changes conflict with mine

**Cause:** Two agents modified the same section of `.ai/` simultaneously.

**Solution:**

1. **Review git history:**
   ```bash
   git log --oneline .ai/CONTEXT.md
   # See what changed and when
   ```

2. **Check for merge conflicts:**
   ```bash
   ai-orch triage | grep -i "conflict"
   ```

3. **Resolve manually:**
   ```bash
   git diff .ai/CONTEXT.md
   nano .ai/CONTEXT.md  # Edit to resolve conflicts
   git add .ai/CONTEXT.md
   git commit -m "docs: resolve merge conflict in CONTEXT.md"
   ```

4. **Use discussions section:**
   Add a note to `.ai/DISCUSSIONS.md` for the other agent:
   ```markdown
   ## Thread: Token caching logic

   **Agent A (2024-01-20):**
   Changed auth.py to cache tokens in Redis...

   **Agent B (2024-01-21):**
   Agree with approach. Also refactored JWT validation...
   ```

---

### Issue: Agent missed an alert or decision

**Cause:** Agent didn't read ORCHESTRATOR.md arrival protocol.

**Solution:**

1. **Post a note in DISCUSSIONS.md:**
   ```markdown
   ## Alert for next agent
   
   @next-agent: P0 alert exists — see ALERTS.md before coding.
   Also check WHEELS.md for failed approaches.
   ```

2. **Make alerts more visible:**
   Update the alert severity if needed:
   ```bash
   nano .ai/ALERTS.md
   # Move to P0 section if it's blocking
   ```

3. **Enforce via CI:**
   ```yaml
   - name: Check for P0 alerts
     run: |
       count=$(grep -c "## P0" .ai/ALERTS.md)
       if [ $count -gt 0 ]; then
         echo "P0 alerts exist — fix before merging"
         exit 1
       fi
   ```

---

## Performance Issues

### Issue: `triage` or `snapshot` is very slow

**Cause:** Scanning a large codebase or network filesystem.

**Solution:**

1. **Profile the command:**
   ```bash
   time ai-orch triage
   # Shows how long each operation takes
   ```

2. **Limit snapshot scope:**
   ```bash
   ai-orch snapshot --src src/core   # Smaller directory
   ```

3. **Exclude large directories:**
   Add to `.gitignore`:
   ```
   node_modules/
   venv/
   .venv/
   dist/
   build/
   ```

4. **Check git status:**
   ```bash
   git status  # Slow on network drives
   ```

---

## Getting Help

- **Check the README:** [README.md](../README.md)
- **Read the arrival protocol:** `.ai/ORCHESTRATOR.md` (created by `ai-orch init`)
- **Review WHEELS.md:** Known issues and solutions in your project
- **Ask in DISCUSSIONS.md:** Leave a question for other agents
- **File an issue:** [GitHub Issues](https://github.com/darkjor/ai-orchestrator)

---

## Reporting Issues

When filing a bug report, include:

1. **Python version:**
   ```bash
   python3 --version
   ```

2. **Package version:**
   ```bash
   pip show ai-orchestrator
   ```

3. **Command and output:**
   ```bash
   ai-orch triage --help
   ai-orch triage 2>&1
   ```

4. **Project structure (safe to share):**
   ```bash
   find .ai -type f -name "*.md" -o -name "*.json" | head
   ```

5. **OS and shell:**
   ```bash
   uname -a
   echo $SHELL
   ```
