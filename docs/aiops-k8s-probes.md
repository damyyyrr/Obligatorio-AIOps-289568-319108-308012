# Salud y recuperación de microservicios en Kubernetes

La issue #7 separa la respuesta del proceso de su capacidad de atender operaciones. Kubernetes deja de enviar tráfico a un pod que pierde readiness. Si falla liveness de forma sostenida, el kubelet reinicia su contenedor. [Probes de Kubernetes](https://v1-34.docs.kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/) · [Health checks de ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks?view=aspnetcore-6.0)

| Probe | Endpoint | Intervalo | Timeout | Fallos consecutivos |
|---|---|---:|---:|---:|
| Startup | `/health/live` | 2 s | 2 s | 60 |
| Readiness | `/health/ready` | 5 s | 4 s | 1 |
| Liveness | `/health/live` | 10 s | 2 s | 3 |

Startup habilita los otros dos probes cuando el servidor HTTP empieza a responder. Liveness verifica que ese servidor siga respondiendo aunque falle una dependencia. El reinicio provocado por liveness tiene cinco segundos de gracia. `/health` sigue disponible como alias de readiness. Las tres rutas de salud del Gateway quedan fuera del rate limiting para que los probes no consuman la cuota de las rutas de negocio.

| Servicio | Readiness | Réplicas |
|---|---|---:|
| Users | Consulta de solo lectura a `dbo.Users` con timeout de 2 s | 2 |
| Pharmacy | Consulta de solo lectura a `dbo.Drugs` con timeout de 2 s | 2 |
| Gateway | Consulta `/health/ready` de Users y Pharmacy por los destinos de YARP, en paralelo y con timeout HTTP de 2 s por destino | 1 |

Gateway responde `200 Healthy` si ambos servicios están listos, `200 Degraded` si solo uno está listo y `503 Unhealthy` si ninguno lo está. Así Kubernetes mantiene el acceso al backend que sigue disponible. Users y Pharmacy vuelven a sus respectivos Services cuando recuperan acceso a SQL. Las migraciones se ejecutan con el Job previo al despliegue. [Migraciones](aiops-sql-migrations.md)

Cada pod pide `100m` de CPU y `128Mi` de memoria, con límites de `500m` y `384Mi`. Con dos réplicas más un pod de surge, Users o Pharmacy requieren hasta `300m / 384Mi` en requests para sus pods durante el recambio. Las dos réplicas de un mismo backend comparten el único nodo elegible de ese servicio en la topología de tres nodos. La pérdida de ese nodo interrumpe el servicio. Gateway queda en una réplica mientras la #9 evalúa el limitador por réplica. La #8 mide continuidad durante rollout y rollback. [Topología y capacidad](aiops-k8s-topology.md)

## Repetir la comprobación

Usar un clúster descartable o el perfil local de pruebas con la app y Prometheus desplegados. Registrar el pod elegido, UID, contenedor, nodo y hora UTC antes de inyectar una falla.

```powershell
$context = 'pharmago-issue3'
$app = 'pharmago-users-service' # Cambiar por Gateway o Pharmacy en el siguiente ensayo
kubectl --context $context -n pharmago get pods -o wide
$pod = kubectl --context $context -n pharmago get pods -l "app=$app" -o jsonpath='{.items[0].metadata.name}'
$podUid = kubectl --context $context -n pharmago get pod $pod -o jsonpath='{.metadata.uid}'
kubectl --context $context -n pharmago get pod $pod -w
# En otras terminales
kubectl --context $context -n pharmago get events --field-selector "involvedObject.uid=$podUid"
kubectl --context $context -n pharmago logs $pod --tail=45
kubectl --context $context -n pharmago port-forward service/prometheus 9090:9090
```

En Prometheus, seguir `up{job="pharmago-app-pods",pod="<pod elegido>"}` y el contador de solicitudes de la ruta con `sum by (service_name, status_code) (pharmago_http_requests_total{job="otlp-collector",namespace="pharmago",endpoint="/api/drug"})`. Cambiar el endpoint a `/api/login` para Users. En paralelo, enviar solicitudes a Gateway desde dentro del clúster con un timeout acotado y verificar el resultado de negocio. Usar un usuario de prueba para login y registrar solo códigos, tiempos y si la respuesta fue válida.

Para probar un proceso colgado, identificar el PID del contenedor con `crictl inspect <container-id>` en su nodo Minikube. Verificar UID, nombre y namespace del pod, y que `/proc/<pid>/comm` sea `dotnet`, antes de ejecutar `docker exec <nodo> sh -c "kill -STOP <pid>"`. Si se interrumpe el ensayo y el mismo contenedor sigue siendo dueño de ese PID, reanudarlo con `kill -CONT`. Esperar `Ready → NotReady → Ready`, un restart y un evento de kubelet que atribuya el reinicio a liveness. Confirmar que una nueva operación real vuelve a responder y guardar la cronología.

Para comprobar readiness ante una dependencia, crear pods aislados con etiquetas propias y Services SQL temporales sin endpoints. Usar Secrets temporales con la conexión de prueba apuntando a esos Services. Verificar por port-forward directo `200` en liveness y `503` en readiness. Restaurar los endpoints de cada Service de prueba por separado y comprobar que el pod recupera Ready con el mismo UID y sin reinicios. Usar un Gateway de prueba que apunte a esos backends aislados para observar también su estado degradado. Eliminar los pods, Services y Secrets temporales al terminar.
