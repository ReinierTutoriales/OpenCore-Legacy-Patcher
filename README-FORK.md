# Fork ReinierTutoriales — OpenCore Legacy Patcher

Build propio de la línea **TechPrototyper** (investigación hacia Dortania).

## Arquitectura del build

| Runner de GitHub | CPU | Resultado |
|------------------|-----|-----------|
| `macos-14` / `macos-15` / `macos-latest` | **Apple Silicon (ARM)** | App solo ARM — **no** sirve en Macs Intel típicos de Hackintosh |
| **`macos-15-intel`** | **Intel x86_64** | App **Intel** — la que necesitas |

Este fork compila en **`macos-15-intel`** para generar **OpenCore-Patcher para Intel**.

El `.spec` usa la arquitectura del runner (`x86_64` o `arm64`). No se fuerza `universal2` en CI porque wxPython de pip no viene como fat binary y PyInstaller falla.

## Compilar

1. [Actions](../../actions) → **Build OCLP Release (unsigned)** → **Run workflow**
2. [Releases](../../releases) → `OpenCore-Patcher.pkg` (tag `v*-intel-*`)

## Notas

- No es el release oficial de Dortania (ellos usan runner privado + firma).
- Build **sin** notarizar: en macOS puede hacer falta clic derecho → Abrir.
- Base: [TechPrototyper/OpenCore-Legacy-Patcher](https://github.com/TechPrototyper/OpenCore-Legacy-Patcher)

Créditos: Dortania · TechPrototyper · Acidanthera
