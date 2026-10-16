---
name: boot-safety
description: Use when changing configs, patches, kexts, or anything that affects boot, SIP, FileVault, or recovery. Enforces extreme caution and grounding.
---

# Boot Safety

- Never invent or guess OpenCore settings, kext load order, or patch behavior.
- Prefer existing, documented patterns from the codebase and Acidanthera references.
- Changes that affect boot, SIP, Secure Boot, FileVault, or Recovery must be minimal and clearly justified.
- Explicitly state assumptions and remaining hardware validation needs.
- Do not relax existing safety checks or fail-closed behavior.
- When in doubt, leave the safer existing path intact and document the limitation.
