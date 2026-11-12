# Revisión retrospectiva: bloqueo de procesos de #7

Tipo: análisis documental del 12/11/2026 sobre ensayos reales del **10/11/2026**. Se aplica ahora la estructura de registro/postmortem a evidencia ya publicada; no se afirma que estos runbooks o roles se usaran durante el ensayo original.

## Identificación, hechos e impacto

- Fuente: [informe #7](../issue-7-20261110/README.md) y [proof.json](../issue-7-20261110/proof.json), `/experiments/0`, `/experiments/1` y `/experiments/2`.
- Entorno original: `pharmago-issue3`, tres nodos Minikube en una PC; imágenes `issue7-recovery-20261110`.
- Ensayos secuenciales: `SIGSTOP` de un proceso dotnet por servicio. El pod afectado perdió Ready y liveness provocó un reinicio. Se conservó el pod SQL.
- Catálogo a través de Gateway durante su propio bloqueo: 2 respuestas válidas de 21 intentos; 19 sin respuesta HTTP. Login al bloquear un pod Users: 7/8 válidas. Catálogo al bloquear un pod Pharmacy: 18/19 válidas. Los conteos incluyen antes/durante/después, sin excluir fallos.
- Roles humanos, canal, reconocimiento, severidad declarada y comunicaciones originales: **no registrados** en esta evidencia. El alcance funcional observado correspondería a S2 según el plan actual, sin atribuir esa clasificación al equipo original. No se midió impacto de navegador ni de caída de nodo.

## Línea temporal y medición

El [JSON reconstruido](reconstruction.json) conserva los timestamps originales y el puntero de cada ensayo. El [script](reconstruct.py) calcula diferencias desde la inyección y preserva desconocidos. Por ejemplo, Gateway:

| Evento observado | UTC del 10/11/2026 | Fuente |
|---|---|---|
| Inyección registrada | 14:54:58.307949 | `/experiments/0/faultUtc` |
| Primera respuesta inválida completada | 14:55:00.517874 | Primera request inválida enviada después de faultUtc |
| Primer NotReady muestreado | 14:55:06.040211 | `/experiments/0/states` |
| Evento liveness Unhealthy/Killing | 14:55:30 | `/experiments/0/livenessEvents`; resolución de segundos |
| Ready muestreado nuevamente | 14:55:38.875357 | `/experiments/0/recovered/timeUtc` |
| Primera respuesta válida posterior a detección | 14:55:41.139853 | `/experiments/0/requests` |

El evento liveness, un reinicio y los logs de arranque sustentan la mitigación automática. La primera señal funcional se capturó 2,209925 s después de la inyección; el pod se observó Ready a los 40,567408 s. No se conoce el instante independiente de inicio de impacto ni un reconocimiento humano. La fuente no verifica la nueva ventana estable de 120 s. Por ello no se registra TTA ni TTRestore, ni se sustituye restauración por Ready.

## Diagnóstico, mitigación y aprendizaje

La falla inyectada fue el bloqueo del proceso; su efecto se contuvo parcialmente mediante las réplicas disponibles y la retirada del pod no preparado. La evidencia muestra recuperación por kubelet. No identifica la réplica que atendió cada respuesta ni demuestra eliminación de un defecto de aplicación que pudiera provocar un bloqueo real. No se declara corrección causal por haber reiniciado.

Los datos muestran que Users y Pharmacy volvieron a dar una respuesta válida antes de la recuperación del pod afectado. El runbook exige medir aparte disponibilidad del servicio y recuperación de la instancia. También advierte que exit 137 aislado no implica OOM: aquí existen eventos explícitos de liveness/Killing.

| Mejora preparada | Dónde quedó | Verificación posterior |
|---|---|---|
| Registrar actor y reconocimiento explícitos, no inferidos de scripts | Ficha y convención del plan | Roles y comunicaciones reales en #17; responsable se acuerda por corrida |
| Separar primer HTTP, pod Ready y servicio estable | Plan, ficha y runbooks | Muestreo funcional sostenido y alertas con datos en #17 |
| Fijar presupuesto, objetivo e inversa antes de inyectar | Precheck y seis runbooks | Mecanismos y limpieza verificados por escenario en #17 |
| Mantener causa desconocida y tiempos ausentes | Plantilla de postmortem y JSON histórico | Revisar postmortems sin completar datos por suposición |

No se asignan nombres o fechas de ejecución futuras sin acuerdo. Las acciones documentales ya están en esta rama; la aplicación operativa y revisión por compañero permanecen pendientes. La restauración/limpieza observada en #7 no se extiende a disco, RAM, red ni a los otros escenarios todavía no ensayados bajo este proceso.
