# Implementación de AIOps

## Incremento del 12 de noviembre de 2026 — issue #14

Se implementan y ejecutan Isolation Forest y One-Class SVM RBF sobre las 300 ventanas sintéticas del notebook docente, preservando el original y su protocolo: StandardScaler y ambos modelos se ajustan sobre toda la muestra, sin etiquetas ni selección de parámetros con ellas. La [guía ML](../ml/README.md) enlaza CLI, notebook ejecutado y dependencias fijadas. Los [resultados](evidence/issue-14-20261112/results/RESULTS.md) incluyen scores/flags por ventana, métricas, todos los FP/FN, tablas por tipo, gráficos y parámetros/versiones/hashes.

Pasaron 20 pruebas y dos ejecuciones CLI produjeron salidas numéricas idénticas; el notebook terminó sus siete celdas de código. F1 observado: IF 0,578313 y OCSVM 0,439024, evaluados sobre la misma muestra de entrenamiento, sin afirmar generalización. La [evidencia](evidence/issue-14-20261112/README.md) conserva alcance y procedencia. R05 tiene validación técnica del material disponible; Q03 y la aceptación académica permanecen pendientes. La ampliación del práctico sigue en #20. No se inició infraestructura.

## Incremento del 12 de noviembre de 2026 — issue #17

Se reemplazan los cuatro scripts heredados por wrappers de un controlador con simulación sin infraestructura, contexto local explícito, límites de carga, prechecks de capacidad/observabilidad, identidad de recursos, journal y watchdog. Se agregan corte de tráfico con NetworkPolicy y desconexión del Service Pharmacy. La [guía](../Implementacion%20K8S/Codigo/chaos-engineering/README.md) describe preparación, ejecución individual, aborto y recuperación, y las [evidencias](evidence/issue-17-20261112/README.md) distinguen regresiones/simulación de ensayos reales.

La revisión posterior corrigió aborto/arranque tardío, transporte LF desde Windows y medición por destino/conexión. Pasaron 45 + 5 + 26 tests del controlador, agente aislado y configuración, también en CI Linux. Después del primer precheck rechazado por memoria, el usuario liberó margen y se completaron **seis ensayos reales PASS** en un laboratorio nuevo con Calico: efectos observados, 120 s estables, limpieza independiente y PV/PVC/configuración conservados. Durante las pruebas se corrigió un HTTP 500 de Grafana/SQLite activando WAL, sin ocultar errores. Red y Service se verifican sobre conexiones nuevas, con la continuidad del Gateway existente registrada aparte. [Fichas, fuentes, intentos fallidos y evidencia](evidence/issue-17-20261112/fix-after-review/README.md). #17 queda lista para revisión/integración técnica local; #16/R06 conserva la revisión humana de roles/comunicaciones y tAck no registrado.

## Incremento del 12 de noviembre de 2026 — issue #16

Se amplía el [plan de incidentes](baseline-incidents.md) a Kubernetes y Compose con roles, severidades, canal, escalamiento y aborto, criterios funcionales de restauración y convención de tiempos del curso. Los [seis runbooks](runbooks/incidentes.md) cubren requests, CPU, RAM, disco, red y desconexión interna. Hay plantillas de [ficha/bitácora y comunicaciones](templates/incidente.md) y [postmortem](templates/postmortem.md).

