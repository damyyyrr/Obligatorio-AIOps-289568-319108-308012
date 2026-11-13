# Issue #15 — BDD real y corrección de duraciones

**Resultado: PASS, cuatro escenarios aprobados sin fallidos, pendientes ni omisiones.**

## Procedencia y entorno

- Rama `feature/issue-15-automatizar-escenarios`, con `obligatorio` integrado sin descartar los cambios de ML.
- Commit ejecutado: `9a420f175b6bd4ea69f02c8c168b455a47af7ce0`; árbol limpio (`workingTreeDirty=false`). Los commits posteriores de esta evidencia solo agregan documentación y artefactos sanitizados.
- Windows 11, aproximadamente 15,95 GiB físicos; Docker Desktop Linux, motor de 7,73 GiB; alrededor de 3,5 GiB físicos disponibles al comprobar el resultado.
- Node 22.16.0, Cypress 15.18.0, Electron 138.0.7204.251 headless. Angular se compila con Node 16 dentro de su Dockerfile.
- Ejecución 12/11/2026, 18:20:56–18:21:11 de Uruguay (UTC en el resumen original).

## Corrección y verificaciones

El reporte anterior sumaba `attempt.wallClockDuration`, campo ausente en el contrato público instalado de Cypress 15, y guardaba cero en todos los escenarios. Ahora usa `TestResult.duration`. Un dato ausente, negativo o no finito se registra como null; un cero medido se conserva. Se sigue excluyendo el objeto completo de Cypress y sus detalles privados.

Pasaron tres pruebas del contrato del resumen, los dos controles negativos del runner (credenciales ausentes y paso indefinido), Gherkin/pasos/bundle de cuatro escenarios y 15 pasos, sintaxis de scripts y `git diff --check`. Las tres regresiones forman parte del CI de preparación. La instalación limpia de e2e con su lockfile y la verificación del binario Cypress se habían realizado en la revisión previa; no se cambiaron dependencias en esta corrección.

Se ejecutó `scripts/start-baseline.ps1 -SeedDemoData` desde esta rama: construyó las cuatro imágenes secuencialmente, aplicó migraciones y seed no destructivo y aprobó los checks HTTP de ocho servicios. Después, desde `Frontend/e2e`, con Node 22.16:

```powershell
npm run check
npm run check:guards
npm run check:results
npm run test:demo
```

En el equipo, los mismos scripts se invocaron mediante `npm exec --package=node@22.16.0 -- node ...` para seleccionar esa versión sin cambiar el Node global. El runner real fue `node scripts/run.cjs --demo`.

## Resultado observado

| Escenario | Estado | durationMs del resumen |
|---|---|---:|
| Administrador con credenciales válidas | passed | 2351 |
| Contraseña incorrecta y reintento sin recargar | passed | 1976 |
| Catálogo y detalle | passed | 802 |
| Medicamento inexistente y regreso al catálogo | passed | 2190 |

El resumen de la API de Cypress incluye el tiempo del test; puede diferir ligeramente del tiempo que su reporter imprime en consola. Se observan rutas, sesión, errores y contenido visible real, sin respuestas HTTP simuladas. La guardia de login evitó crear sesión tras la contraseña incorrecta y permitió el reintento.

[Resumen original](summary.json) · [captura pública](catalogo-detalle.png).

La captura se revisó: muestra medicamento, farmacia, precio, código, presentación y síntomas, sin credenciales ni tokens. No se publican logs de contenedores, videos, objetos completos de Cypress ni formularios de acceso. El baseline se detuvo con `scripts/stop-baseline.ps1`, preservando sus volúmenes.

## Alcance

Esta ejecución acredita los criterios funcionales de #15. El CI anterior ya había aprobado preparación/build Angular, pero omitido `live`; la ejecución descrita aquí es local. No se ejecutó el runner interactivo ni el job manual remoto. No acredita disponibilidad bajo fallas, recuperación ni los seis ensayos de caos. El PR queda listo para revisión e integración; no se cerró automáticamente la issue.
