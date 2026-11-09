# Plan maestro de implementación — AIOps / PharmaGo (ORT 2026)

Revisión del 06/11/2026. El baseline A01–A06 ya se ejecutó con las limitaciones descritas en [el reporte](BASELINE_RESULT.md). Este documento conserva el plan completo ajustado; el estado y los responsables se siguen en [las issues](GITHUB_ISSUES.md) y la [matriz](aiops-requirements-matrix.md). Reemplaza al antiguo plan de acción. La publicación del baseline y la creación de issues, etiquetas e hitos fueron autorizadas por el usuario el 06/11/2026; otras acciones conservan sus permisos específicos.

## 0. Misión y reglas de trabajo
Sos un agente de ingeniería senior con capacidades para inspeccionar, modificar y probar código. Trabajá en MI COPIA/FORK del repositorio del curso `https://github.com/jirabedra/AIOps`, NO en el repositorio original del docente (lectura solamente). Quiero IMPLEMENTAR y VERIFICAR el obligatorio de AIOps, no reescribir la plataforma ni crear documentación ficticia. Tenés autorización para hacer cambios de código y pruebas locales no destructivas dentro del workspace, pero NO para hacer push/merge, alterar repos remotos, borrar datos o ejecutar tests de caos contra sistemas externos sin aprobación.

La solución se llama **PharmaGo** (NO Payment Service). Stack real: Angular, ASP.NET Core/.NET 6, SQL Server Express, API Gateway con YARP, Users Service, Pharmacy Service, observabilidad y Kubernetes. Conservá código y contratos existentes. No inventes resultados de ejecución ni cierres issues por tener solo archivos escritos. Al concluir cada incremento informá archivos cambiados, pruebas ejecutadas, resultados, bloqueos y el próximo incremento. Si algo no puede ejecutarse (Docker/Kubernetes/datasets ausentes), realizá análisis y tests estáticos, marcá BLOCKED y continuá con tareas independientes.

**Fecha límite académica: lunes 16/11/2026 a las 21:00 (Uruguay). Defensa obligatoria 23/11/2026.** El obligatorio vale 40 puntos. Informe máximo 10 páginas, entrega en Gestión ORT en un único ZIP/RAR de hasta 40 MB con los documentos de texto en PDF, además de todo el código versionado en GitHub. Se debe declarar uso y contexto de herramientas de IA. Hay contradicción en el enunciado respecto al tamaño de grupo (una parte 3; otra 2); documentarlo para consulta docente, no inventar respuesta.

### Fuentes, permisos y decisiones pendientes
La fuente académica principal es el enunciado docente `Obligatorio AIOps.docx`, disponible en los materiales del curso. La síntesis pública está en [la matriz](aiops-requirements-matrix.md). Distinguir sus exigencias de las recomendaciones técnicas de este plan. Registrar aclaraciones docentes con fecha y evidencia; no reemplazar un requisito por una interpretación propia. Las observaciones sobre el código son estáticas hasta que exista una prueba ejecutada.

Dentro de la implementación autorizada se permiten lecturas remotas, `git fetch` y cambios/pruebas locales no destructivos. Crear, editar o cerrar issues, etiquetas, milestones y otros objetos de GitHub también constituye escritura remota: preparar todo en Markdown y publicarlo solo con aprobación explícita. No hacer push, merge, publicación de entregas, cambios remotos ni operaciones destructivas por una instrucción genérica de este archivo. No contratar infraestructura ni asumir costos sin autorización.

| Decisión | Qué falta resolver | Evidencia para cerrarla | Impacto mientras esté pendiente |
|---|---|---|---|
| Q01 — Nodos físicos | Interpretación docente y acceso a infraestructura que permita separar los microservicios físicamente | Aclaración docente y mapa de nodos Kubernetes a hosts físicos, o prueba de separación física conforme al requisito literal | Se puede desarrollar en Minikube; el cumplimiento físico no pasa a PASS |
| Q02 — Alcance de reemplazo | Si la demostración de 100% de disponibilidad incluye DB y componentes de observabilidad, además de frontend/gateway/servicios | Alcance y escenarios confirmados por docente, vinculados a pruebas; sin respuesta se conserva el requisito completo de la letra | Se puede verificar rollout de aplicación; eso no cierra por sí solo todo el requisito |
| Q03 — Datasets | Si el notebook docente adjunto es un dataset admitido para el obligatorio o si se entregará otro | Identificación del material autorizado por docente y protocolo de evaluación | Se pueden implementar y probar IF/OCSVM con el material disponible; la aceptación académica queda pendiente |
| Q04 — Integrantes | Contradicción de hasta 3 integrantes frente a hasta 2 en el recordatorio | Aclaración docente o de coordinación | No bloquea tareas técnicas; no afirmar un límite resuelto |

Preparar estas consultas al inicio y registrar las respuestas cuando el equipo las obtenga. No enviar mensajes a terceros automáticamente. La falta de una respuesta solo bloquea el criterio afectado; continuar con trabajo independiente.

## 1. Fuente principal: cómo usar el repositorio del docente
URL: `https://github.com/jirabedra/AIOps`.
**IMPORTANTE: `main` está prácticamente vacía (README mínimo). No tomes `main` como punto de partida de aplicación.** Ramas del upstream identificadas:
- `feature/docker-compose`: aplicación completa en `Implementacion/Codigo/`, Compose + observabilidad + ELK. Contiene `QUICKSTART.md`.
- `feature/intro-k8s`: anterior + tutoriales de pods, probes, rolling updates, ConfigMaps, Blue-Green.
- `feature/k8s`: referencia principal de despliegue K8s en `Implementacion K8S/Codigo/`, manifiestos de servicios, observabilidad, Fluent Bit/ELK, scripts e instrucciones.
- `feature/k8s-no-elastic`: alternativa sin Elasticsearch; **no la uses por defecto**, porque el obligatorio requiere consulta de logs.
- `master`: prácticamente vacía.

