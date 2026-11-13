# Issue #13 — cinco alertas Grafana con experimentos reales

**PASS local: 5/5 reglas con estado inicial OK, Firing durante un experimento acotado y retorno a OK tras restaurar.** Ejecución del 12/11/2026 en Uruguay (13/11 UTC). Base `1eaef3426ef8f208b260de5d8078d1b6ad558c83`, Kubernetes 1.34.1/containerd en el perfil exclusivo `pharmago-issue17-validation`. No se modificó código, umbrales ni configuración del repositorio.

## Reglas efectivas

Las consultas PromQL completas y condiciones están en `rules-definition.json`. `rules-provisioning.json` es la respuesta real del API de Grafana; las cinco reglas tienen `provenance=file`. `rules-check.json` compara UID, consulta, umbral, duración, rango, políticas de datos/error y estado pausado con el archivo del repositorio: 5/5 iguales. `provenance.json` confirma también la igualdad de la ConfigMap desplegada. Las reglas sobrevivieron al arranque del perfil conservado y no se cargaron reglas de prueba.

| UID | Fuente y consulta resumida | Umbral | Ventana / for | NoData / error |
| --- | --- | --- | --- | --- |
| pharmago-http-5xx | OTLP `pharmago_http_requests_total`; porcentaje 5xx por service_name, excluye /health y exige >0,1 req/s | >5% | rate 1m / 30s | OK / Error |
| pharmago-http-p95 | OTLP `pharmago_http_request_duration_milliseconds_bucket`; histogram_quantile(0.95), mismo filtro y tráfico mínimo | >1000 ms | rate 1m / 30s | OK / Error |
| pharmago-pod-cpu | cAdvisor: rate(container_cpu_usage_seconds_total) / (quota/period), cgroup del pod `container=""` | >80% del límite | rate 1m / 1m | NoData / Error |
| pharmago-pod-memory | cAdvisor: container_memory_working_set_bytes / container_spec_memory_limit_bytes, cgroup del pod | >85% del límite | instantánea / 1m | NoData / Error |
| pharmago-pod-not-ready | kube-state-metrics: kube_pod_status_ready{condition="false"} × kube_pod_status_phase{phase="Running"} | >0 | instantánea / 45s | Alerting / Error |

Evaluación cada 10 s. El API configura `relativeTimeRange.from=600` para las consultas instantáneas; esto no convierte el `rate[1m]` en una ventana de diez minutos. No se provocaron errores de datasource ni NoData; sus políticas se verificaron en la configuración efectiva.

## Transiciones individuales observadas

Todas las horas siguientes son UTC del **13/11/2026**, equivalentes al 12/11 por la noche en Uruguay. Son horas de observación, con sondeo cada 5 s más costo de kubectl/API, no el instante exacto de evaluación.

| Regla | Primer Firing del ensayo | Primer OK tras restaurar | Resultado |
| --- | --- | --- | --- |
| pharmago-http-5xx | 02:00:28.627456 | 02:02:08.904273 | PASS |
| pharmago-http-p95 | 02:08:26.084130 | 02:10:36.182711 | PASS |
| pharmago-pod-cpu | 01:57:08.469306 | 01:57:50.019639 | PASS |
| pharmago-pod-memory | 02:13:19.866442 | 02:14:42.259577 | PASS |
| pharmago-pod-not-ready | 02:04:47.588411 | 02:05:22.851821 | PASS |

`alert-verdicts.json` contiene los timestamps completos, el estado previo, inyección/restauración, consulta y umbral por regla. El veredicto requiere Firing y OK dentro de la ventana de su propio ensayo. `transitions.json` y `alerts-sanitized.jsonl.gz` conservan las transiciones y todas las muestras sanitizadas, incluidas las del arranque y otros efectos; esos eventos ajenos no se usan como sustituto del ensayo individual.

## Escenarios y efectos

