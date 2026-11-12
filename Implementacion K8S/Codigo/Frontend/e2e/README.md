# BDD: Cypress + Cucumber — issue #15

**Preparado; ejecución real pendiente en otra PC.** La validación local de preparación no demuestra comportamiento del navegador. Ver [registro de preparación](../../../../docs/evidence/issue-15-20261112/README.md).

La suite recorre Angular → gateway → Users/Pharmacy → SQL con los cuatro escenarios de [pharmago.feature](features/pharmago.feature). Comprueba tanto las respuestas reales como los resultados visibles: panel/sesión del administrador, rechazo de contraseña con reintento en la misma página, catálogo/detalle y error 404 con regreso al catálogo. No hay respuestas simuladas ni un manejador que oculte excepciones de Angular.

## Preparar la PC del compañero

Usar Docker Desktop Linux, Git, PowerShell y **Node 22.16 o posterior de la serie 22** con npm. Angular 14 se construye dentro del Dockerfile con Node 16; sus dependencias están separadas de esta herramienta. Versiones exactas y lockfile: Cypress 15.18.0, preprocesador Cucumber 26.0.0, esbuild 0.28.2. No actualizar automáticamente a latest.

Se recomienda una PC de 16 GB con al menos 4 GB disponibles para Docker y memoria adicional para compilar y abrir Electron. El baseline exige 3,5 GiB asignados al motor. No ejecutar a la vez Minikube, ELK, caos u otras compilaciones. Estos valores son orientación de capacidad; esta suite aún no tiene medición real de consumo.

Desde la raíz del repositorio:

```powershell
git fetch origin
git switch feature/issue-15-automatizar-escenarios
git pull --ff-only
cd 'Implementacion K8S/Codigo'
# Construye las cuatro imágenes de ESTA rama, de a una, antes de iniciar los servicios.
# Si este baseline está activo, detenerlo primero con scripts/stop-baseline.ps1.
.\scripts\start-baseline.ps1 -SeedDemoData
if ($LASTEXITCODE -ne 0) { throw 'Revisar el arranque antes de seguir.' }
cd Frontend/e2e
npm ci --no-audit --no-fund
npm run check
npm run check:guards
npm run test:demo
```

El primer npm ci descarga el navegador Electron de Cypress. Si se instaló antes con CYPRESS_INSTALL_BINARY=0, quitar esa variable y ejecutar npx cypress install. En Linux, instalar las [dependencias de sistema de Cypress](https://docs.cypress.io/app/get-started/install-cypress#Linux-Prerequisites) y usar pwsh para el script Compose.

El arranque usa exclusivamente el proyecto pharmago-baseline y su .env ignorado; el seed docente agrega filas faltantes sin borrar ni actualizar datos existentes. Usar una PC/checkout de laboratorio, sin usuarios reales. No usar -SkipBuild la primera vez: una imagen UI vieja no contiene los selectores ni la corrección de login. Las migraciones las ejecuta el servicio pharmago-db-migrate, antes de Users/Pharmacy.

El modo test:demo lee la credencial Administrator del seed ya existente, solo con opt-in y contra direcciones locales fijas. No crea ni modifica usuarios desde la prueba. La fixture contiene únicamente expectativas públicas del medicamento PARA001; los IDs existentes se descubren al navegar. Si la cuenta o ese medicamento fueron alterados, resolver los datos de prueba con el responsable; no resetear la base. Para una cuenta Administrator de laboratorio distinta, definir BDD_USERNAME y BDD_PASSWORD solo en el entorno local y usar npm test. No escribirlas en archivos versionados ni en argumentos de Cypress.

## Ver y diagnosticar

- npm run open:demo abre el runner interactivo para observar cada paso; seleccionar E2E, Electron y pharmago.feature. npm run open usa las credenciales del entorno.
- npm run test:demo ejecuta en Electron headless; es un navegador real aunque no abra una ventana. El wrapper elimina ELECTRON_RUN_AS_NODE solamente de su propio proceso.
- Cada intento crea .runtime/runs/<fecha-id>/summary.json. PASS exige exactamente cuatro escenarios aprobados, sin fallidos, pendientes ni omitidos. FAIL indica resultados de la suite; BLOCKED indica que no terminó la preparación/ejecución.
- El resumen registra commit, árbol modificado, versiones, tiempos, conteos y estados. No copia la configuración, el entorno ni las respuestas con tokens. La captura catalogo-detalle.png muestra únicamente el detalle público. No se graban videos ni capturas automáticas de fallos de login.
- Ante un fallo, revisar la salida local, diagnostic.txt si existe y el runner interactivo. Si falta un data-cy, reconstruir la UI desde esta rama. Un 400 Invalid Password exige revisar la cuenta/seed; un 404 esperado es parte del cuarto escenario; un 429 exige detener otros generadores y esperar el límite del gateway.
- Las llamadas interceptadas solo se observan: cy.wait sincroniza sin pausas fijas ni reintentos de escenarios. La contraseña se escribe con log:false. El runner interactivo puede mostrar solicitudes y sesiones en memoria: no publicar grabaciones, capturas del login, objetos completos de Cypress ni logs de contenedores sin revisarlos.
- La suite limpia cookies/localStorage entre escenarios mediante testIsolation. No compra, modifica stock ni borra datos. El login puede crear o reutilizar la sesión del usuario de laboratorio en SQL.

Para detener conservando volúmenes, desde Implementacion K8S/Codigo:

```powershell
.\scripts\stop-baseline.ps1
```

El runner BDD no inicia ni detiene infraestructura por su cuenta.

## CI y cierre del trabajo

El workflow bdd.yml tiene comprobaciones automáticas para PRs a obligatorio: Gherkin/pasos/bundle sin navegador y build de Angular por separado. **Ninguna de ellas equivale a E2E aprobado.** La ejecución real es manual con workflow_dispatch y run_live=true en un runner Ubuntu dedicado: construye el baseline con seed, ejecuta los cuatro escenarios, adjunta resumen/captura pública y detiene los contenedores. Tiene timeout y permisos de solo lectura del repositorio. No dispara caos ni despliega a entornos compartidos. El workflow tampoco fue ejecutado durante la preparación local.

npm run check:guards verifica dos rechazos sin infraestructura: un paso sin definición no puede aprobar el control de preparación; la falta de credenciales impide abrir el navegador y genera BLOCKED. Los intentos de estos controles quedan en .runtime y no se publican como pruebas funcionales.

Para terminar #15, el compañero debe:

1. Ejecutar desde un commit limpio, comprobar PASS con 4/4 y observar al menos una vez los escenarios en el runner.
2. Revisar resumen y captura antes de copiarlos a una carpeta fechada de docs/evidence/issue-15-...; excluir archivos privados de .runtime.
3. Documentar commit, PC/capacidad, versiones, resultados y posibles correcciones. Repetir después de corregir fallos, sin ocultarlos.
4. Actualizar la matriz y el PR, solicitar revisión y pasar el PR de borrador a listo. La issue queda abierta hasta tener evidencia real.

En AIOps estos escenarios verifican la experiencia del usuario tras desplegar y sirven como base de regresión funcional. No prueban por sí mismos disponibilidad bajo fallas, tiempos de recuperación ni los seis ensayos de caos.

Referencias de configuración: [Cypress](https://docs.cypress.io/app/references/configuration), [Cucumber preprocessor](https://github.com/badeball/cypress-cucumber-preprocessor/blob/v26.0.0/docs/quick-start.md) y [Cypress GitHub Action](https://github.com/cypress-io/github-action).
