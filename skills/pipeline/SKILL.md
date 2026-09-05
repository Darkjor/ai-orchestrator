---
name: pipeline
description: The production standard for multi-agent work inside a .ai/ project — decompose the task into verifiable steps before assigning any of it, pass structured JSON envelopes between planner, executor and QA instead of prose, validate every handoff with `ai-orch validate`, and treat each role prompt as versioned code. Load this when orchestrating more than one agent, when chaining planner/executor/QA roles, when designing what one agent hands to the next, when a pipeline must run unattended, or when writing or revising an agent role prompt.
when_to_use: Trigger phrases — "multi-agent", "pipeline", "planner", "executor", "QA agent", "orchestrate agents", "chain agents", "structured output", "agent handoff format", "role prompt", "prompt version", "run unattended", "sin supervisión", "descomponer la tarea".
allowed-tools: Bash(ai-orch validate:*), Bash(ai-orch roles:*), Bash(ai-orch triage:*), Bash(ai-orch sync:*), Read, Glob, Grep
---

# The `.ai/` pipeline standard

Inside a `.ai/` project every agent runs under **production** prompting rules, not
casual ones. The difference is not tone — it is that the output has to be
verifiable and the pipeline has to survive running with nobody watching.

Casual prompting is fine in a direct chat. It is not what this pipeline is.

## 1. Nothing gets the whole task

The orchestrator decomposes before assigning. An agent handed "refactor auth"
invents scope; an agent handed one step with a completion condition does not.

Every step carries a **`done_when`** — the condition that makes it checkable.
A step without one is an intention, and the validator rejects it:

```json
{"id": "S-1", "goal": "Extract token validation",
 "done_when": "tests/test_auth.py passes", "depends_on": []}
```

If a step turns out to be underspecified, the executor returns
`status: "blocked"` with `blocked_on` — it does **not** re-plan. Re-planning is a
new chain with a new `task_id`, which is what keeps a pipeline from looping
forever without a human seeing it.

## 2. Agents hand over envelopes, not prose

Prose between agents is where hallucination enters: the receiver has to
*interpret*, and interpretation invents. A structured envelope removes the
interpretation step — the next agent consumes fields.

```
planner ──▶ executor ──▶ qa ──┬─▶ executor   (rejected: back for another pass)
                              └─▶ none       (approved: chain ends)
```

Nothing routes back to the planner. That is enforced, not conventional.

## 3. The envelope, and validating it

```json
{
  "schema": "ai-orch/v1",
  "role": "executor",
  "task_id": "T-001",
  "status": "ok",
  "summary": "Extracted token validation into validate_token()",
  "changes": [{"path": "src/auth.py", "action": "modified",
               "why": "S-1: validation was inline and untestable"}],
  "evidence": ["pytest tests/test_auth.py: 12 passed"],
  "next_role": "qa"
}
```

Validate before handing on — never after:

```bash
ai-orch validate envelope.json --role executor
```

Exit 0 prints the routing decision. Exit 1 lists every violation at once, each
with the exact field path (`steps[0].done_when`), so you fix them in one pass
instead of one round-trip per field.

Role-specific required fields: planner → `steps`, executor → `changes`,
qa → `verdict` + `findings`. `ai-orch validate` is the authority on the rest;
read `src/aiorch/pipeline.py` if you need the full rule set.

**`status: "ok"` requires `evidence`.** A claim without something checkable
behind it is the shape hallucination takes. This is the same rule
`analyze`/`qa` already enforce on metrics, applied to the chain.

## 4. Do not force reasoning that already happens

On a reasoning model, "think step by step", `<scratchpad>` instructions, and
"take a deep breath" are redundant at best and actively degrade output at worst
— current models follow instructions more literally, so a script written for an
older generation freezes that generation's behavior into a better model.
Control depth with configuration (`thinking: {type: "adaptive"}` and
`output_config.effort`), not with prose.

Three related habits are not merely discouraged — **they are hard API errors on
current models**, so code carrying them fails outright rather than degrading:

| Habit | What happens now |
| --- | --- |
| Assistant-turn prefill (`{"role": "assistant", "content": "{"}`) | **400.** Use structured outputs (`output_config.format`). |
| `thinking: {budget_tokens: N}` | **400.** Use `{type: "adaptive"}` + `effort`. |
| `temperature` / `top_p` / `top_k` on thinking models | **400.** Remove them. |

When you delete a prefill, delete the scaffolding built around it too — the
stop-sequences guarding JSON, the regex extraction, the retry-on-parse loop, the
"output ONLY valid JSON" line. Those existed to serve the prefill.

**Few-shot is where the brief oversimplifies, so be careful:** the rule is not
"use fewer examples". Examples of *judgment the model already owns* should go —
they freeze old behavior. Examples that **pin a format-sensitive output shape
stay**, labeled illustrative. This pipeline's envelopes are exactly that case:
keep the worked envelope examples above.

And do not confuse cruft with length. Context — the audience, the constraints,
and the *reasons* for them — is never cruft. A too-short role prompt produces
generic work because the model fills the gaps with safe defaults.

## 5. Role prompts are code

Each role in `.ai/config.json` carries a `version` and a `prompt_changelog`:

```bash
ai-orch roles     # every role and its prompt version
```

Changing a role prompt is a release, not an edit:

1. Bump the `version` (semver — a behavior change is not a patch).
2. Add a `prompt_changelog` line saying what changed and why.
3. **Evaluate against real cases before replacing the old version.** Not vibes
   — a set of real inputs, run both ways, compared. `/claude-api build-eval`
   builds the set and `/claude-api hillclimb` iterates against it.

An unversioned role prompt cannot be changed safely, which is why `ai-orch roles`
flags one as a gap rather than passing it silently.

## 6. QA stays fresh

The QA agent reviews **without having been in the task** — that independence is
the safeguard, and it does not change. What changed is the input: QA now
receives a structured envelope rather than the executor's prose, so its review
is comparable across runs instead of shaped by however the executor wrote it up.

Two rules the validator enforces on QA specifically:

- Every finding needs `evidence`. A finding without it is an opinion.
- **You cannot return `verdict: "approved"` while a P0 finding stands.**

A rejected verdict must say what is wrong; it routes back to the executor.

## 7. Before you finish

The pipeline standard does not replace the session rituals — `/ai-orch:arrival`
on the way in, `ai-orch sync --note "..."` on the way out. A chain that produced
good work and recorded nothing has still lost it.
