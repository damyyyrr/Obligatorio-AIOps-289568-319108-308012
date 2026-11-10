# Issue #6 — métricas y targets por instancia

Ensayo del 10/11/2026 en `feature/issue-6-metricas-por-instancia` desde `c6b1e15` de `obligatorio`. Se reutilizó el perfil de prueba de tres nodos Kubernetes. Minikube 1.39.0, Kubernetes y kubectl 1.34.1, containerd 2.3.4, Prometheus 2.54.1, Collector 0.111.0, Node Exporter 1.7.0 y Grafana 10.4.2. Los tres nodos locales corresponden a una sola PC.

| Prueba | Resultado |
|---|---|
| Comparación con inventario Kubernetes | 10 targets `up`. Tres pods de aplicación, tres Node Exporters, tres kubelets para cAdvisor y un Collector central. |
| Contadores OTLP | Tres consultas de catálogo dieron un incremento de 3 en Gateway y 3 en Pharmacy. Un login dio un incremento de 1 en Gateway y 1 en Users. Las solicitudes devolvieron HTTP 200. Cada scrape directo conservó 0 muestras de aplicación. |
| CPU, memoria, almacenamiento y red | Se verificaron las etiquetas de los tres pods de aplicación y sus contenedores, y de los tres nodos. El Summary API aportó ocupación efímera por pod y contenedor, y cAdvisor aportó I/O por contenedor y red por pod. |
| Reemplazo de un pod | Prometheus detectó los dos targets de Users durante el solapamiento, retiró el anterior y recibió una serie OTLP identificada con el pod nuevo. |
| Dashboards después de reaplicar | Grafana volvió a provisionar `pharmago-overview` con 6 paneles y `pharmago-infra` con 12. Se consultaron las 18 expresiones contra Prometheus. Cambió el UID del pod de Grafana y se conservó el del PVC. Prometheus mantuvo su pod porque su configuración era idéntica. |

[proof.json](proof.json) contiene el inventario, los targets antes y después, las consultas con cobertura comprobada, los incrementos, los pods observados y el resultado de provisionamiento. Las pruebas de la #6 cubren métricas locales. La continuidad de solicitudes durante el rollout se mide en la #8.

## Reproducción

Se construyó la imagen de Gateway con el tag `issue6-metrics-20261110` y se reutilizaron las otras tres imágenes de la #5 con el mismo tag, ya que sus binarios no cambiaron. Se cargó el Collector de almacenamiento en los nodos elegibles. La [guía de despliegue](../../../Implementacion%20K8S/Codigo/k8s/README-k8s.md) describe la construcción completa para un perfil nuevo.

```powershell
$ctx = 'pharmago-issue3'
$k8s = 'Implementacion K8S/Codigo/k8s'
$py = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
& $py -m unittest discover -s $k8s
& $py "$k8s/manage.py" apply --context $ctx --image-tag issue6-metrics-20261110 --secrets-file .runtime/issue4-upgrade-secrets.local.json
kubectl --context $ctx get nodes
kubectl --context $ctx -n pharmago get pods -o wide
kubectl --context $ctx -n pharmago rollout restart deployment/pharmago-users-service
kubectl --context $ctx -n pharmago rollout status deployment/pharmago-users-service
```

Se comparó `/api/v1/targets?state=active` con los pods y nodos, y se usó `/api/v1/query` para ejecutar las consultas de la [guía de métricas](../../aiops-k8s-metrics.md). Con port-forward al Gateway se enviaron tres `GET /api/drug` y un `POST /api/login` con un usuario de demo. El conteo usó `pharmago_http_requests_total` con `job="otlp-collector"`, `namespace="pharmago"`, el endpoint, el método y `status_code="200"`, agrupado por servicio.

Para comprobar el provisionamiento, se consultó `/api/dashboards/uid/<uid>` en Grafana con una credencial local. Se escaló a cero su Deployment en el perfil de ensayo y se ejecutó otra vez el mismo apply. Se repitió la consulta y se comparó el UID de `grafana-pvc`. Los paneles de estado HTTP pueden quedar sin muestras cuando no se produjo ese código.

Pasaron 23 pruebas de regresión, el build de Gateway, `promtool check config` para las dos configuraciones de Prometheus y `docker compose config --quiet` para los dos archivos Compose.
