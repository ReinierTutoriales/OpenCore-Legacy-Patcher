Candidato experimental basado en los cambios de Dortania hasta e2107e05, con OpenCore 1.0.8 y PatcherSupportPkg 2.0.5.

Incluye PyObjC Core/Cocoa 13.0 para Python 3.11, kexts actuales verificadas, AppleALC 1.9.8 opcional y la variante Jazzzny por defecto para compatibilidad antigua. Corrige ajustes malformados, operaciones de copia, callbacks de UI y el aviso de actualización con diez segundos para cancelar. Evita calcular dos veces los hashes de los paquetes.

Para instalación manual: OpenCore-Patcher.pkg. AutoPkg-Assets.pkg es para uso interno del parcheador. Los paquetes se acompañan de SHA256SUMS.txt y procedencia con el commit exacto de construcción.

Paquetes sin firma ni notarización: el helper original exige una firma Developer ID de confianza para las operaciones privilegiadas. Pruebas automatizadas y validación de configuraciones no sustituyen arranque, audio, red, suspensión, UI y root patching en el Mac objetivo. No es una versión estable oficial de Dortania.