Estado local observado el 06/11/2026: el directorio de trabajo es este fork. Su `origin` es `https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012.git`; la rama de trabajo `obligatorio` está limpia y su HEAD coincide con `origin/feature/k8s` y `origin/obligatorio` en `dccba6748ef7698c52a20f3132c41e6753858b5d`. No había un remote `upstream` configurado. Es una fotografía del estado local, no una comprobación en vivo del remoto.

Al iniciar la implementación, ejecutar `git status`, `git remote -v`, `git branch -a` y volver a comprobar ese estado desde el directorio del fork. **Reutilizar la rama `obligatorio` existente**, sin crear otra por defecto. Hacer fetch no destructivo de las referencias necesarias sin cambiar HEAD ni integrar cambios automáticamente. Solo si no existe copia/rama de trabajo, preparar una basada en `feature/k8s` y explicitar el commit reutilizado. NUNCA hacer merge ciego de todas las ramas ni sobrescribir cambios locales. Si falta una rama de curso en el fork, consultar el upstream en lectura. Los permisos de escritura remota se rigen por la sección 0.

Archivos exactos a inspeccionar prioritariamente:
- `Implementacion/Codigo/QUICKSTART.md` (rama `feature/docker-compose`)
- `Implementacion/Codigo/docker-compose.yml` (ídem)
- `Implementacion K8S/Codigo/QUICKSTART.md` (rama `feature/k8s`)
- `Implementacion K8S/Codigo/tutoriales/quickstart.md`
- `Implementacion K8S/Codigo/docker-compose.yml`
- `Implementacion K8S/Codigo/k8s/apply-k8s.sh` y `.ps1`
- `Implementacion K8S/Codigo/k8s/build-images.sh` y `.ps1`
- `Implementacion K8S/Codigo/k8s/cleanup.sh` y `.ps1` (INSPECCIONAR, no ejecutar destructivamente)
- `Implementacion K8S/Codigo/k8s/deployments/`, `services/`, `configmaps/`, `persistent-volumes/`, `secrets/`
- `Implementacion K8S/Codigo/Backend/PharmaGo.ApiGateway/Program.cs`
- `Implementacion K8S/Codigo/Backend/PharmaGo.ApiGateway/Middleware/UserRateLimitMiddleware.cs`
- `Implementacion K8S/Codigo/Backend/PharmaGo.UsersService/`
- `Implementacion K8S/Codigo/Backend/PharmaGo.PharmacyService/`
- `Implementacion K8S/Codigo/Backend/otel-collector-config.yaml`
- `Implementacion K8S/Codigo/Backend/prometheus.yml`
- `Implementacion K8S/Codigo/grafana/provisioning/`
- `Implementacion K8S/Codigo/chaos-engineering/`
- `Implementacion K8S/Codigo/Backend/PharnaGo.Test/`

**Verificado por inspección de archivos, NO por ejecución:** el quickstart Compose describe `pharmago-db`, `pharmago-users-service`, `pharmago-pharmacy-service`, `pharmago-api-gateway`, `pharmago-ui`, Prometheus, Grafana, OTel Collector y ELK. Puertos locales documentados: Angular `4200`, gateway `5000`, Users `5001`, Pharmacy `5002`, Prometheus `9090`, Grafana `3000`, Kibana `5601`, DB de Compose `11433`. Grafana debe consultar `http://prometheus:9090` en red interna Docker; en K8s resolver por DNS Service. El quickstart de K8s propone Minikube, `k8s/build-images.sh`, `k8s/apply-k8s.sh` y `k8s/port-forward.sh`. La guía Compose explica carga inicial/seed SQL; revisar `Backend/seed-data.sql` y adaptar la configuración de modo seguro.

