# Implementación de AIOps

## Estado al 14 de noviembre de 2026

Ver [estado contrastado](estado-actual.md) y [matriz](aiops-requirements-matrix.md). Las issues #2–#17 están cerradas; las evidencias de BDD, observabilidad, ML y seis escenarios de caos están integradas. #16 se cerró para plan y aplicación guiada local, con revisión independiente opcional no realizada. Siguen abiertas las consultas académicas #1, entrega #18, defensa #19 y ampliación opcional #20, según la [consulta de GitHub](evidence/docs-review-20261114/issues.json).

La corrección de aislamiento de `PurchasesDetailRepositoryTest` se integró mediante el PR #42. La [ejecución .NET del 14/11](evidence/test-isolation-20261114/README.md) aprobó 319/319 pruebas. Los apartados siguientes conservan los resultados de sus incrementos originales; sus conteos y equipos no describen automáticamente la candidata actual.

## Incremento del 12 de noviembre de 2026 — issue #15

Se preparan cuatro escenarios BDD de acceso y consulta con Cypress/Cucumber, dependencias aisladas de Angular, datos del seed de laboratorio, selectores estables, resumen de ejecución y CI. Se corrige el acceso a un resultado vacío después de un login rechazado. La [guía de traspaso](../Implementacion%20K8S/Codigo/Frontend/e2e/README.md) permite ejecutar y diagnosticar desde otra PC.

La preparación inicial se conserva como registro histórico. En la validación posterior se construyeron las cuatro imágenes, se inició el baseline con SQL y seed y se ejecutaron los cuatro escenarios en Electron: **4/4 PASS**, sin omisiones, desde el commit limpio `9a420f1`. Se corrigió el reporte de duración para la API pública de Cypress 15 y pasaron tres regresiones, además de los controles de preparación. La [evidencia real](evidence/issue-15-20261112/live-after-fix/README.md) incluye resumen, captura y límites del ensayo. Los cambios se integraron y #15 está cerrada. Se usó Electron headless; no se ejecutaron runner interactivo ni job remoto `live`.

## Incremento del 12 de noviembre de 2026 — issue #14

Se implementan y ejecutan Isolation Forest y One-Class SVM RBF sobre las 300 ventanas sintéticas del notebook docente, preservando el original y su protocolo: StandardScaler y ambos modelos se ajustan sobre toda la muestra, sin etiquetas ni selección de parámetros con ellas. La [guía ML](../ml/README.md) enlaza CLI, notebook ejecutado y dependencias fijadas. Los [resultados](evidence/issue-14-20261112/results/RESULTS.md) incluyen scores/flags por ventana, métricas, todos los FP/FN, tablas por tipo, gráficos y parámetros/versiones/hashes.

Pasaron 20 pruebas y dos ejecuciones CLI produjeron salidas numéricas idénticas; el notebook terminó sus siete celdas de código. F1 observado: IF 0,578313 y OCSVM 0,439024, evaluados sobre la misma muestra de entrenamiento, sin afirmar generalización. La [evidencia](evidence/issue-14-20261112/README.md) conserva alcance y procedencia. R05 tiene validación técnica del material disponible; Q03 y la aceptación académica permanecen pendientes. La ampliación del práctico sigue en #20. No se inició infraestructura.

## Incremento del 12 de noviembre de 2026 — issue #17

Se reemplazan los cuatro scripts heredados por wrappers de un controlador con simulación sin infraestructura, contexto local explícito, límites de carga, prechecks de capacidad/observabilidad, identidad de recursos, journal y watchdog. Se agregan corte de tráfico con NetworkPolicy y desconexión del Service Pharmacy. La [guía](../Implementacion%20K8S/Codigo/chaos-engineering/README.md) describe preparación, ejecución individual, aborto y recuperación, y las [evidencias](evidence/issue-17-20261112/README.md) distinguen regresiones/simulación de ensayos reales.

La revisión posterior corrigió aborto/arranque tardío, transporte LF desde Windows y medición por destino/conexión. Pasaron 45 + 5 + 26 tests del controlador, agente aislado y configuración, también en CI Linux. Después del primer precheck rechazado por memoria, el usuario liberó margen y se completaron **seis ensayos reales PASS** en un laboratorio nuevo con Calico: efectos observados, 120 s estables, limpieza independiente y PV/PVC/configuración conservados. Durante las pruebas se corrigió un HTTP 500 de Grafana/SQLite activando WAL, sin ocultar errores. Red y Service se verifican sobre conexiones nuevas, con la continuidad del Gateway existente registrada aparte. [Fichas, fuentes, intentos fallidos y evidencia](evidence/issue-17-20261112/fix-after-review/README.md). Los cambios se integraron y #17 está cerrada. La [repetición guiada del 13/11](evidence/issue-16-20261113/README.md) sustenta el cierre posterior de #16 para ese alcance; no acredita revisión independiente, comunicaciones externas ni tAck humano durante cada falla.

## Incremento del 12 de noviembre de 2026 — issue #16

Se amplía el [plan de incidentes](baseline-incidents.md) a Kubernetes y Compose con roles, severidades, canal, escalamiento y aborto, criterios funcionales de restauración y convención de tiempos del curso. Los [seis runbooks](runbooks/incidentes.md) cubren requests, CPU, RAM, disco, red y desconexión interna. Hay plantillas de [ficha/bitácora y comunicaciones](templates/incidente.md) y [postmortem](templates/postmortem.md).

