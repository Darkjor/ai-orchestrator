# Architecture Decisions

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

## [DEC-001] AI Orchestrator v2 folder setup
**Date**: 2026-06-05
**Status**: Active
**Context**: Need a standard communication mechanism for asynchronous multi-agent development.
**Decision**: Adopt the `.ai/` documentation folder containing universal status, alerts, decisions, wheels, and discussions.
**Rationale**: Keeps all agents aligned, avoids code reinvention, and handles token/session constraints gracefully.
**Consequences**: Requires developers/agents to run arrival/departure protocol on every session.
**Revisit when**: The project is completed or another workflow tool is introduced.
