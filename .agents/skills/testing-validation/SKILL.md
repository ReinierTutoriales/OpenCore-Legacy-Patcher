---
name: testing-validation
description: Use when adding features or changing logic. Emphasizes verification against existing code and the need for real-hardware validation.
---

# Testing & Validation

- Prefer reasoning about and running the GUI/CLI entry points where possible.
- Do not relax existing checks or safety paths.
- A change is incomplete until consistent with existing code, configs, and known hardware support matrices.
- Explicitly call out gaps that still need real Mac (Intel) hardware validation.
- Prefer the Intel CI path for release-related changes (see README-FORK.md).
