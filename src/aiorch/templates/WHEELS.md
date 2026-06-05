# Wheels & Patterns — What NOT to Reinvent

> Before writing any utility, installing a library, or designing a subsystem:
> Check this list. If a solution exists, USE IT.
> If you think we should change a solution, add a new entry to DECISIONS.md first.

---

## 1. Core Stack & Libraries in Use
List of established libraries to prevent agents from implementing custom alternatives or installing redundant packages.

- **[Category/Layer]**: [Library/Framework Name]. Do NOT implement custom alternatives.

## 2. Failed Experiments (What NOT to do)
Critical section to reduce hallucination. Explains what was tried, why it failed, and why we don't use it.

### [WHEEL-001] [Short title of failed experiment]
- **What was tried**: [What did we build/try to use]
- **Why it failed**: [Why didn't it work out]
- **What we do instead**: [The working alternative in the codebase]
- **Rule**: [Concrete instruction to future agents]

## 3. Standard Utility Patterns
- **[Utility Name]**: [Pattern or file location to use]. Do NOT write custom code for this.