La [evidencia inicial de #16](evidence/issue-16-20261112/README.md) distingue revisión de procedimientos y reconstrucción reproducible de tres ensayos históricos de #7 frente a ejecución nueva. En ese incremento no se inyectaron fallas, enviaron mensajes ni operaron contenedores. Después se incorporó la [ejecución guiada de seis casos del 13/11](evidence/issue-16-20261113/README.md) y [#16 se cerró con ese alcance](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/16). La revisión independiente quedó como mejora opcional no realizada; los tiempos y comunicaciones no registrados siguen indeterminados.

## Incremento del 11 de noviembre de 2026 — issue #8

Gateway, Users y Pharmacy incorporan drenaje antes de SIGTERM, timeout de apagado y permanencia mínima en Ready. El ensayo local de actualización y rollback registró 226/226 respuestas funcionalmente válidas en 282,139 s. Se observaron versiones coexistentes, se restauraron las tres plantillas y se conservaron el esquema, los registros comprobados y los volúmenes. La [guía](aiops-k8s-rollout.md) incluye el generador reproducible y la [evidencia](evidence/issue-8-20261111/README.md) registra todas las muestras, revisiones y validaciones.

El resultado cubre los tres procesos de aplicación en Minikube, con SQL y observabilidad estables. La primera instalación de la política de drenaje quedó fuera de la ventana medida. R03 completo sigue condicionado por Q02 y los componentes pendientes. Las 26 pruebas Python, los tres builds y el dry-run del API server pasaron. En aquel ensayo .NET registró una falla preexistente, reproducida también en la base limpia (290/291). El resultado histórico se conserva; su corrección y las 319/319 actuales están en la actualización del 14/11.

## Incremento inicial del 6 de noviembre de 2026

Objetivo: levantar PharmaGo en Compose, verificar acceso funcional a SQL a través del gateway y registrar métricas y un log correlacionado. La referencia de planificación es el [plan maestro](aiops-master-plan.md); el código del curso reutilizado proviene del commit `dccba6748ef7698c52a20f3132c41e6753858b5d`, rama `feature/k8s`. La rama de integración del equipo es `obligatorio`; el seguimiento del trabajo restante está en [GitHub Issues](GITHUB_ISSUES.md).

El proyecto Compose aislado se llama `pharmago-baseline`. Usa la aplicación original, sus Dockerfiles y configuraciones de Prometheus, Collector y Grafana. No comparte los volúmenes de proyectos anteriores. Las mejoras iniciales son espera activa de SQL, credenciales locales aleatorias, logs JSON mediante configuración de .NET, límites de recursos, builds secuenciales y smoke verificable. El Dockerfile de Angular usa el lockfile y limita sus workers/heap.

## Inventario observado el 06/11/2026

- Windows, 12 procesadores lógicos, 7,72 GiB de RAM física. En la primera lectura solo había 0,81 GiB de RAM disponible; no se cerraron aplicaciones del usuario.
- Docker Engine 27.2.0, Compose 2.29.2; motor Linux con 3,75 GiB. Se inició Docker Desktop, sin cambiar su configuración global.
- SDK .NET 6.0.427, 8.0.411 y 10.0.203; Node 22.16.0; Python 3.11.0; kubectl 1.30.2; Minikube 1.38.1. No se inició Kubernetes.
- El baseline utiliza su propio proyecto Compose y volúmenes, sin operar sobre recursos de otras aplicaciones.
- `git fetch origin feature/k8s feature/docker-compose` completado; no se integraron commits ni se cambió de rama.

En el baseline del 06/11, la suma de límites de los ocho servicios era 3,25 GiB, sin sobrecarga del motor. El arranque se limitaba a aplicación, SQL, Collector, Prometheus y Grafana. La inspección inicial encontró referencias a archivos Logstash ausentes en el Compose heredado. Posteriormente se retiró ese servicio del Compose; la centralización validada usa Fluent Bit → Elasticsearch/Kibana en Kubernetes, según [#12](evidence/issue-12-20261112/README.md). El baseline Compose consulta logs con Docker y no acredita ese pipeline central.

## Secuencia del incremento inicial, 06/11/2026

1. A01/A04: inspección de fork, herramientas y capacidad completada; consultas académicas documentadas en `aiops-open-questions.md`.
2. A02/A03: configuración y scripts ejecutados; cuatro imágenes construidas y ocho contenedores activos. La parada y el reinicio sin seed conservaron los datos de demostración. Resultado en `BASELINE_RESULT.md` y `evidence/baseline-20261106/`.
3. A05: PASS parcial de baseline: catorce comprobaciones funcionales/telemetría aprobadas y repetidas tras parada/reinicio. Se verificaron Users y Pharmacy contra SQL, cuatro targets de Prometheus, métrica funcional y log JSON de negocio con correlation ID. Esto no cierra R04 completo.
4. A06: procedimiento mínimo en `baseline-incidents.md`; no se ejecutan ensayos de caos en este incremento.

La recomendación de aquel incremento era comprobar topología, PVs, métricas y probes/migraciones antes de avanzar a Kubernetes. Los incrementos posteriores documentan esas verificaciones; no corresponde reiniciarlas por leer este antecedente. Q01/Q02/Q03 siguen abiertos; no se declara cumplimiento académico por pruebas locales.

## Evidencia requerida

El script smoke guarda `summary.json`, targets de Prometheus y la consulta funcional. Con credencial de demostración también guarda un evento JSON correlacionado, sin token ni contraseña. Los resultados deben distinguir HTTP de frontend de una prueba real en navegador. Registrar las imágenes/digests y estado de recursos al cerrar el incremento. Las pruebas nuevas no sustituyen la suite existente ni demuestran disponibilidad bajo fallas.
