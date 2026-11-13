# Plan de operación e incidentes de PharmaGo

Revisión del 12/11/2026, issue #16 (OPS-01, R06). Aplica al laboratorio Kubernetes del equipo, namespace `pharmago`, y al baseline Compose `pharmago-baseline`. Identificar un único entorno por intervención; no mezclar comandos de ambos. No operar infraestructura externa ni recursos de otros proyectos.

Actualización del 13/11/2026: [seis ensayos guiados ejecutados por el operador](evidence/issue-16-20261113/README.md), con reportes PASS, bitácora, capturas y parada conservando datos. La revisión se realizó en solitario y conserva las horas reales de anotación; no demuestra revisión independiente, comunicaciones a terceros ni reconocimiento humano durante cada falla.

El plan prepara los seis incidentes de #17. La revisión y la reconstrucción de evidencia histórica están en [la evidencia de #16](evidence/issue-16-20261112/README.md). **La validación integral de R06 se completa con los ensayos de #17.** Los scripts heredados de caos no quedan habilitados ni validados por este documento.

## Servicios críticos y limitaciones

| Capacidad | Dependencias y validación |
|---|---|
| Catálogo | Gateway → Pharmacy → SQL; `GET /api/drug` devuelve 200 y el contenido esperado |
| Roles y login | Gateway → Users → SQL; `GET /api/roles` y login válido con usuario de prueba existente |
| Interfaz | Angular → Gateway; comprobar también el flujo visible en navegador |
| Detección y diagnóstico | App → OTLP Collector → Prometheus/Grafana; trazas a Jaeger; Fluent Bit → Elasticsearch/Kibana |
| Datos | SQL Express y su PVC; [propietario, respaldo y restauración](aiops-k8s-recovery.md) |

Gateway tiene una réplica; Users y Pharmacy, dos cada uno, en el único nodo elegible de su servicio. La caída de ese nodo afecta ambas réplicas. SQL tiene una réplica y `Recreate`; su reinicio interrumpe operaciones dependientes. Cambiar etiquetas de nodos no traslada discos. Jaeger guarda trazas en memoria y las pierde al reiniciar. Ver [topología](aiops-k8s-topology.md), [probes](aiops-k8s-probes.md), [rollout](aiops-k8s-rollout.md) y [timeouts](aiops-interservice-resilience.md).

## Roles, canal y escalamiento

Completar nombres y suplencias en [la ficha](templates/incidente.md) antes del ensayo. No deducir responsables de autores de commits.

| Rol | Responsabilidad |
|---|---|
| Coordinación / Incident Commander | Confirma impacto y severidad, decide cambios, aborto, escalamiento y cierre |
| Respuesta técnica | Diagnostica y ejecuta una acción reversible por vez sobre el destino aprobado |
| Observación y bitácora | Vigila host, tráfico, recursos y alertas; registra horas/evidencia y confirma recuperación |
| Enlace con interesados | Comunica al equipo; escala al propietario del host/datos y al docente si cambia el alcance académico |

Una persona puede asumir varios roles si registra esa limitación. Si trabaja sola, detener la inyección para diagnosticar; no mantener carga sin vigilancia. En S1, detener el daño tiene prioridad sobre reunir evidencia.

Acordar un único canal de voz/chat y una bitácora local canónica; registrar su ubicación. No se presupone Slack/Teams ni una guardia permanente. Las [comunicaciones de ejemplo](templates/incidente.md) son borradores para revisión y envío manual; no se envían mensajes automáticamente.

| Severidad | Condición observable | Acción y comunicación |
|---|---|---|
| S1 crítica | Riesgo para datos/otros proyectos/host; MemoryPressure/DiskPressure; OOM o reinicios repetidos fuera del objetivo | Abortar inmediatamente y avisar al equipo y propietario del host/datos. Actualizar tras abortar y ante cada cambio material |
| S2 alta | Login o catálogo fallan o presentan latencia incompatible con el objetivo del ensayo; host estable | Detener estímulo, abrir incidente y aplicar runbook. Comunicar al confirmar y cada 2 min o cambio material |
| S3 observabilidad | Operaciones válidas pero faltan métricas, logs, trazas o evaluación de alertas | Suspender nuevas inyecciones, comunicar alcance ciego y restaurar observación; actualizar cada 5 min |

