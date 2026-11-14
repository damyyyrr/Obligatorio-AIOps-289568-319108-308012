# Issue #15 — BDD validado y antecedentes de preparación

**Estado actual: PASS funcional local, cuatro escenarios reales aprobados; issue cerrada como completada.** Ver [ejecución desde commit limpio, resumen y captura](live-after-fix/README.md) y [cierre de la issue #15](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/15). Los apartados de preparación siguientes describen la etapa anterior a esa ejecución, no trabajo funcional pendiente.

Rama de implementación: feature/issue-15-automatizar-escenarios, creada desde obligatorio en 54d5a17c68cb7ede122b92862ad156163a0b09d9. [Guía de ejecución](../../../Implementacion%20K8S/Codigo/Frontend/e2e/README.md).

## Validación funcional realizada

El 12/11/2026 se ejecutaron los cuatro escenarios contra Angular, gateway y SQL reales desde el commit limpio `9a420f175b6bd4ea69f02c8c168b455a47af7ce0`. El [summary.json original](live-after-fix/summary.json) registra `status=PASS`, `browserExecuted=true`, `workingTreeDirty=false`, cuatro aprobados y cero fallidos, pendientes u omitidos. La captura pública fue revisada, se documentaron capacidad/versiones del equipo y se actualizó la [matriz](../../aiops-requirements-matrix.md).

La ejecución usó Electron headless: un navegador real sin ventana visible. No se ejecutaron el runner interactivo ni el job manual remoto de GitHub; no se presentan como comprobaciones realizadas. Esos modos no son requisitos adicionales de la letra, que pide BDD con Cypress + Cucumber.

## Antecedente de preparación

En la etapa inicial el usuario no podía liberar RAM y pidió dejar todo preparado para otro compañero. Entonces se validaron configuración y dry-run, sin iniciar Docker, SQL, Kubernetes ni navegador y sin declarar E2E aprobado. Esa limitación inicial se superó con la ejecución funcional enlazada arriba.

## Cambios implementados

- Cuatro escenarios en español: login válido; contraseña incorrecta y reintento; catálogo y detalle; medicamento inexistente y regreso al catálogo.
- Cypress 15.18.0 + Cucumber preprocessor 26.0.0 + esbuild 0.28.2, con lockfile independiente del de Angular 14. Node 22.16; Angular conserva Node 16 en el Dockerfile.
- Datos de laboratorio del seed docente, fixture pública de PARA001 e ID inexistente. No hay resets ni respuestas de API simuladas. Login puede crear/reutilizar la sesión de laboratorio.
- Selectores data-cy y guardia para el resultado vacío del login: antes, el servicio notificaba el error y luego el componente intentaba leer login.userName; ahora conserva el error y termina sin guardar sesión. El escenario negativo verificó este comportamiento y el reintento en la ejecución real.
- Resumen por intento con commit/estado del árbol, conteos, versiones y estados; captura pública de detalle. No se guarda el objeto completo de Cypress ni se publican credenciales, tokens, videos o capturas del login.
- CI acotado para preparación y build; ejecución real manual en runner de laboratorio. Ningún resultado remoto se presume aprobado.

## Comprobaciones iniciales de preparación

En Windows, Node 22.16.0 y npm 10.9.2, con CYPRESS_INSTALL_BINARY=0:

- npm install resolvió las versiones exactas y sus peers.
- npm ci --no-audit --no-fund completó una instalación limpia desde el lockfile, sin descargar el navegador.
- npm run check aprobó el dry-run de Cucumber: **4 escenarios y 15 pasos reconocidos y omitidos**, sin pasos ambiguos/ausentes. El bundler de esbuild compiló el feature con el plugin de Cypress/Cucumber y sus definiciones.
- La lectura opt-in de credenciales desde el seed se comprobó sin imprimir sus valores.
- node --check aprobó los scripts de ejecución, apertura y pasos.
- npm run check:guards aprobó dos controles negativos: credenciales ausentes producen exit 1/BLOCKED sin navegador; un paso indefinido produce exit 1 aunque Cucumber permita exit 0 en dry-run. Ambos son repetibles y forman parte del CI de preparación.
- Se validó la sintaxis YAML del workflow, sus tres jobs, los enlaces locales de la guía/evidencia y git diff --check.

Estos controles iniciales comprueban sintaxis, registro de pasos y empaquetado. El build Angular y el comportamiento real se comprobaron después, según la evidencia funcional enlazada arriba; no se atribuyen al dry-run.

## Evidencia de cierre disponible

- [Resumen original PASS](live-after-fix/summary.json): commit limpio, cuatro escenarios ejecutados/aprobados, ninguna omisión y `browserExecuted=true`.
- [Informe de ejecución](live-after-fix/README.md): capacidad/versiones de la PC, corrección del reporte de duraciones y resultados de las verificaciones.
- [Captura pública revisada](live-after-fix/catalogo-detalle.png) y [matriz actualizada](../../aiops-requirements-matrix.md).

Para repetir la suite o usar el runner interactivo como apoyo de revisión, seguir la guía de ejecución. No es necesario repetir la validación ya acreditada por conservarse aquí los antecedentes iniciales. Publicar solo evidencia revisada, nunca `.runtime` completo.

La asistencia de IA se utilizó en escenarios, configuración, corrección de login y documentación. La validación real está registrada en los artefactos enlazados; el equipo sigue siendo responsable de revisar y comprender el código y los resultados. Estos escenarios son regresión funcional desde el usuario; no sustituyen los ensayos de caos, la disponibilidad ni la defensa.