- **CPU:** dos bucles de shell, con `timeout 135`, en una réplica Pharmacy con límite de 500m. Grafana registró la instancia del pod en Alerting con resumen de uso de 100% del límite; terminó la carga y volvió a inactive/ok.
- **Errores:** tráfico de aproximadamente 1 req/s y Pharmacy temporalmente escalada de dos réplicas a cero durante 105 s; restauración a dos. `errors-traffic.json`: 260 respuestas, 161 HTTP 200 y 99 HTTP 502. Se conserva el 502 observado, aunque el script original describa 503. La regla mide 5xx y volvió a OK con tráfico sano.
- **Ready:** pausa de la tarea SQL durante 80 s, con reanudación en finally y watchdog independiente de 180 s. Cuatro pods Users/Pharmacy permanecieron Running con Ready=False; al mismo tiempo `up{job="kube-state-metrics"}=1`. `ready-during.json` y `ready-after.json` prueban condición real, fuente sana y recuperación. SQL no necesitó reiniciar durante el ensayo. La request fallida y sus tres spans HTTP 500 están en [#11](../issue-11-20261112/README.md).
- **Latencia:** pausas de 1,5 s y reanudaciones de 1 s de ambas tareas Pharmacy, durante unos 115 s, con watchdog y restauración final. `latency-during.json`: p95 estimado por el histograma del Gateway de 2211,54 ms frente a umbral 1000 ms; pods Ready en la muestra. `latency-traffic.json`: 257 respuestas, todas HTTP 200. El p95 de Prometheus es una estimación por buckets, no una duración máxima medida por el cliente.
- **Memoria:** `dd` retuvo un bloque en un pipe hasta terminar un `sleep 135`, dimensionado al 92% del límite cgroup de la réplica Pharmacy. `memory-before.json`, `memory-during.json`, `memory-after.json` registran la consulta efectiva; durante el ensayo alcanzó 92,01355% frente al umbral 85%. Al finalizar se liberó la memoria y volvió a OK. El proceso tuvo duración fija y no se cambiaron límites.

El primer control de recursos bloqueó la carga de memoria por disponer de 1,38 GB libres en Windows, menos que el margen de 2 GiB. Tras liberar aplicaciones, el control pasó con 2.439.888.896 bytes disponibles. `memory-precheck.json` conserva ambas mediciones y el ensayo vuelve a verificar el margen antes de inyectar.

## Comandos y trazabilidad

Se usaron kubectl con contexto explícito y APIs internas, sin port-forwards públicos. Los scripts existentes `scripts/probe-alerts.py` y `scripts/alert-scenarios.py` guiaron la captura y las cargas. CPU/memoria usan los mismos mecanismos; la pausa de tareas se adaptó operativamente a **containerd/Minikube**, porque las variantes `docker pause` del script solo sirven para Docker Desktop. No se editó ese script.

Comandos representativos exactos, desde `Implementacion K8S/Codigo/`, para la variante existente de CPU/memoria:

```sh
python scripts/alert-scenarios.py --context pharmago-issue17-validation --hold 135 --recover 100 cpu
python scripts/alert-scenarios.py --context pharmago-issue17-validation --hold 135 --recover 100 memory
```

La ejecución registrada utilizó un envoltorio temporal para guardar JSON y enviar stdin como bytes UTF-8 (evita traducción CRLF de Windows). El diario `faults.jsonl` incluye tareas/pods capturados, duración, restauración y final de cada ensayo. La carga HTTP fue GET `http://pharmago-api-gateway/api/drug` con un máximo aproximado de una petición por segundo, timeout 20 s, contando todas las respuestas y excepciones.

Para las pausas se obtuvieron IDs de `status.containerStatuses[].containerID` de los pods seleccionados, se comprobó que fueran hashes hexadecimales de 64 caracteres y se ejecutó dentro del nodo:

```sh
sudo ctr -n k8s.io tasks pause ID_CAPTURADO
sudo ctr -n k8s.io tasks resume ID_CAPTURADO
```

El watchdog se lanzó antes de pausar, con `nohup sh -c 'sleep 180; sudo ctr -n k8s.io tasks resume ID_CAPTURADO ...'`, stdin/stdout/stderr redirigidos, exclusivamente sobre los IDs capturados. El bucle principal hizo pause/sleep 1.5/resume/sleep 1 para latencia o pause/sleep 80/resume para SQL. En ambos casos se reanudaron las tareas en finally, aunque fallara el control. Para repetir, obtener IDs actuales y conservar las mismas garantías de reanudación; los IDs históricos no identifican futuros contenedores.

El escalado de errores usó `kubectl --context pharmago-issue17-validation -n pharmago scale deploy/pharmago-pharmacy-service --replicas=0` y restauró el valor capturado `--replicas=2`, seguido de `rollout status --timeout=180s`.

## Limpieza, límites y artefactos

`safety-check.json` compara specs/UIDs de PV, PVC, Deployments y Services, datos/UIDs de ConfigMaps y estado Ready contra el inicio. `cleanup.json` registra la comprobación final de tareas, eliminación del cliente de validación por su identidad y parada del laboratorio conservando datos. Los cambios de pod esperados por el ensayo de escalado y el reemplazo de Elasticsearch se distinguen de cambios de configuración.

Minikube terminó su parada y se comprobó Host=Stopped antes de apagar Docker Desktop. La CLI de apagado de Desktop agotó 180 s; la comprobación posterior confirmó API no disponible, pipe del motor Linux ausente, ningún proceso vmmemWSL, contexto Kubernetes nuevamente sin seleccionar y configuración del perfil conservada. Windows recuperó unos 10,6 GiB libres. El timeout del comando de cierre queda registrado en `cleanup.json`; no afectó las cinco validaciones previas.

Esta evidencia valida reglas en un laboratorio local de un nodo, con recursos e imágenes identificados en `provenance.json`; no demuestra alta disponibilidad, retención de trazas, separación física, canales de notificación ni reconocimiento humano de incidentes. La issue #16 mantiene su validación humana independiente.

Los artefactos no contienen contraseñas ni tokens. Las muestras de alertas se publican como proyección sanitizada (estado, salud, labels permitidos, valor y resumen controlado de regla), comprimida con gzip; no se presenta como el JSON original íntegro. `manifest.json` contiene SHA-256 de los archivos públicos. Ver también [trazas #11](../issue-11-20261112/README.md) y [logs #12](../issue-12-20261112/README.md).
