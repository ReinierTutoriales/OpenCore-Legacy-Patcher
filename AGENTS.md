# OpenCore Legacy Patcher — Agent Instructions

## Project
Python-based GUI/CLI tool that builds and applies OpenCore configurations and root patches so unsupported Macs can run modern macOS (Big Sur and newer). Fork focused on Intel builds.

## Stack
- Python 3.6+ (CI uses 3.11)
- wxPython GUI
- PyObjC, PyInstaller
- Core logic in `opencore_legacy_patcher/`
- Payloads and configs under `payloads/`
- Build: `Build-Project.command` or GitHub Actions (`macos-15-intel` for Intel binary)

## Commands
```sh
pip3 install -r requirements.txt
python3 OpenCore-Patcher-GUI.command          # GUI
python3 OpenCore-Patcher-GUI.command --help   # CLI
python3 Build-Project.command                 # produce .app
```
Prefer the Intel CI runner for release builds (see README-FORK.md).

## Priorities
- Preserve boot safety: never invent OpenCore config keys, kexts, or patch behaviors not present in the code or Acidanthera docs.
- Prefer native/stable APIs and existing patterns. Keep changes small and measurable.
- Do not break SIP, FileVault, Secure Boot, or recovery paths.
- Manage dependencies carefully; pin or justify updates (see requirements.txt).
- Validate against real hardware when possible; note remaining physical validation needs.
- Match existing code style (see .flake8 / .pylintrc).

## Working style
1. Brief analysis + risks (especially boot, SIP, hardware-specific patches).
2. Propose the smallest grounded solution.
3. Implement cleanly, matching existing style.
4. Verify against existing code, configs, and tests if any.
5. State what is verified vs. what needs real Mac validation.

## Rules
- Match existing Python style and patterns.
- Keep changes focused; do not touch unrelated files.
- Prefer the simplest correct fix.
- Update CHANGELOG or relevant docs when user-facing behavior changes.
- Do not invent hardware support or OpenCore settings.

## Skills
Use skills from `.agents/skills/` when relevant, especially `precise-coding` for any code change.