Defectos/puntos pendientes visibles en `feature/k8s` que DEBÉS auditar y no dar como completados:
1. Deployments de API Gateway, Users y Pharmacy revisados tienen `replicas: 1`; sus nodeAffinity aceptan `node-type: [backend, all]`. `apply-k8s.sh` etiqueta el primer nodo `node-type=all`, por lo que no garantiza separación de servicios por nodos. Es necesario diseñar afinidad/anti-afinidad y probarlo; Kubernetes virtual en Minikube no equivale necesariamente a nodos **físicos** del requisito.
2. Algunos manifiestos y Compose tienen contraseñas de laboratorio en texto plano, incluso `db-secret.yaml` con `stringData` versionado. Reemplazar por mecanismos de secretos no versionados y proporcionar ejemplo seguro. Tratar credenciales publicadas como comprometidas y cambiarlas en entornos propios de prueba.
3. Varias imágenes están con etiqueta `latest` y `imagePullPolicy: Never`. Elegir tags reproducibles y un proceso de carga/despliegue comprobado, sin afectar la posibilidad de usar Minikube.
4. El `otel-collector-config.yaml` inspeccionado tiene pipeline de métricas, **no demuestra un pipeline de trazas**. Añadir instrumentación y backend consultable si faltan. Prometheus también hace scrape directo de `/metrics`; revisar el flujo efectivo y evitar dobles conteos.
5. `grafana-provisioning.yaml` contiene datasource y dashboards, pero NO comprueba cinco reglas de alerta provisionadas. Hay que implementarlas y probarlas.
6. Existen `chaos-engineering/cpu-spike.sh`, `ram-spike.sh`, `volume-spike.sh`, `load-requests.sh`. Revisar seguridad y cleanup: RAM escribe en `/dev/shm` o `/tmp`, storage escribe `/tmp/chaos_fill`, CPU lanza loops y `load-requests.sh` crea muchas solicitudes en paralelo. No ejecutarlos sin límites, verificación de namespace/destino, tiempo máximo y limpieza asegurada. Faltan evidencias de escenarios de interrupción de red y desconexión interna.
7. En Kubernetes se ve una solución de logs con Fluent Bit → Elasticsearch → Kibana (no necesariamente Logstash). Mantener ese enfoque si satisface la rúbrica; no imponer Logstash extra en K8s.
8. Ya existen módulos de instrumentación, métricas, dashboards y rate limiting (`AspNetCoreRateLimit`, modo IP/User); AUDITAR Y PROBAR antes de agregar otro sistema. `UserRateLimitMiddleware` usa caché local y encabezados como `X-User-Id`/`X-Forwarded-For`: revisar bypass, confianza en proxies, colisiones, concurrencia y comportamiento multinodo. No aceptar headers no confiables como identidad.
9. `k8s/deployments/ops/db-deployment.yaml` tiene una sola réplica SQL Server Express y estrategia `Recreate`. Reemplazar esa DB implica una ventana sin instancia disponible; el rollout sin errores de los servicios no demuestra disponibilidad durante reemplazo de DB. Revisar además las migraciones al arranque antes de aumentar réplicas. No intentar resolverlo ejecutando varias instancias SQL independientes sobre el mismo directorio ni cambiando únicamente `Recreate` por `RollingUpdate`.
10. `k8s/configmaps/prometheus-config.yaml` consulta los servicios de aplicación y `node-exporter:9100` por Service. Con varias réplicas/nodos, un único target balanceado no demuestra recolección completa de cada instancia. Diseñar descubrimiento por pod/endpoint y nodo, etiquetas estables y conteo de targets contra el inventario real. Comprobar también las métricas de estado Ready antes de elegir una alerta basada en ellas.

No afirmar que estos son los únicos problemas: buscar otros durante auditoría.

## 2. Contexto de capturas docentes (Codex NO las conoce si no se adjuntan)
Las imágenes proporcionadas por el alumno explican esta evolución:
- **DA2:** tres nodos Dockerfile: Angular frontend →HTTP→ ASP.NET Core backend →TCP/IP→ SQLExpress.
- **ISA2:** mismo stack con ASP.NET Core →gRPC/OTLP→ OpenTelemetry Collector →HTTP→ Prometheus →HTTP→ Grafana (diagrama de telemetría; verificar el flujo específico en configuración).
- **AIOps sin Kubernetes:** topología más amplia, separada en aplicación y observabilidad. Aplicación: Angular; gateway + reverse proxy YARP; User Service, Pharmacy Service y SQLExpress con sus conexiones. Se añade rama de logs con Logstash, Elasticsearch y Kibana y rama de métricas con OTel Collector, Prometheus y Grafana. Cada servicio tiene Dockerfile. Las capturas indican que primero se levanta ISA2/Compose, luego se sigue `quickstart.md`, y que la dirección de Prometheus en Grafana es `http://prometheus:9090`.
- Nota docente: el proyecto es pesado, por lo que sugiere apagar/eliminar contenedores cuando no se usen hasta estabilizar el entorno. **No borrar volúmenes ni datos persistentes automáticamente.**
- La solución final del obligatorio no se limita a Compose: debe desplegarse y validarse en Kubernetes.

## 3. Rúbrica oficial — 8 apartados de 5 puntos
1. **Plataforma:** aplicación en Kubernetes; cada microservicio en pod independiente y microservicios en nodos físicos distintos; diagrama de despliegue real. Distinguir nodos físicos vs simulados; si el requisito físico no puede verificarse en Minikube, marcarlo explícitamente y proponer prueba en hardware/infra que sí lo cumpla.
2. **Alta disponibilidad:** los servicios se curan automáticamente ante errores en ejecución (READY → falla → READY); protección frente a alto volumen de solicitudes fallidas. Demostrar efecto de limitación y/o patrones de resiliencia.
3. **Despliegues seguros:** reemplazar componentes preservando el objetivo de 100% de disponibilidad; justificar técnica (Rolling Update/Blue-Green/Canary, etc.) y medir tráfico durante un rollout. No declarar 100% sin mediciones.
4. **Telemetría:** logs JSON, trazas OTLP con propagación de contexto, métricas a nivel pod/contenedor y nodo (CPU, memoria, almacenamiento, red sugeridos), OTLP/Prometheus/Grafana, logs consultables en ELK o equivalente y **al menos cinco alertas en Grafana sobre las métricas**.
5. **Anomalías ML:** implementar Isolation Forest y Support Vector Machine con kernel RBF sobre **datasets proporcionados por docentes**. El notebook adjunto genera un dataset sintético; la letra no permite concluir por sí sola si ese material satisface la entrega o si habrá otro dataset (Q03). No inventar una exigencia de datos adicionales ni declarar el adjunto aceptado sin confirmación. Implementar IF y One-Class SVM RBF como variante no supervisada consistente con el práctico; registrar el origen y protocolo de cada dataset. Si el docente exige otro insumo, adaptar la carga y dejar pendiente solo su evaluación mientras falte.
6. **Contención de incidentes:** plan operativo de mitigación, roles, severidad, detección, respuesta, restauración, comunicación y postmortem.
7. **Caos:** scripts que prueben los SEIS eventos: solicitudes masivas, CPU, memoria, almacenamiento, interrupción de tráfico de red y desconexión de componentes internos. Cuatro tipos tienen scripts preliminares; revisar y completar.
8. **Defensa:** war-room con script docente aún desconocido; demostrar el incidente, sus efectos en telemetría, la respuesta del sistema y explicar por qué funcionaron los mecanismos. La defensa es eliminatoria.