Un 429 esperado en una prueba de cuota no constituye por sí solo caída: registrar también el tráfico legítimo afectado. Si ese tráfico falla, elevar severidad. Las cadencias son objetivos del laboratorio, no un SLA medido. Si S2 no mejora en 5 min desde detección, convocar al segundo respondedor o propietario. Si falla la reversión o el destino es dudoso, detener acciones y escalar. La falta de otra persona no autoriza ampliar el impacto.

## Preparar

1. Abrir ficha con ID, tipo (real, ensayo o retrospectiva), commit/diff, imágenes/digests, roles y canal.
2. Identificar contexto, namespace, nodos, pod/UID/contenedor y destino. Registrar réplicas, revisiones y UIDs de PV/PVC. Usar siempre `--context` y namespace; no cambiar el contexto global para reparar.
3. Guardar baseline: catálogo, roles y login válidos; contenido esperado sin secretos; nodos sin presión, espacio libre, pods y targets. Si ya falla, registrar ese incidente y no inyectar otro.
4. Comprobar dashboards, evaluación de alertas y consulta de logs/trazas. Acordar límites y presupuesto libre de CPU/RAM/disco en host y nodos; una cuota de pod no garantiza capacidad del host.
5. Para #17, registrar hipótesis, mecanismo revisado, duración máxima, PID/job/regla/archivo de inyección, inversa exacta y condición de aborto. Mantener un terminal de recuperación independiente del port-forward afectado.
6. Un ensayo a la vez, sin rollouts/migraciones simultáneos. Sin reversión identificada y sin presupuesto de recursos, no iniciar.

Desde la raíz del repositorio, en PowerShell, completar valores verificados:

```powershell
$ctx = '<contexto-validado>'
$ns = 'pharmago'
git rev-parse HEAD
git status --short
kubectl --context $ctx cluster-info
kubectl --context $ctx get nodes -o wide
kubectl --context $ctx -n $ns get deploy,pods,svc,endpointslices,pvc -o wide
kubectl --context $ctx get pv sql-pv elasticsearch-pv prometheus-pv grafana-pv
$runDir = '.runtime/incidents/<id-unico>'
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
kubectl --context $ctx -n $ns get deploy,pods,pvc -o json |
    Set-Content -Encoding utf8 -LiteralPath "$runDir/before.json"
```

Comprobar `$LASTEXITCODE` después de cada comando nativo; no continuar ante error ni publicar una captura vacía. Si el API server no responde, no cambiar a otro contexto: verificar perfil y estabilidad del host. No capturar Secrets ni dumps completos de configuración.

## Detectar y diagnosticar

Registrar primera señal observada, fuente y hora; no esperar Firing para reconocer un fallo funcional. Contrastar impacto externo, Kubernetes y telemetría. `up=1`, Running, Ready o una alerta en OK aislados no demuestran servicio funcional. Gateway puede seguir Ready/Degraded con ambos backends caídos.

```powershell
$app = 'pharmago-pharmacy-service' # Elegir el servicio realmente afectado
kubectl --context $ctx -n $ns get pod -l "app=$app" -o wide
$pod = '<nombre-exacto-observado>'
kubectl --context $ctx -n $ns describe pod $pod
kubectl --context $ctx -n $ns get events --sort-by=.lastTimestamp
kubectl --context $ctx -n $ns get endpointslices -l "kubernetes.io/service-name=$app"
kubectl --context $ctx -n $ns logs $pod --since=5m --tail=100
# Solo si hubo reinicio y existe un contenedor previo:
kubectl --context $ctx -n $ns logs $pod --previous --tail=100
```

Logs y `describe` pueden exponer datos sensibles: revisar localmente y publicar solo fragmentos sanitizados. Nunca guardar contraseñas, `.env`, Secrets, cadenas de conexión, Authorization ni cuerpos/tokens de login. Registrar también evidencia perdida por un reinicio.

