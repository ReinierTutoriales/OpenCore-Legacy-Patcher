---
name: dependency-management
description: Use when adding, updating, or reviewing Python dependencies. Focuses on stability, compatibility, and minimal surface.
---

# Dependency Management

- Prefer the smallest set of dependencies that solve the problem.
- Check existing requirements.txt and pin or justify any version change.
- Verify compatibility with Python 3.11 (CI) and the wxPython / PyObjC stack.
- Avoid unnecessary third-party libraries when stdlib or existing packages suffice.
- Note any risk of regression or platform-specific issues (especially Intel vs ARM builds).
- Update requirements.txt and relevant docs in the same change.