Herramientas mencionadas por el enunciado: GitHub para repos/tablero/CI, .NET+Angular, Prometheus/Grafana/OTLP y BDD Cypress+Cucumber. No sustituir el cumplimiento de la rúbrica por una herramienta decorativa. Debe existir informe de máximo 10 páginas y reflexión sobre ingeniería ágil.

## 4. Archivo práctico adjunto por el alumno: `Markdown pegado.md`
El material adjunto se copió sin cambios a `ml/practico_detectores_aiops.ipynb` (ruta desde la raíz del fork). La copia de origen en Markdown tenía las mismas 24 celdas. Registrar el origen y los cambios del notebook al implementarlo; no duplicar versiones divergentes sin necesidad. Su especificación es:
- Dataset sintético: 300 ventanas de 1 minuto de un servicio checkout, generadas con `np.random.default_rng(42)`.
- Features: `requests`, `error_rate`, `latency_ms`, `cpu_pct`.
- `kind` e `is_anomaly` solo para EVALUACIÓN, jamás para entrenamiento.
- Clases de eventos: `normal`, `batch` y `pico_carga` (no incidentes); `spike_error`, `incidente_5xx`, `timeouts`, `latencia_silenciosa`, `combo_sutil`, `degradacion`, `cpu_latencia`, `micro_burst` (anómalas).
- Estimar parámetros sobre las 300 ventanas, incluidas ventanas contaminadas, porque así lo exige el protocolo docente (no reemplazar silenciosamente por train/test split distinto).
- Secciones 4–7: completar TODO de cuatro detectores, scores y flags.
  * k-sigma (ddof=1, k=3): `score_ksigma_error`, `score_ksigma_lat`, `flag_ksigma_error`, `flag_ksigma_lat`.
  * MAD (mediana, MAD, 1.4826*MAD, k=3): `score_mad_error`, `score_mad_lat`, `flag_mad_error`, `flag_mad_lat`; con escala 0, devolver score 0 en mediana e infinito fuera.
  * IsolationForest: `n_estimators=300`, `max_samples=min(256,len(data))`, `contamination=0.10`, `random_state=42`; fit sobre `StandardScaler().fit_transform(data[FEATURES])`; `score_if = -forest.score_samples(X_all)`; `flag_if = forest.predict(X_all) == -1`.
  * OneClassSVM: `kernel="rbf"`, `nu=0.10`, `gamma="scale"`; fit sobre X_all; `score_ocsvm = -ocsvm.decision_function(X_all)`; `flag_ocsvm = ocsvm.predict(X_all)==-1`.
- Comparación: conteo de alertas por `kind`, medianas de score, precision/recall/F1 (con `is_anomaly`), series temporales y proyecciones 2D.
- Cierre: responder 7 preguntas con evidencia sobre (1) sigma vs MAD ante spikes, (2) alertas error vs latencia, (3) combo_sutil en 1D vs 4D, (4) pico_carga vs incidente_5xx, (5) falsos positivos batch, (6) detección de degradación y limitaciones i.i.d., (7) comparación F1 entre IF y OCSVM. Exit ticket: un FP y un FN con vector x_t, explicación del detector y mejora de umbral/feature/entrenamiento.
**Aceptación académica pendiente (Q03):** este práctico es material disponible para desarrollo y evaluación local. No afirmar que reemplaza o que no puede reemplazar los datasets del obligatorio hasta contar con confirmación docente. La rúbrica exige IF y SVM RBF; k-sigma, MAD, las siete respuestas y el exit ticket quedan como ampliación del práctico, salvo que el docente también exija su entrega. Conservar el protocolo exacto descrito arriba para cualquier ejecución de este notebook; no imponerlo automáticamente a un dataset diferente.

## 5. Plan e issues reales: auditar → adaptar → verificar (no reconstruir)
Mantener `docs/AIops-implementation-plan.md`, `docs/aiops-requirements-matrix.md` y `docs/GITHUB_ISSUES.md` dentro del fork; los tres ya existen desde el baseline. La matriz debe vincular requisito literal, interpretación/decisión pendiente, prioridad, dependencias, estado REAL (EXISTING UNVERIFIED / PASS / FAIL / MISSING / BLOCKED), archivos, prueba, resultado, fecha, commit y evidencia. Un PASS requiere prueba suficiente y alcance explícito; una consulta pendiente o un archivo escrito no equivale a cumplimiento. Desglosar criterios parciales sin ocultar bloqueos del requisito completo.