La [evidencia de #16](evidence/issue-16-20261112/README.md) distingue revisión de procedimientos y reconstrucción reproducible de tres ensayos históricos de #7 frente a ejecución nueva. No se inyectaron fallas, enviaron mensajes ni operaron contenedores. Reconocimiento humano, corrección causal y restauración con ventana estable no registrados quedan indeterminados. La preparación permite comenzar #17; el cierre de #16/R06 requiere su aplicación integral con esos ensayos.

## Incremento del 11 de noviembre de 2026 — issue #8

Gateway, Users y Pharmacy incorporan drenaje antes de SIGTERM, timeout de apagado y permanencia mínima en Ready. El ensayo local de actualización y rollback registró 226/226 respuestas funcionalmente válidas en 282,139 s. Se observaron versiones coexistentes, se restauraron las tres plantillas y se conservaron el esquema, los registros comprobados y los volúmenes. La [guía](aiops-k8s-rollout.md) incluye el generador reproducible y la [evidencia](evidence/issue-8-20261111/README.md) registra todas las muestras, revisiones y validaciones.

El resultado cubre los tres procesos de aplicación en Minikube, con SQL y observabilidad estables. La primera instalación de la política de drenaje quedó fuera de la ventana medida. R03 completo sigue condicionado por Q02 y los componentes pendientes. Las 26 pruebas Python, los tres builds y el dry-run del API server pasaron. .NET registra una falla preexistente, reproducida también en la base limpia (290/291).

## Incremento inicial del 6 de noviembre de 2026

Objetivo: levantar PharmaGo en Compose, verificar acceso funcional a SQL a través del gateway y registrar métricas y un log correlacionado. La referencia de planificación es el [plan maestro](aiops-master-plan.md); el código del curso reutilizado proviene del commit `dccba6748ef7698c52a20f3132c41e6753858b5d`, rama `feature/k8s`. La rama de integración del equipo es `obligatorio`; el seguimiento del trabajo restante está en [GitHub Issues](GITHUB_ISSUES.md).

El proyecto Compose aislado se llama `pharmago-baseline`. Usa la aplicación original, sus Dockerfiles y configuraciones de Prometheus, Collector y Grafana. No comparte los volúmenes de proyectos anteriores. Las mejoras iniciales son espera activa de SQL, credenciales locales aleatorias, logs JSON mediante configuración de .NET, límites de recursos, builds secuenciales y smoke verificable. El Dockerfile de Angular usa el lockfile y limita sus workers/heap.

## Inventario observado

- Windows, 12 procesadores lógicos, 7,72 GiB de RAM física. En la primera lectura solo había 0,81 GiB de RAM disponible; no se cerraron aplicaciones del usuario.
- Docker Engine 27.2.0, Compose 2.29.2; motor Linux con 3,75 GiB. Se inició Docker Desktop, sin cambiar su configuración global.
- SDK .NET 6.0.427, 8.0.411 y 10.0.203; Node 22.16.0; Python 3.11.0; kubectl 1.30.2; Minikube 1.38.1. No se inició Kubernetes.
- El baseline utiliza su propio proyecto Compose y volúmenes, sin operar sobre recursos de otras aplicaciones.
- `git fetch origin feature/k8s feature/docker-compose` completado; no se integraron commits ni se cambió de rama.

La suma de límites de los ocho servicios es 3,25 GiB; no incluye sobrecarga del motor. El arranque se limita a aplicación, SQL, Collector, Prometheus y Grafana. ELK requiere otro incremento: el Compose original referencia `logstash/logstash.conf` y `.yml`, ausentes en `feature/k8s` pero presentes en `origin/feature/docker-compose`. El baseline consulta logs con Docker; no demuestra todavía el requisito completo de logs/telemetría en Kubernetes.

## Secuencia y estado

1. A01/A04: inspección de fork, herramientas y capacidad completada; consultas académicas documentadas en `aiops-open-questions.md`.
2. A02/A03: configuración y scripts ejecutados; cuatro imágenes construidas y ocho contenedores activos. La parada y el reinicio sin seed conservaron los datos de demostración. Resultado en `BASELINE_RESULT.md` y `evidence/baseline-20261106/`.
3. A05: PASS parcial de baseline: catorce comprobaciones funcionales/telemetría aprobadas y repetidas tras parada/reinicio. Se verificaron Users y Pharmacy contra SQL, cuatro targets de Prometheus, métrica funcional y log JSON de negocio con correlation ID. Esto no cierra R04 completo.
4. A06: procedimiento mínimo en `baseline-incidents.md`; no se ejecutan ensayos de caos en este incremento.

No avanzar a Kubernetes por tener servicios Running. El siguiente incremento debe resolver topología y scripts/PVs, habilitar las métricas de infraestructura necesarias y revisar probes/migraciones antes de escalar. Q01/Q02/Q03 siguen abiertos; no se declara cumplimiento académico por pruebas locales.

## Evidencia requerida

El script smoke guarda `summary.json`, targets de Prometheus y la consulta funcional. Con credencial de demostración también guarda un evento JSON correlacionado, sin token ni contraseña. Los resultados deben distinguir HTTP de frontend de una prueba real en navegador. Registrar las imágenes/digests y estado de recursos al cerrar el incremento. Las pruebas nuevas no sustituyen la suite existente ni demuestran disponibilidad bajo fallas.
