# Estado contrastado — 14/11/2026

Base de código: `2f125b89bf5c8c34a8748367b068bbdb8cd17975` de `obligatorio`, con el PR #42 integrado. Este resumen distingue las ejecuciones registradas del estado administrativo de las issues. Las fechas de las evidencias no se trasladan a esta revisión: no se volvieron a ejecutar Docker, Kubernetes, navegador ni caos para actualizar estos documentos.

## Implementación y evidencia disponible

| Área | Resultado registrado | Evidencia y límites |
|---|---|---|
| Kubernetes y datos | Instalación, segundo apply, parada/arranque, topología local, persistencia y restauración verificadas | [#2](evidence/issue-2-20261108/live/README.md), [#3](evidence/issue-3-20261109/README.md), [#4](evidence/issue-4-20261109/README.md) y [#5](evidence/issue-5-20261109/README.md). Nodos Kubernetes locales no equivalen a hosts físicos distintos |
| Recuperación y protección | Probes, recuperación de procesos, rate limiting y timeouts probados en sus entornos documentados | [#7](evidence/issue-7-20261110/README.md), [#9](evidence/issue-9-20261111/README.md) y [#10](evidence/issue-10-20261111/README.md). Cuotas por instancia; Gateway conserva una réplica |
| Rollout/rollback | 226/226 solicitudes válidas durante el ensayo del 11/11 | [#8](evidence/issue-8-20261111/README.md). Gateway, Users y Pharmacy; SQL y observabilidad permanecieron estables. No es una repetición sobre el código del 14/11 |
| Observabilidad | Métricas/paneles, trazas enlazadas, logs consultables y cinco alertas Firing → OK | [#6](evidence/issue-6-20261110/README.md), [#11](evidence/issue-11-20261112/README.md), [#12](evidence/issue-12-20261112/README.md), [#13](evidence/issue-13-20261112/README.md). Jaeger usa memoria; la persistencia de logs no acredita HA del stack |
| ML | IF y One-Class SVM RBF implementados, notebook ejecutado y 20 pruebas registradas | [#14](evidence/issue-14-20261112/README.md). F1 0,578313 y 0,439024 sobre la muestra de entrenamiento; aceptación del dataset pendiente Q03. El notebook docente original conserva sus TODO; la implementación está en los módulos y `algoritmos.ipynb` |
| BDD | 4/4 escenarios reales aprobados en Electron headless desde commit limpio | [#15](evidence/issue-15-20261112/live-after-fix/README.md). `browserExecuted=true`, cero omisiones. No se ejecutaron runner interactivo ni job remoto `live` |
| Incidentes y caos | Seis ensayos técnicos y una repetición de seis casos por el operador, PASS y limpieza verificada | [#17](evidence/issue-17-20261112/fix-after-review/README.md), [paquete original del operador del 13/11](evidence/issue-16-20261113/README.md) y [cierre acordado de #16](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/16). Aplicación guiada en solitario; revisión independiente opcional, no realizada. `tAck` permanece null |
| Suite .NET | 319/319 aprobadas en una nueva ejecución local del 14/11 | [Corrección de aislamiento y resumen de ejecución](evidence/test-isolation-20261114/README.md). Solo cambió la prueba en el PR #42, no la implementación de la aplicación |

Los escenarios de RAM/disco de #17/#16 retienen o escriben 32 MiB: acreditan estímulo acotado, efecto observado y limpieza, no OOM ni disco lleno. La prueba específica de la alerta de memoria está en #13. En red/desconexión se interrumpen conexiones nuevas a Pharmacy y se observa aparte la ruta existente del Gateway, que siguió disponible. Estos límites se conservan al describir el requisito de sobrecarga de la letra; no se afirma una saturación que el reporte no demuestra.

## Issues y pendientes reales

La [consulta de GitHub del 14/11](evidence/docs-review-20261114/issues.json) registra las issues del plan #2–#17 cerradas como completadas. #16 se cerró para plan y aplicación guiada local; el cierre acordado dejó la ejecución independiente por compañero como mejora opcional. El paquete del 13/11 se produjo antes de esa decisión: sus textos y manifiesto se conservan intactos y deben leerse junto con el cierre remoto.

Siguen abiertas:

- [#1](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/1): Q01, separación física; Q02, alcance del reemplazo sin interrupción; Q03, dataset/protocolo; Q04, dos/tres integrantes. El [supuesto del equipo sobre SQL](supuesto-sql.md) no constituye confirmación docente. SQL mantiene una réplica y `Recreate`.
- [#18](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/18): consolidación del informe, diagrama del entorno real, reflexión ágil, declaración de IA y paquete de entrega. Esta revisión documental no declara terminado el informe ni presentado el obligatorio.
- [#19](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/19): preparación y realización de la defensa. Los ensayos técnicos no equivalen a una defensa aprobada.
- [#20](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/20): ampliación opcional de k-sigma/MAD y cierre completo del práctico, salvo confirmación docente.

El cierre de una issue técnica no resuelve automáticamente las consultas académicas ni amplía la cobertura de su ensayo. Antes de entregar, identificar la candidata y repetir las verificaciones que correspondan a los cambios de código/configuración y al entorno elegido. Ver la [matriz por requisito](aiops-requirements-matrix.md).

## Cómo leer los antecedentes

Los incrementos del 06–12/11 describen sus fechas, equipos, commits y resultados, incluso intentos rechazados o fallidos. Las actualizaciones enlazan el resultado posterior sin reemplazar los originales. En particular, 290/291 en #8 sigue siendo el resultado histórico del 11/11; 319/319 es la ejecución del 14/11 con más pruebas y con el test corregido.

## Incremento posterior: almacenamiento sostenido

La rama `codex/storage-sustained-io` refuerza el caso de almacenamiento con escritura repetida sobre un archivo limitado y corroboración I/O del pod. El [registro del incremento](evidence/storage-io-20261114/README.md) acredita 54 pruebas de controlador, siete del agente real aislado y un ensayo completo PASS: 29 pasadas, 928 MiB lógicos, 61/61 sondas 200 válidas, recuperación estable y limpieza verificada. Tras tres arranques bloqueados por memoria se liberó caché WSL durante la preparación, antes del baseline; se mantuvieron precheck y observabilidad. La ejecución nueva registra base, árbol modificado y hashes; no sustituye los seis PASS históricos de la tabla ni demuestra saturación del dispositivo. Sigue correspondiendo justificar académicamente el alcance de “sobrecarga”.