Preparar issues en Markdown para **MI fork**, nunca para el docente, consultando los existentes en lectura para evitar duplicados. Publicarlos, editarlos o cerrarlos solo con aprobación explícita. Etiquetas propuestas: `priority/P0`, `priority/P1`, `priority/P2`, `infra`, `kubernetes`, `resilience`, `observability`, `ml`, `chaos`, `docs`, `bug`. Cada issue debe tener tarea concreta, dependencias, criterio de cierre y evidencia esperada. Mantener los enlaces a las issues publicadas y comprobar su estado antes de crear otras.

### Milestone A — Baseline reproducible
A01. Auditar ramas/árbol de archivos y preparar rama de trabajo sin sobrescribir nada. DoD: mapa de componentes y matriz de requisitos con referencias al código.
A02. Probar Compose sin datos destruidos; revisar DB/seed, frontend, gateway, Users/Pharmacy y endpoints. DoD: build, tráfico real, logs y resultados registrados.
A03. Revisar README/quickstart y preparar `.env.example`, scripts de inicio/parada no destructivos y smoke tests. DoD: otro integrante puede levantar y detener el entorno.
A04. Registrar Q01–Q04 e inventariar versiones, recursos disponibles de Docker/Kubernetes, RAM, CPU y disco antes de elegir topología. Usar consultas locales; no arrancar clusters para inventariar. DoD: capacidad observada, restricciones y decisiones abiertas documentadas, sin asumir recursos disponibles.
A05. Habilitar una observabilidad mínima con métricas de éxito/error/latencia y logs consultables desde el baseline; preparar captura de evidencia y reloj de incidente. Reutilizar lo existente. DoD: una operación real puede seguirse y medirse; este criterio precede a los ensayos de recuperación y rollout. No exige completar todavía todas las trazas y alertas de D.
A06. Redactar la primera versión del plan de incidentes: roles, canal, severidad, condiciones de aborto, restauración y registro temporal. DoD: procedimiento mínimo revisable antes de la primera inyección de fallas; F04 lo completa con los resultados reales.

### Milestone B — Kubernetes y disponibilidad
B01. Auditar `k8s` existente, corregir scripts/rutas/labels/namespaces/PVs/Service DNS; validación YAML y pruebas. DoD: despliegue repetible sin cambios manuales ocultos.
B02. Diseñar y probar scheduling separado (sin `node-type=all` como atajo), después de A04 y la decisión de topología de 5.1. Definir explícitamente qué servicios se separan, dónde viven sus réplicas y dónde cabe el pod adicional de rollout. DoD local: inventario de nodos/pods, reglas y distribución comprobados; DoD físico: mapa a hosts y evidencia según Q01. `kubectl get pods -o wide` por sí solo no cierra el requisito físico.
B03. Revisar probes y health endpoints de Gateway, Users, Pharmacy; quitar falsos healthy y evitar reinicios por dependencias transitorias. DoD: fallo → alerta/recuperación → Ready.
B04. Configurar réplicas, requests/límites y recuperación automática compatibles con la capacidad observada. Distinguir reinicio de proceso/pod de pérdida de nodo. DoD: ensayos controlados definidos en A06, métricas de A05 y D04 disponibles en K8s, mediciones de impacto y recuperación; no afirmar tolerancia a caída de nodo por haber borrado un pod.
B05. Implementar primero Rolling Update para componentes de aplicación sin estado, con readiness funcional, shutdown ordenado, recursos para surge y compatibilidad entre versión anterior/nueva. Usar Blue-Green solo si la auditoría justifica su costo. DoD: ensayo de tráfico funcional end-to-end antes/durante/después del rollout, rollback probado y resultados conforme a sección 6. No cerrar el requisito completo mientras Q02 o B07 estén pendientes.
B06. Quitar credenciales publicadas de las configuraciones activas, evitar exposición innecesaria y preparar secretos locales no versionados. Revisar PVs con `hostPath`: fijar su relación con el nodo que contiene los datos y documentar que no proporcionan almacenamiento compartido/failover. Probar persistencia y restauración en un entorno de prueba aislado, sin borrar datos existentes. DoD: no hay secretos nuevos versionados; datos preservados y restauración verificada. No reescribir el historial remoto para retirar credenciales como parte de esta tarea.
B07. Resolver explícitamente DB y migraciones en el alcance de disponibilidad. Auditar migraciones al arranque, concurrencia al escalar y compatibilidad de esquema durante rollout/rollback. Diseñar su ejecución controlada antes de aumentar réplicas. Si Q02 incluye reemplazo de DB, evaluar una solución compatible con la edición SQL usada y la infraestructura; registrar costo/viabilidad antes de implementarla. DoD: pruebas del alcance confirmado, sin pérdida de datos ni afirmación de 100% basada solo en servicios stateless. Sin aclaración o solución suficiente, mantener abierto el cumplimiento completo y registrar la limitación de SQL Express con una réplica/Recreate.

### Milestone C — Resiliencia de la aplicación
C01. Auditar rate limiting existente (IP vs User, bypass de headers, concurrencia, multipod) y corregirlo. DoD: pruebas de bursts, 429 y usuarios legítimos.
C02. Auditar conexiones interservicio; agregar timeouts, Circuit Breaker y reintentos seguros donde aporte, sin duplicar compras ni modificaciones de stock. DoD: prueba de dependencia caída y recuperación, conservando la corrección de las operaciones.
C03. Verificar BDD Cypress+Cucumber, herramientas mencionadas por el enunciado, e implementar un conjunto mínimo de escenarios funcionales críticos si falta. Reutilizar la aplicación y contratos actuales. DoD: escenarios ejecutables de un flujo exitoso y su error relevante, con instrucciones y resultados; no crear una suite extensa que retrase los criterios de rúbrica.

