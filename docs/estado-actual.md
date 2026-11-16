# Estado contrastado del proyecto

Base documental: `04f3edd0935bf9fc845900d0329fd79a6110523f` de `obligatorio`, con las evidencias del despliegue en tres PCs y el informe académico. Los ensayos en tres PCs registran código `ae24ebe`, árbol limpio e imágenes `k8s-20261116-01`; cada ensayo anterior conserva su propio commit. Este resumen distingue los resultados técnicos del estado administrativo capturado de las issues. No se volvieron a ejecutar Docker, Kubernetes, navegador ni caos para actualizar estos documentos.

## Implementación y evidencia disponible

| Área | Resultado registrado | Evidencia y límites |
|---|---|---|
| Kubernetes y datos | Gateway, Users y Pharmacy en tres PCs físicas con k3s/Tailscale; instalación, persistencia y restauración probadas previamente en Minikube | [Topología física, diagrama, nodos y pods](evidence/chaos-3pc-20261116/README.md). Antecedentes locales: [#2](evidence/issue-2-20261108/live/README.md), [#3](evidence/issue-3-20261109/README.md), [#4](evidence/issue-4-20261109/README.md) y [#5](evidence/issue-5-20261109/README.md). PC A concentra Gateway, SQL, observabilidad y servidor k3s; no se acredita tolerancia a la pérdida de esa PC |
| Recuperación y protección | Probes, recuperación de procesos, rate limiting y timeouts probados en sus entornos documentados | [#7](evidence/issue-7-20261110/README.md), [#9](evidence/issue-9-20261111/README.md) y [#10](evidence/issue-10-20261111/README.md). Cuotas por instancia; Gateway conserva una réplica |
| Rollout/rollback | 226/226 solicitudes válidas durante el ensayo local del 11/11 | [#8](evidence/issue-8-20261111/README.md). Gateway, Users y Pharmacy; SQL y observabilidad permanecieron estables. No se repitió ese ensayo de recambio entre las tres PCs |
| Observabilidad | Métricas/paneles, trazas enlazadas, logs consultables y cinco alertas Firing → OK probados localmente; stack desplegado también en tres PCs | [#6](evidence/issue-6-20261110/README.md), [#11](evidence/issue-11-20261112/README.md), [#12](evidence/issue-12-20261112/README.md), [#13](evidence/issue-13-20261112/README.md) y [distribución física](evidence/chaos-3pc-20261116/README.md). No se declara repetida toda la validación de telemetría entre PCs. Jaeger usa memoria; la persistencia de logs no acredita HA del stack |
| ML | IF y One-Class SVM RBF implementados, notebook ejecutado y 20 pruebas registradas | [#14](evidence/issue-14-20261112/README.md). F1 0,578313 y 0,439024 sobre la muestra de entrenamiento; dataset y protocolo adoptados por el equipo en D03. El notebook docente original conserva sus TODO; la implementación está en los módulos y `algoritmos.ipynb` |
| BDD | 4/4 escenarios reales aprobados en Electron headless desde commit limpio | [#15](evidence/issue-15-20261112/live-after-fix/README.md). `browserExecuted=true`, cero omisiones. No se ejecutaron runner interactivo ni job remoto `live` |
| Incidentes y caos | Seis categorías PASS en tres PCs; un intento de red FAIL conservado, con limpieza verificada en las siete corridas | [Reportes, journals y resumen en tres PCs](evidence/chaos-3pc-20261116/README.md). Antecedentes: [#17](evidence/issue-17-20261112/fix-after-review/README.md), [paquete local del operador](evidence/issue-16-20261113/README.md) y [cierre acordado de #16](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/16). La revisión independiente del plan de incidentes sigue sin acreditarse; el despliegue compartido no equivale a esa revisión. `tAck` permanece null |
| Suite .NET | 319/319 aprobadas en una nueva ejecución local del 14/11 | [Corrección de aislamiento y resumen de ejecución](evidence/test-isolation-20261114/README.md). Solo cambió la prueba en el PR #42, no la implementación de la aplicación |

Los escenarios originales de RAM/disco de #17/#16 retienen o escriben 32 MiB. El caso de almacenamiento se reforzó con escrituras repetidas y telemetría I/O; en tres PCs registró 26 pasadas sincronizadas observadas sobre un archivo de 32 MiB y `deviceSaturation=null`. Se acredita estímulo acotado, efecto observado y limpieza, no OOM, disco lleno ni saturación general. La prueba específica de la alerta de memoria está en #13. En red/desconexión se interrumpen conexiones nuevas directas a Pharmacy y se observa aparte la ruta del Gateway, que respondió 200 en las sondas durante los cortes. Estos resultados no garantizan disponibilidad fuera de la ventana muestreada.

## Despliegue y caos en tres PCs físicas

Cada integrante aportó una PC: `pharmago-a` ejecutó Gateway, SQL y la mayor parte de observabilidad; `pharmago-b`, Users con dos réplicas, UI y Kibana; `pharmago-c`, Pharmacy con dos réplicas y los clientes de caos. Los tres nodos usaron k3s en Ubuntu/WSL2, conectados mediante Tailscale. La [evidencia](evidence/chaos-3pc-20261116/README.md) contiene el diagrama y los inventarios de nodos/pods. El intento inicial con Hamachi y su migración se conservan como antecedentes de preparación; los scripts no forman una instalación completa desde cero.

El [resumen de corridas](evidence/chaos-3pc-20261116/summary.json) registra requests (111 HTTP 200 y 129 HTTP 429), CPU (130 s de carga), RAM (32 MiB), storage (26 pasadas sincronizadas observadas), red y desconexión interna. Las seis categorías terminaron PASS; el primer intento de red terminó FAIL al perderse la evaluación sana de las alertas durante la estabilidad posterior a la restauración. Las siete corridas verificaron la limpieza. El relato atribuye el fallo a Tailscale/Wi-Fi, pero el log citado no está versionado: la causa no queda acreditada con ese archivo publicado. Se conserva tanto el FAIL como la repetición PASS.

Esta ejecución acredita la distribución documentada entre equipos y los efectos de caos observados. No repite las 226 solicitudes de rollout/rollback ni todas las pruebas de recuperación, persistencia o cinco alertas de los laboratorios anteriores. PC A y su enlace son un punto único de falla; dos réplicas en la misma PC no toleran la pérdida del host.

## Issues y pendientes reales

La [consulta de GitHub del 14/11](evidence/docs-review-20261114/issues.json) registra las issues del plan #2–#17 cerradas como completadas. #16 se cerró para plan y aplicación guiada local; el cierre acordado dejó la ejecución independiente por compañero como mejora opcional. El paquete del 13/11 se produjo antes de esa decisión: sus textos y manifiesto se conservan intactos y deben leerse junto con el cierre remoto.

La captura de GitHub registra los siguientes temas; el alcance actual se actualiza aquí:

- [#1](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/1): las [decisiones D01–D04](aiops-open-questions.md) registran el alcance anterior: laboratorio local, recambio de Gateway/Users/Pharmacy, dataset docente y tres integrantes. La evidencia física amplía D01 para despliegue y caos; no extiende automáticamente las demás pruebas. La captura remota conserva el título/estado anteriores; esta edición no modifica las issues. SQL mantiene una réplica y `Recreate`.
- [#18](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/18): existe un [informe académico de diez páginas](entrega/README.md), con diagramas, reflexión ágil y declaración de IA. Su contenido debe mantenerse alineado con la matriz y las evidencias. Falta confirmar el paquete final y la presentación efectiva; esta revisión no declara entregado el obligatorio.
- [#19](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/19): preparación y realización de la defensa. Los ensayos técnicos no equivalen a una defensa aprobada.
- [#20](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/20): ampliación opcional de k-sigma/MAD y cierre completo del práctico, por decisión D03.

Las decisiones D01–D04 se leen junto con la evidencia física incorporada; el cierre de una issue técnica conserva la cobertura real de su ensayo. Antes de entregar, identificar la candidata y repetir las verificaciones que correspondan a los cambios de código/configuración y al entorno elegido. Ver la [matriz por requisito](aiops-requirements-matrix.md).

## Cómo leer los antecedentes

Los incrementos del 06–12/11 describen sus fechas, equipos, commits y resultados, incluso intentos rechazados o fallidos. Las actualizaciones enlazan el resultado posterior sin reemplazar los originales. En particular, 290/291 en #8 sigue siendo el resultado histórico del 11/11; 319/319 es la ejecución del 14/11 con más pruebas y con el test corregido.

## Incremento posterior: almacenamiento sostenido

La rama `codex/storage-sustained-io` refuerza el caso de almacenamiento con escritura repetida sobre un archivo limitado y corroboración I/O del pod. El [registro del incremento](evidence/storage-io-20261114/README.md) acredita 54 pruebas de controlador, siete del agente real aislado y un ensayo completo PASS: 29 pasadas, 928 MiB lógicos, 61/61 sondas 200 válidas, recuperación estable y limpieza verificada. Tras tres arranques bloqueados por memoria se liberó caché WSL durante la preparación, antes del baseline; se mantuvieron precheck y observabilidad. La ejecución nueva registra base, árbol modificado y hashes; no sustituye los seis PASS históricos de la tabla ni demuestra saturación del dispositivo. Sigue correspondiendo justificar académicamente el alcance de “sobrecarga”.
