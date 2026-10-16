---
name: precise-coding
description: Use when writing or modifying any code. Forces grounded output by verifying against the existing codebase. Reduces hallucinations and token waste.
---

# Precise Coding (Anti-Hallucination)

1. Read the relevant existing Python modules, configs, payloads, and docs before writing anything.
2. Never invent OpenCore config keys, kext names, patch sets, hardware models, or behaviors not already present or clearly documented.
3. If unclear, state the assumption explicitly instead of inventing.
4. Prefer the smallest change that matches existing patterns and preserves boot safety.
5. Do not claim correctness or successful build unless reasoned from the actual project files.
6. Write only the precise code needed. Avoid speculative refactors or unused helpers.

Every line must be traceable to existing code or a clearly labeled minimal assumption.