### Milestone D — Telemetría y alertas
D01. Verificar métricas de cada servicio por OTLP→Collector→Prometheus y scrape directo; revisar en particular el gateway, que en la inspección solo exporta métricas a Prometheus. Definir la fuente usada por cada consulta para evitar doble conteo. DoD: series reales identificables por servicio/instancia, flujo OTLP comprobado y consultas documentadas. Comenzar su versión mínima junto con A05, sin esperar a completar B/C.
D02. Habilitar y probar trazas OTLP entre Gateway→Users/Pharmacy→DB, backend de consulta si falta, correlación con logs. DoD: trace ID rastreable entre servicios.
D03. Verificar logs JSON con Fluent Bit/Elasticsearch/Kibana en K8s y ELK en Compose. DoD: logs consultables, sin tokens/credenciales.
D04. Verificar métricas de nodos/pods/contenedores (CPU, RAM, disk, red) y Grafana provisionado. Descubrir cada pod/endpoint y cada node-exporter de forma individual, con etiquetas de namespace, pod, servicio y nodo donde apliquen; comprobar también identificación de instancias en la vía OTLP. No usar como única evidencia un target balanceado por Service. DoD: inventario esperado frente a targets/series reales en varios nodos y réplicas, paneles persistentes, cobertura durante rollout y caída de una instancia sin series duplicadas en las consultas. Habilitar métricas mínimas de cada ensayo antes de B04/B05.
D05. Provisionar >=5 alertas Grafana reales: errores HTTP, p95, CPU, memoria y disponibilidad/estado Ready son candidatas. Para Ready comprobar primero una fuente de estado Kubernetes (p. ej., kube-state-metrics si se justifica) o elegir otra métrica verificable; `up` de scrape no equivale a Pod Ready. Calibrar umbral, ventana, duración, no-data y errores de consulta. DoD: para cada regla, PromQL y origen identificados, Firing y retorno a OK registrados con hora y escenario. Validar la regla de forma acotada antes de aumentar carga para los ensayos de caos.

### Milestone E — Machine Learning
E01. Inventariar datasets/materiales docentes disponibles, su procedencia, features, etiquetas y protocolo. Resolver Q03 sin suponer que los datos deben ser reales o distintos del sintético adjunto. DoD técnico: carga/preprocesamiento reproducibles para los datos disponibles, sin fuga de etiquetas; DoD académico: insumo autorizado identificado. Si se exige otro archivo ausente, dejar pendiente esa evaluación y continuar con IF/OCSVM sobre el material disponible, identificado como tal.
E02. Implementar Isolation Forest y guardar scores/predicciones con semilla. DoD: script o notebook reproducible y tests.
E03. Implementar One-Class SVM RBF con escalado y parámetros. DoD: resultado reproducible.
E04. Comparar IF/OCSVM sobre el dataset autorizado y respetar su protocolo. Usar precision/recall/F1 y FP/FN solo si hay etiquetas; si no las hay, documentar scores, alertas y limitaciones sin inventar verdad de referencia. DoD: tablas, gráficos, versiones/parámetros y conclusiones reproducibles; aceptación pendiente mientras Q03 no esté resuelto.
E05. Ampliación: completar k-sigma/MAD, comparación de cuatro detectores, preguntas y exit ticket del cuaderno adjunto, conservando su protocolo exacto. IF/OCSVM del mismo cuaderno pueden reutilizarse en E02–E04 si Q03 lo admite, sin duplicar implementaciones. DoD de la ampliación: todas las celdas corren, seis flags, preguntas y exit ticket. No tratar esta ampliación como obligación de la rúbrica salvo confirmación docente.

### Milestone F — Ingeniería del caos e incidentes
F01. Auditar y hacer seguros los 4 scripts existentes: timeout, límites, cleanup automático, `trap`, prechecks y autorización local. DoD: ensayos reversibles que registran sus efectos.
F02. Implementar script de interrupción controlada de red. DoD: repro/rollback sin afectar máquinas externas.
F03. Implementar script de desconexión de componente interno. DoD: fallo observable, recuperación y evidencia.
F04. Completar el plan iniciado en A06 con severidades, roles, comunicación, runbooks, restauración y postmortem. Para MTTD/MTTA/MTTRestore registrar los eventos de inicio y fin usados, unidades y fuente temporal; no mezclar convenciones ni promediar un solo ensayo como si fuera una muestra de incidentes. DoD: procedimientos aplicados y corregidos con evidencia de los escenarios; plan usable antes del simulacro F05.
F05. Ejecutar simulacro war-room con seis fallas, telemetría, alertas y recuperación. DoD: informe por escenario con hipótesis, mediciones, conclusión.

### Milestone G — Entrega y defensa
G01. Preparar diagrama de despliegue ACTUAL, README y guía de troubleshooting. DoD: reproduce arquitectura verificada.
G02. Preparar informe académico <=10 páginas con una sección por cada una de las 8 áreas de rúbrica, desafíos/resultados, limitaciones abiertas y declaración de uso/contexto de IA. Incorporar la reflexión de G06 dentro del límite total. DoD: referencias y pruebas reales, no afirmaciones inventadas; iniciar el borrador con la primera evidencia, sin esperar al final.
G03. Reproducir instalación y demo sobre entorno limpio; generar evidencias vinculadas a la matriz. DoD: test integral con estado y bloqueos.
G04. Preparar paquete ZIP/RAR <=40MB, PDFs y checklist de Gestión (NO subir sin autorización). DoD: archivo verificado y ruta documentada.
G05. Preparar plan de defensa del 23/11: roles de war-room, script docente desconocido, checklist de recuperación, simulacro. DoD: guía para que cualquiera pueda explicar causas y acciones.
G06. Registrar y redactar una reflexión sobre el impacto de prácticas de ingeniería ágil: incrementos pequeños, pruebas, trazabilidad de requisitos, coordinación y decisiones apoyadas por evidencia. DoD: ejemplos concretos del trabajo efectivamente realizado, con beneficios y límites; no inventar prácticas, ceremonias o resultados.

