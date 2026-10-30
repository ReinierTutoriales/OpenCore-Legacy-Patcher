# OpenCore Legacy Patcher — ReinierTutoriales

Fork experimental basado en **Dortania 3.0.0-rc.5**, con los cambios oficiales posteriores hasta `e2107e05`. Conserva el conjunto oficial de OpenCore **1.0.6**, kexts y PatcherSupportPkg **2.0.5**. No es una versión oficial ni una versión estable.

## Componentes

| Componente | Versión |
|---|---|
| OpenCore / OpenRuntime / OpenCanopy / ocvalidate | 1.0.6 |
| Lilu | 1.7.2 |
| WhateverGreen | 1.7.1 |
| AirportBrcmFixup | 2.2.1 |
| NVMeFix | 1.1.3 |
| BlueToolFixup | 2.7.2 |
| CPUFriend | 1.3.0 |
| FeatureUnlock | 1.1.8 |
| DebugEnhancer | 1.1.1 |
| CryptexFixup | 1.0.5 |
| PatcherSupportPkg | 2.0.5 |
| AppleALC | 1.6.3-Jazzzny, igual que Dortania |

`payloads/Kexts/Acidanthera`, `payloads/OpenCore` y la plantilla de configuración coinciden con Dortania `e2107e05`. Se conserva OpenCore 1.0.6 por la reversión oficial `3096fa9`, junto con su validador. AppleALC utiliza la variante oficial 1.6.3-Jazzzny para modelos antiguos. La actualización incluye los mapas USB oficiales reestructurados, nuevas kexts específicas y PatcherSupportPkg 2.0.5.

RestrictEvents conserva la compilación rolling 1.1.7 de Dortania: la publicación etiquetada 1.1.6 es anterior. WhateverGreen 1.6.9-Navi conserva el parche especial de retroiluminación para Navi MXM. Las extensiones antiguas de Apple y los inyectores específicos de modelo siguen asociados al conjunto de parches de OCLP: sustituirlos por archivos de un macOS moderno elimina su propósito.

`ci_tooling/components.lock.json` registra versiones, excepciones, fuentes y SHA-256 de los payloads. `requirements.txt` fija las dependencias Python directas a las versiones consultadas el 16-10-2026; Cocoa reemplaza al metapaquete completo PyObjC. La CI conserva también `pip freeze` para identificar las dependencias transitivas resueltas.

## Compilación y comprobaciones

### Sincronización oficial

`Sync Dortania candidate` comprueba diariamente a las 09:23 UTC el `main` de Dortania, y también permite una ejecución manual. Fusiona el código oficial completo en `auto-sync/dortania`, junto con OpenCore, kexts y referencias de versiones. Usa una fusión de tres vías: conserva las modificaciones del fork y detiene la ejecución si encuentra conflictos, sin elegir automáticamente una de las dos versiones.

Abre un PR en borrador y solicita explícitamente `Build fork candidate` mediante `workflow_dispatch`, porque un push hecho con `GITHUB_TOKEN` no dispara los workflows normales de push. La validación incluye inventario, pruebas, configuraciones, recursos y empaquetado. No fusiona el PR ni publica una versión. Si el oficial cambia los archivos o versiones registrados en `components.lock.json`, la verificación exige revisar y actualizar el inventario; la automatización no acepta nuevos hashes a ciegas.

El calendario solo queda activo cuando este workflow está integrado en `main`; las ramas de actualización se comprueban antes de integrarse. GitHub debe permitir a Actions crear pull requests en este repositorio; si esa opción está deshabilitada, el trabajo lo indicará como un error de permisos. No requiere un token personal adicional.

### Validación y paquetes

El workflow **Build fork candidate** compila el commit de este repositorio en `macos-15-intel`, Python 3.11. No descarga la rama mutable de TechPrototyper ni elimina publicaciones o etiquetas existentes.

Antes de empaquetar ejecuta:

```sh
python ci_tooling/verify_components.py
python -m unittest discover -s tests -v
python OpenCore-Patcher-GUI.command --validate
```

