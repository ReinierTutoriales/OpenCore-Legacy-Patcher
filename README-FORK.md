# Fork ReinierTutoriales — OpenCore Legacy Patcher

Build propio de la línea **TechPrototyper** (investigación / cooperación hacia la versión nueva de Dortania).

| | |
|--|--|
| **Upstream investigación** | [TechPrototyper/OpenCore-Legacy-Patcher](https://github.com/TechPrototyper/OpenCore-Legacy-Patcher) |
| **Proyecto original** | [dortania/OpenCore-Legacy-Patcher](https://github.com/dortania/OpenCore-Legacy-Patcher) |
| **Versión en árbol** | 2.5.0 (`constants.py`) |
| **Compilar** | Actions → **Build OCLP Release (unsigned)** → Run workflow |

## Importante

- Este fork **no** es el release oficial de Dortania.
- Los builds de CI salen **sin** firma ni notarización de Apple (Gatekeeper puede avisar).
- El workflow oficial de Dortania solo se ejecuta en el repo `dortania` (runner propio + certificados).

## Uso

1. [Actions](../../actions) → workflow **Build OCLP Release (unsigned)** → **Run workflow**
2. Cuando termine: [Releases](../../releases) → descarga `OpenCore-Patcher.pkg`
3. En macOS: clic derecho → Abrir (si Gatekeeper bloquea el unsigned build)

## Relación con otras guías ReinierTutoriales

- Broadcom Wi‑Fi Sequoia: root patch **Modern Wireless** con OCLP
- Intel Wi‑Fi: [itlwm-AirportItlwm-LQM](https://github.com/ReinierTutoriales/itlwm-AirportItlwm-LQM)

Créditos: Dortania · TechPrototyper · Acidanthera