### 5.1 Topología y condiciones para avanzar
Durante A04/B01, elegir y registrar dos alcances: entorno local de desarrollo y entorno de demostración académica. Minikube multinodo en una sola computadora permite probar scheduling; no demuestra separación de hosts físicos. No adoptar por defecto el reparto frontend/backend/ops del script, porque concentra los microservicios en el mismo nodo backend.

El diseño debe especificar nodos elegibles para Users, Pharmacy y Gateway, si este último se incluye en la separación, réplicas por servicio, ubicación de frontend/DB/observabilidad, límites y margen de CPU/RAM/disco para despliegues. La interpretación provisional más conservadora separa también el Gateway; una aclaración docente puede precisar el alcance. Las reglas deben separar servicios distintos sin impedir innecesariamente que convivan la versión vieja y la nueva del mismo servicio durante el rollout. Si además se exige separación física entre réplicas, calcular los nodos adicionales necesarios. Comprobar scheduling de todos los pods y del surge antes de la prueba de disponibilidad; una preferencia de anti-afinidad no garantiza separación obligatoria.

Para datos con `hostPath`, documentar el nodo propietario y la recuperación admitida. Ni agregar nodos ni agregar réplicas de aplicación vuelve altamente disponible al SQL Server actual. Una eventual solución de almacenamiento compartido o HA de DB exige diseño y pruebas propios. Si no hay recursos para el requisito físico, demostrar lo local y mantener visible el bloqueo académico.

La issue #3 concreta esta sección en [Topología Kubernetes de PharmaGo](aiops-k8s-topology.md), con el diagrama, el presupuesto y el mapa de nodos a hosts.

Dependencias mínimas:
- A01/A04 y consultas Q01–Q04 preceden a decisiones de infraestructura; A02/A03 producen el baseline reproducible.
- A05/A06 preceden a inyecciones de fallas. En K8s, B01/B02/B03 y las métricas mínimas D01/D04 necesarias para el ensayo preceden a B04/B05; B07 precede a escalar servicios que migran la DB.
- D02/D03/D05 y F01–F04 pueden avanzar por incrementos. F05 requiere procedimientos, límites, restauración y telemetría que permitan observar los seis escenarios.
- E01–E04 son una línea independiente del despliegue; pueden trabajarse alternadamente sin esperar a terminar infraestructura. E05 depende de la prioridad y confirmación de alcance.
- G01/G02/G06 se actualizan con cada evidencia; G03/G04 requieren resultados consolidados y bloqueos explicitados.

### 5.2 Prioridades y calendario de referencia
El calendario se organiza por hitos, sin asignar integrantes ni horas. Las fechas son objetivos provisionales, no una garantía de capacidad. Revisar el avance al cerrar cada incremento; si un hito se retrasa, recortar ampliaciones y visibilizar el riesgo sin omitir requisitos evaluables.

P0: resolver incertidumbres que condicionan el cumplimiento, baseline, seguridad de scripts/PVs, topología, instrumentación mínima y plan inicial de incidentes. P1: completar y verificar los ocho apartados de la rúbrica, BDD mínimo, documentación y entrega. P2: ampliación E05 y mejoras adicionales que no sean necesarias para aprobar un criterio. No añadir migraciones de framework, nuevas plataformas ni herramientas duplicadas sin necesidad comprobada.

| Fechas objetivo (Uruguay, 2026) | Resultado esperado | Evidencia o condición de salida |
|---|---|---|
| 06–07/11 | A01–A06, consultas preparadas, baseline y propuesta de topología/DB | Matriz inicial, smoke funcional medido, inventario y decisiones abiertas; no afirmar aprobación docente |
| 08–10/11 | K8s reproducible, separación local, probes/recuperación/rollout y persistencia; completar métricas mínimas | B01–B07 según alcance, C01/C02 y D01/D04 con pruebas; bloqueos físicos/DB explícitos si siguen abiertos |
| 08–12/11, línea independiente | E01–E04, conjunto mínimo BDD y borrador de informe | IF/OCSVM reproducibles, Q03 documentada, escenarios funcionales y evidencias incorporadas |
| 11–13/11 | Trazas/logs, cinco alertas y seis escenarios de caos con plan operativo | D02/D03/D05, F01–F05: efectos, límites, restauración y resultados por escenario |
| 14–15/11 | Reproducción, informe final, diagrama y paquete candidato | G01–G04/G06: <=10 páginas, ZIP/RAR <=40 MB, PDFs y revisión de trazabilidad; publicación remota solo autorizada |
| 16/11, antes de las 18:00 como margen interno | Paquete final revisado y listo para la entrega del equipo | Verificar contenido/ruta; el límite oficial sigue siendo 21:00. No subir automáticamente |
| 17–22/11 | Ensayo de defensa y repaso de evidencias/procedimientos | G05, roles y simulacro; conservar identificada la versión entregada y cualquier diferencia posterior |
| 23/11 | Defensa obligatoria | Preparación para war-room y explicación individual del comportamiento observado |