Para acceso local, usar terminales dedicadas y `kubectl --context $ctx -n $ns port-forward --address 127.0.0.1 service/<servicio> <puertos>`. Pares: Prometheus `9090:9090`, Grafana `3000:3000`, Kibana `5601:5601`, Jaeger `16686:16686`, Gateway `5000:80`, UI `4200:80`. Un port-forward se ata a un pod: reconectarlo al cambiar ese pod y contrastar con acceso por Service dentro del clúster antes de culpar a la aplicación.

| UID de alerta Grafana | Condición y permanencia | Runbook inicial |
|---|---|---|
| `pharmago-http-5xx` | >5% en 1 min, tráfico >0,1 req/s, `for: 30s` | RB-01 o RB-06 |
| `pharmago-http-p95` | >1000 ms en 1 min, mismo mínimo de tráfico, `for: 30s` | RB-02, RB-05 o RB-06 |
| `pharmago-pod-cpu` | >80% del límite, tasa de 1 min, `for: 1m` | RB-02 |
| `pharmago-pod-memory` | >85% del límite, `for: 1m` | RB-03 |
| `pharmago-pod-not-ready` | Running sin Ready, `for: 45s` | RB-05/RB-06 o recursos |

Fuente: [reglas versionadas](../Implementacion%20K8S/Codigo/k8s/configmaps/grafana-alerting.yaml), evaluadas cada 10 s. Sin tráfico, 5xx/p95 pasan a OK; CPU/memoria sin datos pasan a NoData y Ready sin datos a Alerting; error de consulta es Error. NoData/Error no significan recuperación. OTLP exporta cada 15 s, Prometheus scrapea cada 5 s; ventanas y evaluación añaden demora. No obtener TTD sumando intervalos teóricos.

Usar [consultas de métricas](aiops-k8s-metrics.md) para CPU/RAM/bytes efímeros/filesystem/red. En Kibana filtrar `kubernetes.namespace_name:"pharmago"`, pod e intervalo; buscar correlation ID o trace ID en los campos realmente indexados, por ejemplo `Scopes.correlation_id`/`Scopes.TraceId`. Si no existen, inspeccionar un evento y su mapping. Abrir el mismo trace ID en Jaeger y comparar Gateway → servicio → SQL.

## Responder, recuperar y validar

1. Coordinación registra reconocimiento, impacto, severidad y runbook. Congelar cambios y detener el estímulo identificado antes de reiniciar servicios. Seguir [los seis runbooks](runbooks/incidentes.md).
2. Capturar diagnóstico mínimo sin demorar aborto. Separar hechos de hipótesis y ejecutar una acción reversible por vez. Si cambió UID/PID, reidentificar antes de actuar.
3. Recuperar primero la dependencia afectada. SQL lenta no justifica reiniciar todos los consumidores. No repetir compras/escrituras de resultado incierto: no hay claves de idempotencia ni reintentos automáticos seguros para ellas.
4. Si coincide con un release, seguir [rollback](aiops-k8s-rollout.md) con revisión guardada y esquema compatible. No ejecutar Down, seed ni apply integral como reparación a ciegas.
5. Validar por el camino del usuario: catálogo/roles con contenido esperado; login con usuario existente, token no vacío y usuario correcto sin guardar respuesta; UI si corresponde. Registrar todos los códigos, latencias e intentos, incluidos 429, errores y timeouts.
6. Criterio de restauración por defecto del laboratorio, acordado antes del ensayo: catálogo y roles cada 5 s durante **120 s**, login al inicio y final, cero errores funcionales, réplicas/Endpoints esperados, sin nuevos reinicios/presión, estímulo retirado y datos comprobados. Es una política, no un resultado obtenido. Un error reinicia la ventana. No superponer generadores ni exceder cuotas.
7. Fijar `t_restore` en el comienzo de esa ventana solo después de verificarla completa; registrar `t_verified` al terminar. Separar Ready y primera respuesta válida. Esperar vuelta de alertas a OK con datos frescos antes de reanudar caos. Si sigue ceguera, el servicio puede estar mitigado pero queda S3 abierto.
8. Comparar réplicas, revisiones, PV/PVC, datos y recursos temporales con el inventario. Terminar el generador no acredita limpieza. Comunicar recuperación o escalamiento si falla la reversión.