Después comprueba que la aplicación empaquetada puede abrir su CLI. Los artefactos incluyen los paquetes, sus SHA-256, las dependencias resueltas y la procedencia del build. No se publican automáticamente como versión estable.

Los tres paquetes se ofrecen individualmente, con los nombres del original: `OpenCore-Patcher.pkg`, `OpenCore-Patcher-Uninstaller.pkg` y `AutoPkg-Assets.pkg`. Los hashes y datos de compilación se entregan aparte en `OpenCore-Patcher-Intel-build-info`. Ya no se agrupan los dos paquetes grandes en una descarga conjunta ni se duplica AutoPkg. `AutoPkg-Assets.pkg` conserva el propósito definido por Dortania: lo utiliza el parcheador; para instalar la aplicación manualmente corresponde `OpenCore-Patcher.pkg`.

El validador conserva el proceso original de Dortania: genera configuraciones para los modelos compatibles y las capturas de hardware, las comprueba con `ocvalidate` y revisa los recursos de los parches. El ejecutable `ocvalidate` coincide con el de OpenCore 1.0.6. Las comprobaciones de recursos incluyen Tahoe y respetan las versiones Darwin terminadas en `.0`, sin sustituirlas por la versión del equipo anfitrión. La imagen de recursos se desmonta también cuando falla una comprobación; si el desmontaje devuelve un error, solo se acepta como completado tras comprobar que el volumen ya no está montado.

En el original revisado (`e2107e05`), la comprobación de recursos recorre Darwin 20–24 (Big Sur–Sequoia), con versiones menores 0–9; este fork conserva esos casos y añade Darwin 25 (Tahoe), para un total de 60 combinaciones. El sistema anfitrión de la CI es distinto: Dortania usa su runner Intel Monterey y aquí se usa `macos-15-intel`. Los workflows originales `CI - Validation` y `CI - Build wxPython` están restringidos al propietario `dortania` y aparecen omitidos en un fork. Aquí se ejecutan `CI - Validation (External)` y `Build fork candidate`, que invocan el mismo punto de entrada `--validate`.

## Instalación y recuperación

La instalación prepara los archivos en la partición EFI, verifica sus hashes y conserva los archivos anteriores en `.OCLP-Backups/<identificador>/`. Un bloqueo impide instalaciones simultáneas. Un error durante el reemplazo activa la restauración; si esta falla, se conservan el bloqueo y el registro de recuperación. No se modifica `EFI/Microsoft`.

`transaction.json` enumera los archivos gestionados, los que existían antes y el estado. Para una recuperación manual desde otra instalación o un USB arrancable: montar la misma EFI, comprobar el estado, preservar una copia del contenido actual y restaurar únicamente las rutas de `previous` desde el respaldo. Las rutas gestionadas nuevas que no figuren en `previous` no pertenecían a la instalación anterior. No eliminar el bloqueo hasta completar la recuperación.

Las operaciones sobre varias carpetas FAT no son atómicas frente a pérdida de energía. Las pruebas de archivos y configuración no sustituyen una prueba de arranque desde USB, sonido, Wi-Fi, Bluetooth, suspensión y root patching en el Mac objetivo.

## Firma del helper privilegiado

Los paquetes del workflow son **candidatos sin firma/notarización**. El helper original comprueba que la aplicación esté firmada por Dortania; una aplicación de este fork sin esa firma no puede utilizarlo para operaciones privilegiadas. No se desactiva esa comprobación ni se distribuye un helper SUID de depuración.

Para una distribución funcional con permisos elevados hace falta una identidad Developer ID propia, compilar el helper con el Team ID correspondiente y firmar la aplicación y el paquete. Véase `ci_tooling/privileged_helper_tool/README.md`. Compilar correctamente o abrir la GUI no demuestra que el helper acepte las operaciones.

Créditos: Dortania, colaboradores de OCLP, Acidanthera y TechPrototyper.
