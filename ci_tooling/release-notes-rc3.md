Fork experimental de ReinierTutoriales basado en OCLP 3.0.0-rc.3, con las actualizaciones oficiales de Dortania y correcciones de la aplicación.

- OpenCore y kexts Acidanthera idénticos a Dortania `8da38565`; PatcherSupportPkg 2.0.3.
- Correcciones de descargas, ajustes, actualización de la app, callbacks de interfaz y manejo de errores de copia.
- Sincronización diaria de novedades oficiales mediante PR y validación.
- 75 pruebas, validación de configuraciones y recursos, compilación Intel y apertura de la CLI empaquetada aprobadas en macOS.

Para instalar la aplicación, descargar **OpenCore-Patcher.pkg**. **AutoPkg-Assets.pkg** es para uso interno del parcheador; no ejecutarlo manualmente. Se incluye el desinstalador por separado.

**Candidato sin firma ni notarización.** El helper original exige una firma Developer ID de confianza: este paquete sin firma no está validado para operaciones privilegiadas. No se ha desactivado esa comprobación. Arranque, sonido, red, interfaz gráfica y root patching requieren pruebas en el Mac objetivo. No es una versión estable oficial de Dortania.

Fuente de los paquetes: `d2c9532f7d465d99fd2143338caa551b0b567c6e`, [compilación verificada](https://github.com/ReinierTutoriales/OpenCore-Legacy-Patcher/actions/runs/39062582425). Se adjuntan SHA-256, procedencia y dependencias resueltas.