## Aborto y parada de emergencia

Abortar ante S1, destino/contexto ambiguo, pérdida de observabilidad durante inyección, duración excedida o limpieza fallida. Detener únicamente PID/job/recurso del ensayo. Con API accesible, aplicar la inversa exacta; no vaciar reglas de red ni matar procesos por patrones generales.

Si persiste riesgo para el host, coordinación puede detener **el entorno dedicado verificado**, conservando discos. Compose: desde `Implementacion K8S/Codigo`, `./scripts/stop-baseline.ps1`. Minikube propio: `minikube stop -p <perfil-verificado>` tras comparar sus nodos con `$ctx`. En clúster compartido no apagar el clúster: detener solo la carga identificada y escalar al propietario. `cleanup.ps1` escala todos los Deployments del namespace y deja DaemonSets activos; no usarlo para una falla de un servicio ni confundirlo con apagar el host. No ejecutar `down -v`, prune, `minikube delete` ni borrar namespace/PV/PVC.

## Bitácora y convención de tiempos

Fuente académica: `AIOps__Clase_1.pdf`, páginas 33–35 y 42–45, y `AIOps__Clase_5.pdf`, ciclo de incidentes y postmortem, en materiales del curso. Registrar ISO 8601 UTC (`Z`/`+00:00`); Uruguay es UTC-03:00. PowerShell: `[DateTimeOffset]::UtcNow.ToString('o')`. Anotar fuente, precisión, muestreo y diferencias de reloj. No mezclar segundos relativos con timestamps sin anclar su origen.

| Evento | Definición |
|---|---|
| `t_start` | Inicio observado del fallo/impacto. Conservar además `t_inject`; si se usa como origen, explicitarlo sin afirmar primer impacto medido |
| `t_detect` | Primera señal de falla capturada: respuesta inválida, condición, alerta o reporte; identificar detector y evidencia |
| `t_ack` | Reconocimiento explícito de coordinación; ni el reinicio automático ni el inicio de un script son reconocimiento humano |
| `t_repair` | Corrección causal conocida. Un reinicio puede mitigar sin eliminar el defecto; en tal caso reparación causal pendiente |
| `t_restore` / `t_verified` | Inicio de la ventana estable / confirmación al completarla, según criterio acordado |
| `t_alert_firing` / `t_alert_ok` | Transiciones de alerta separadas de detección/restauración funcional |

Por incidente: **TTD = t_detect − t_start; TTA = t_ack − t_start; TTRestore = t_restore − t_start**. El curso mide TTA desde el inicio del fallo. Si se calcula reconocimiento-detección, llamarlo `ack_delay = t_ack − t_detect`, sin sustituir TTA. TRepair solo con corrección causal identificada. En causas múltiples registrar cada reparación; no equiparar automáticamente reparación, mitigación y restauración.

Dato ausente = `no registrado`/`null`, nunca cero ni una hora deducida. Sin origen conocido, esos intervalos quedan indeterminados. Una serie muestreada da observaciones con esa resolución, no instantes exactos. Reservar MTTD/MTTA/MTTRestore para promedios de incidentes comparables, con N, población y convención explícitos.

## Aprender y cierre

Completar [postmortem sin culpas](templates/postmortem.md): impacto, cronología, evidencia, causas sustentadas, mitigación frente a corrección y acciones con responsable y criterio verificable. Mantener causas desconocidas como hipótesis; conservar intentos fallidos y corregir runbooks/matriz.

La [ficha y mensajes](templates/incidente.md) cubren apertura, actualización, aborto, recuperación y handoff. Para cerrar #16/R06, adjuntar fichas de los seis ensayos de #17 con roles reales, procedimientos aplicados, tiempos observables, limpieza y revisión por otro integrante cuando esté disponible. Los campos desconocidos conservan su motivo. Hasta entonces: **preparación terminada; validación integral pendiente**. Una reconstrucción histórica no prueba la aplicación contemporánea del proceso.
