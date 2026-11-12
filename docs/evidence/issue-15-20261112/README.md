# Issue #15 — preparación y traspaso, 12/11/2026

**Actualización posterior: cuatro escenarios reales aprobados y reporte corregido.** Ver [ejecución desde commit limpio, resumen y captura](live-after-fix/README.md). El resto de este archivo conserva la preparación original, cuando todavía no se había iniciado el navegador.

Rama: feature/issue-15-automatizar-escenarios, creada desde obligatorio en 54d5a17c68cb7ede122b92862ad156163a0b09d9. [Guía ejecutable para el compañero](../../../Implementacion%20K8S/Codigo/Frontend/e2e/README.md).

## Estado

**Preparación validada; E2E real pendiente.** El usuario indicó que no podía liberar RAM y pidió dejar todo listo para otro compañero. En este incremento no se inició Docker, SQL, Kubernetes ni un navegador. No se ejecutaron los escenarios contra la aplicación ni el workflow de GitHub. No se cierra #15 ni se declara cumplimiento BDD por un dry-run.

## Cambios preparados

- Cuatro escenarios en español: login válido; contraseña incorrecta y reintento; catálogo y detalle; medicamento inexistente y regreso al catálogo.
- Cypress 15.18.0 + Cucumber preprocessor 26.0.0 + esbuild 0.28.2, con lockfile independiente del de Angular 14. Node 22.16; Angular conserva Node 16 en el Dockerfile.
- Datos de laboratorio del seed docente, fixture pública de PARA001 e ID inexistente. No hay resets ni respuestas de API simuladas. Login puede crear/reutilizar la sesión de laboratorio.
- Selectores data-cy y guardia para el resultado vacío del login: antes, el servicio notificaba el error y luego el componente intentaba leer login.userName; ahora conserva el error y termina sin guardar sesión. El escenario negativo debe verificarlo en navegador.
- Resumen por intento con commit/estado del árbol, conteos, versiones y estados; captura pública de detalle. No se guarda el objeto completo de Cypress ni se publican credenciales, tokens, videos o capturas del login.
- CI acotado para preparación y build; ejecución real manual en runner de laboratorio. Ningún resultado remoto se presume aprobado.

## Comprobaciones de preparación

En Windows, Node 22.16.0 y npm 10.9.2, con CYPRESS_INSTALL_BINARY=0:

- npm install resolvió las versiones exactas y sus peers.
- npm ci --no-audit --no-fund completó una instalación limpia desde el lockfile, sin descargar el navegador.
- npm run check aprobó el dry-run de Cucumber: **4 escenarios y 15 pasos reconocidos y omitidos**, sin pasos ambiguos/ausentes. El bundler de esbuild compiló el feature con el plugin de Cypress/Cucumber y sus definiciones.
- La lectura opt-in de credenciales desde el seed se comprobó sin imprimir sus valores.
- node --check aprobó los scripts de ejecución, apertura y pasos.
- npm run check:guards aprobó dos controles negativos: credenciales ausentes producen exit 1/BLOCKED sin navegador; un paso indefinido produce exit 1 aunque Cucumber permita exit 0 en dry-run. Ambos son repetibles y forman parte del CI de preparación.
- Se validó la sintaxis YAML del workflow, sus tres jobs, los enlaces locales de la guía/evidencia y git diff --check.

Estos controles comprueban sintaxis, registro de pasos y empaquetado. No validan el build Angular ni el comportamiento real. La ejecución funcional sigue pendiente en otra PC.

## Evidencia necesaria para cerrar

Desde un commit limpio de esta rama, seguir la guía y adjuntar un summary.json PASS con cuatro escenarios ejecutados/aprobados, ninguna omisión y browserExecuted=true. Revisar la captura pública y registrar capacidad/versiones de la PC. Observar los pasos en el runner interactivo. Registrar y corregir fallos antes de pasar el PR a listo y actualizar la matriz. No copiar .runtime completo.

La asistencia de IA se utilizó para preparar escenarios, configuración, corrección de login y documentación; el equipo debe revisar el código y producir su propia validación real. Estos escenarios son regresión funcional desde el usuario; no sustituyen los ensayos de caos, la disponibilidad ni la defensa.