Si Q01/Q02/Q03 siguen sin respuesta, no esperar para trabajar sobre lo verificable ni rebajar la rúbrica: registrar exactamente qué resultado está probado y qué aceptación sigue pendiente. Priorizar consultas y viabilidad de DB/nodos al principio, porque pueden requerir una decisión docente o infraestructura externa.

## 6. Procedimiento técnico de validación
Desde la ruta CORRECTA (con espacios entrecomillados) y sin borrar volúmenes:
```
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs --tail=100
```
Smoke test: Angular → API Gateway YARP → Users/Pharmacy → SQL Server; probar operación, HTTP y datos persistidos; validar seed SQL si corresponde. No asumir que Running = funcional. Primero Compose estable según las capturas.

Para K8s, según entorno, revisar antes `minikube status`, `kubectl config current-context`, capacidad del host y autorizaciones; construir imágenes según scripts y desplegar. Recolectar:
```
kubectl get nodes -o wide
kubectl get pods -n pharmago -o wide
kubectl get deployments -n pharmago
kubectl get events -n pharmago --sort-by=.lastTimestamp
kubectl rollout status deployment/pharmago-api-gateway -n pharmago
```
Registrar número de pods Ready, nodos asignados, errores y tiempos de recuperación. Para cada ensayo guardar commit/tag de imagen, manifiestos/configuración sin secretos, versiones, contexto/namespace, recursos, inicio/fin, comandos y resultado. Conservar consultas y logs junto con el reporte; una captura de Running/Ready aislada no demuestra una operación funcional.

Para rollout, usar un flujo funcional que atraviese gateway, servicio y DB, no solo `/health`; validar también frontend cuando esté en el alcance. Definir carga acotada, duración/cadencia, timeout, resultados esperados y condición de aborto antes de ejecutar. Medir antes, durante y después, incluyendo solicitudes en vuelo: total enviado, éxitos, errores HTTP, timeouts, fallos de validación y latencia, con marcas temporales. En un ensayo de rollout bajo carga normal, no descontar 429 ni errores para mejorar el porcentaje. En un ensayo específico de rate limiting, clasificar 429 esperados por separado y medir el éxito de tráfico legítimo.

El criterio de la prueba de despliegue es cero fallos inesperados en operaciones funcionales durante la ventana definida y rollback verificable. Reportar “100% observado en N solicitudes durante T, bajo estas condiciones”; no extrapolar a una garantía universal ni a componentes que no se reemplazaron. Si se estima downtime, declarar la resolución de muestreo y límites de la medición. Registrar cobertura por componente y mantener abierto lo no demostrado según Q02/B07.

Para alertas, guardar regla, consulta, umbral, ventana y transición Firing → OK, comprobando su fuente real por pod/nodo. Para caos, ejecutar un escenario a la vez con límites de duración/carga, verificación de destino/namespace, limpieza acotada y recuperación confirmada antes del siguiente. Establecer condiciones de aborto basadas en recursos del host y evitar que un fallo local afecte otros trabajos. Validar primero en seco o estáticamente los scripts; la prueba real debe respetar el procedimiento de A06/F04.

Verificar que rollback/cleanup es seguro: **NUNCA ejecutar `docker compose down -v`, `kubectl delete namespace`, scripts de `cleanup` u operaciones destructivas sin autorización**. No saturar recursos de la máquina anfitriona. No lanzar carga a URL pública/external.

## 7. Inicio de implementación y reporte
**Estado: baseline implementado y verificado; trabajo restante abierto en GitHub.** Para retomar el trabajo: A) verificar estado local y reutilizar `obligatorio` basada en `feature/k8s`; B) preparar matriz e issues en Markdown; C) trabajar primero A01/A04, consultas y baseline instrumentado A02/A05/A06; D) seguir dependencias y prioridades, produciendo incrementos pequeños con código y pruebas reales. Ninguna instrucción de este archivo autoriza por sí sola escrituras remotas o la presentación de la entrega.

Al cerrar cada incremento, informar archivos cambiados, pruebas/comandos ejecutados, resultados y evidencias, decisiones pendientes, bloqueos y siguiente incremento concreto. Distinguir DONE verificado, FAIL con logs, BLOCKED con causa y EXISTING UNVERIFIED; no cerrar el requisito completo por completar una subtarea. Preferir el mínimo cambio reproducible que cumpla la letra. No prometer continuar en segundo plano ni en otra sesión; dejar un estado reanudable.

## 8. Referencias de esta revisión
- Fuente académica: enunciado `Obligatorio AIOps.docx` y capturas en los materiales del curso; práctico adjunto copiado a `ml/practico_detectores_aiops.ipynb`. El enunciado y las capturas originales no se incluyen en esta publicación.
- Código inspeccionado en el fork local, commit `dccba6748ef7698c52a20f3132c41e6753858b5d`: manifiestos de backend y DB, scripts de apply/build, configuración de Collector/Prometheus y arranque/instrumentación de servicios. Inspección estática; no equivale a ejecución.
- Kubernetes, estrategias de Deployment y parámetros de rollout: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
- Kubernetes, afinidad/anti-afinidad: https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/
- Minikube multinodo y limitación del provisionador host-path predeterminado (distinto de los PV estáticos propios): https://minikube.sigs.k8s.io/docs/tutorials/multi_node/
