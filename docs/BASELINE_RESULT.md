# Resultado del baseline de PharmaGo

El 6 de noviembre de 2026 se construyó y levantó PharmaGo en un proyecto Compose aislado. Los ocho servicios quedaron activos. Pasaron catorce comprobaciones funcionales y de telemetría a las 17:32 y nuevamente a las 17:34, hora de Uruguay, tras detener y volver a iniciar sin recargar datos. El entorno queda corriendo al cerrar este incremento.

## Resultado verificado

| Comprobación | Resultado | Evidencia |
|---|---|---|
| Angular por HTTP | 200 y documento con `app-root` | `evidence/baseline-20261106/functional-run/summary.json` |
| Gateway → Users → SQL | 200 y tres roles persistidos | Ambos `summary.json` funcionales |
| Gateway → Pharmacy → SQL | 200 y cuatro medicamentos persistidos | Ambos `summary.json` funcionales |
| Login de demostración | 200 y token no vacío; contraseña/token no guardados | Ambos `summary.json` funcionales |
| Correlación de logs | Header preservado y evento `Login succeeded` con el mismo ID, JSON con scopes | `functional-run/login-event.json` y `after-stop-start/login-event.json` |
| Prometheus | Cuatro jobs up: gateway, users, pharmacy y Collector | `prometheus-targets.json` en ambos runs |
| Métrica funcional | Petición `/api/drug` exitosa observada en Prometheus | `request-metric.json` en ambos runs |
| Grafana | API de salud HTTP 200 | Ambos `summary.json` funcionales |
| Persistencia al parar/iniciar | Sin seed en el segundo arranque: mismos tres roles/cuatro medicamentos y login válido | `after-stop-start/summary.json` |
| Recursos | Ocho contenedores running, ningún OOMKilled; unos 1,23 GiB de memoria de contenedores en la captura de 17:35 | `containers.json` y `resource-usage.json` |

Las rutas de evidencia de la tabla parten de `evidence/baseline-20261106/` cuando no incluyen ese prefijo. La medición de memoria es una captura puntual, excluye sobrecarga del motor/host y no constituye prueba de capacidad bajo carga. Los tiempos HTTP registrados incluyen calentamiento; no son un estudio de rendimiento.

## Cambios realizados

- `Implementacion K8S/Codigo/compose.baseline.yaml`: proyecto `pharmago-baseline`, ocho servicios, volúmenes propios, puertos solo en loopback, espera de SQL, límites de memoria/CPU y logs rotados. Reutiliza configuraciones docentes de métricas y Grafana. SQL Express mantiene datos en volumen propio.
- `.env.example` y `.env` local ignorado: contraseñas aleatorias para SQL y Grafana; el script conserva cualquier `.env` previo. Ninguna contraseña generada se añadió a Git.
- `scripts/start-baseline.ps1`, `stop-baseline.ps1` y `smoke-baseline.ps1`: construcción secuencial, arranque validado, seed opt-in, parada sin borrado y evidencia funcional sanitizada. El arranque exige capacidad mínima del motor y evita compilar con el baseline activo.
- `Frontend/Dockerfile`: `npm ci` desde el lockfile, configuración production explícita y límites de workers/heap para la compilación.
- `.dockerignore` de Backend/Frontend: exclusión de compilados, cachés y archivos locales de los contextos de build.
- Guía `Implementacion K8S/Codigo/BASELINE.md`; plan de implementación, matriz, consultas docentes, borradores de issues y procedimiento inicial de incidentes en `docs/`.

El Compose original y los manifiestos de Kubernetes del curso no se modificaron durante el baseline. No se ejecutó caos. Las capturas se obtuvieron antes del primer commit del baseline; por eso identifican el commit del curso como fuente y un árbol de trabajo todavía modificado. La publicación posterior y el trabajo pendiente se siguen desde el README y el mapa de issues.

## Comandos ejecutados y evidencias

Desde el fork se verificaron status/remotes/ramas/commit y se ejecutó `git fetch origin feature/k8s feature/docker-compose` sin integrar cambios. Desde `Implementacion K8S/Codigo/`:

```powershell
.\scripts\start-baseline.ps1 -SeedDemoData
.\scripts\smoke-baseline.ps1 -DemoCredential $demoCredential -EvidenceDirectory '..\..\docs\evidence\baseline-20261106\functional-run'
.\scripts\stop-baseline.ps1
.\scripts\start-baseline.ps1 -SkipBuild
.\scripts\smoke-baseline.ps1 -DemoCredential $demoCredential -EvidenceDirectory '..\..\docs\evidence\baseline-20261106\after-stop-start'
```

La credencial de laboratorio se construyó en memoria usando el usuario del seed suministrado. El primer intento de smoke encontró un error en el propio script al tratar como booleano una comparación de cabecera multivalor de PowerShell. Se corrigió uniendo los valores antes de comparar; el intento fallido se conserva en `first-run/summary.json`, seguido de las dos ejecuciones aprobadas. No fue un fallo de la aplicación.

También pasaron `docker compose config --quiet`, análisis sintáctico PowerShell y `git diff --check`. Los cuatro builds terminaron con advertencias de C#/dependencias/CSS, sin errores; esas advertencias no se corrigieron como parte del baseline. Los IDs de imágenes, digests disponibles y versiones están en `application-images.json`, `runtime-images.json` y `environment-public.json`.

## Límites y pendientes

La comprobación de Angular fue HTTP. El intento de abrir un navegador automatizado agotó el tiempo de espera de la herramienta; no se verificó interacción real ni se ejecutaron Cypress/Cucumber. No se demuestra todavía K8s, separación física, despliegue sin interrupción, trazas completas, ELK, cinco alertas, recuperación bajo caos ni detectores ML. La salida directa `Console.WriteLine` existente tampoco queda convertida en JSON por configurar el logger; solo se verificó el evento de negocio indicado.

Q01–Q04 siguen abiertas en `aiops-open-questions.md`. El siguiente incremento es auditar/corregir scripts de K8s y PVs sin borrar datos, definir la topología local/física y el alcance de DB/migraciones, y habilitar las métricas de infraestructura antes de pruebas de recuperación/rollout.

## Acceso y operación

Aplicación: http://127.0.0.1:4200; Prometheus: http://127.0.0.1:9090; Grafana: http://127.0.0.1:3000. Las credenciales locales de Grafana están en `.env`; el seed docente describe las de la aplicación. La guía `BASELINE.md` incluye parada/reinicio sin borrar datos.
