# Métricas de PharmaGo por servicio, pod y nodo

Gateway, Users y Pharmacy envían métricas por OTLP/gRPC al Collector. Cada instancia agrega atributos de Kubernetes desde la Downward API. El Collector conserva las etiquetas de servicio, instancia y UID del pod. Prometheus identifica también `namespace`, `pod`, `node` y, para almacenamiento, `container`. El intervalo de exportación de la app es de 15 segundos y el de scrape, de 5 segundos. [Exporter de Prometheus para OpenTelemetry 0.111](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.111.0/exporter/prometheusexporter/README.md)

Prometheus descubre cada destino del namespace por pod y cada kubelet por nodo. El job `pharmago-app-pods` consulta `/metrics` por pod para medir el resultado del scrape con `up`. Las muestras de aplicación de esos scrapes se descartan después del scrape. Los contadores de negocio llegan por el job `otlp-collector`. Un pedido del usuario que pasa por Gateway y Pharmacy tiene una observación en cada servicio. Para medir tráfico del cliente, filtrar `service_name="PharmaGo.ApiGateway"`. [Descubrimiento y relabeling de Prometheus 2.54.1](https://github.com/prometheus/prometheus/blob/v2.54.1/docs/configuration/configuration.md#kubernetes_sd_config)

## Consultas

| Qué se verifica | PromQL |
|---|---|
| Target individual de app | `up{job="pharmago-app-pods"}` |
| Target por nodo | `up{job=~"node-exporter\|kubernetes-cadvisor"}` |
| Muestras de app conservadas por scrape directo | `scrape_samples_post_metric_relabeling{job="pharmago-app-pods"}` devuelve 0 |
| Solicitudes OTLP por instancia | `sum by (service_name, node, pod) (rate(pharmago_http_requests_total{job="otlp-collector",namespace="pharmago",endpoint!~"/(health\|metrics)(/.*)?"}[2m]))` |
| CPU por contenedor | `sum by (node, pod, container) (rate(container_cpu_usage_seconds_total{job="kubernetes-cadvisor",namespace="pharmago",container!="",container!="POD"}[2m]))` |
| Memoria por pod | `sum by (node, pod) (container_memory_working_set_bytes{job="kubernetes-cadvisor",namespace="pharmago",container!="",container!="POD"})` |
| Almacenamiento efímero del pod | `k8s_pod_filesystem_usage_bytes{job="otlp-collector",namespace="pharmago"}` |
| Filesystem del contenedor | `container_filesystem_usage_bytes{job="otlp-collector",namespace="pharmago",container!=""}` |
| Escrituras por contenedor | `sum by (node, pod, container) (rate(container_fs_writes_bytes_total{job="kubernetes-cadvisor",namespace="pharmago",container!="",container!="POD"}[2m]))` |
| Red por pod | `sum by (node, pod) (rate(container_network_receive_bytes_total{job="kubernetes-cadvisor",namespace="pharmago",container="",pod!="",interface!="lo"}[2m]))` |
| CPU, memoria, filesystem y red del nodo | `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`, `node_filesystem_avail_bytes`, `node_network_receive_bytes_total` con `job="node-exporter"` |

La red de Kubernetes se comparte dentro del pod. cAdvisor reporta esa red a nivel del sandbox, y se agrupa por pod para evitar contar el mismo namespace de red por contenedor. El DaemonSet `kubelet-storage` consulta el Summary API de cada nodo a través del proxy autenticado del API server y solo exporta los bytes ocupados. Eso distingue ocupación de la actividad de escritura por cgroup. Los bytes efímeros no miden la ocupación de los PVC. Node Exporter expone espacio del filesystem donde están esos datos. En Minikube con driver Docker se observa `/var` porque la raíz `overlay` queda excluida por defecto. Las métricas de los tres nodos locales reflejan el entorno virtual de un solo host. [Kubelet Stats Receiver 0.111](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.111.0/receiver/kubeletstatsreceiver/README.md) · [Exclusiones de Node Exporter 1.7](https://github.com/prometheus/node_exporter/blob/v1.7.0/collector/filesystem_linux.go)

## Operación

```powershell
$ctx = '<contexto>'
kubectl --context $ctx get nodes
kubectl --context $ctx -n pharmago get pods -o wide
kubectl --context $ctx -n pharmago port-forward service/prometheus 9090:9090
# En otra terminal
kubectl --context $ctx -n pharmago port-forward service/grafana 3000:3000
```

Comparar los pods y nodos con la página local `/targets` de Prometheus. Revisar las series anteriores antes y después de reemplazar un pod. El target de scrape del pod anterior desaparece al retirarlo. Sus series OTLP pueden permanecer hasta tres minutos en el Collector y el histórico sigue consultable en Prometheus. Para una vista de instancias actuales, combinar las series OTLP con `and on(namespace, pod) (up{job="pharmago-app-pods"} == 1)`. `up` mide el scrape y se complementa con pruebas de negocio para disponibilidad.

Grafana provisiona **PharmaGo - Overview** y **PharmaGo - Infra** con los UIDs `pharmago-overview` y `pharmago-infra`. Los ConfigMaps versionan los dashboards y el datasource Prometheus. El apply cambia la anotación de contenido del pod si cambia una configuración de observabilidad montada. Esto vuelve a cargar configuraciones incluso cuando se montan con `subPath`. [Provisionamiento de Grafana](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards)
