# Issue #7 — recuperación de Gateway, Users y Pharmacy

Ensayo del 10/11/2026 en `feature/issue-7-recuperacion-microservicios`, desde `d4c050b` de `obligatorio`. Se reutilizó el perfil local `pharmago-issue3`, con tres nodos Kubernetes en una sola PC. Minikube 1.39.0, Kubernetes 1.34.1, containerd 2.3.4 y Prometheus 2.54.1. Las imágenes de Gateway, Users y Pharmacy se construyeron con el tag `issue7-recovery-20261110`. UI se reutilizó con el mismo tag porque su binario no cambió.

## Dependencias y readiness

Los pods de prueba se conectaron a Services SQL temporales sin endpoints. Se habilitó el de Pharmacy primero y después el de Users. Gateway apuntó a esos backends aislados.

| Estado de los Services SQL de prueba | Users | Pharmacy | Gateway |
|---|---|---|---|
| Ambos sin endpoints durante al menos 33 s | 503, NotReady | 503, NotReady | 503, NotReady |
| Solo Pharmacy con endpoint | 503, NotReady | 200 Healthy, Ready | 200 Degraded, Ready |
| Ambos con endpoint | 200 Healthy, Ready | 200 Healthy, Ready | 200 Healthy, Ready |

En todas las etapas, liveness devolvió HTTP 200. Los tres pods conservaron sus UID y registraron cero reinicios. Los recursos temporales se retiraron al terminar y el pod SQL mantuvo su UID durante todo el ensayo.

## Recuperación automática del proceso

Se suspendió con `SIGSTOP` un proceso `dotnet` por vez en los Deployments. La cronología muestra `Ready → NotReady → Ready` y un reinicio del contenedor en el mismo pod. Los eventos `Unhealthy` y `Killing` atribuyen el reinicio a liveness. Prometheus registró `up` en `1 → 0 → 1` para cada pod. Los logs del nuevo contenedor registraron el arranque del servidor HTTP.

| Proceso suspendido | Ruta por Gateway | Inicio UTC | Primer NotReady UTC | Ready otra vez UTC | Tiempo hasta Ready | HTTP 200 válidos / intentos | Sin respuesta HTTP |
|---|---|---|---|---|---:|---:|---:|
| Gateway | `GET /api/drug` | 14:54:58 | 14:55:06 | 14:55:38 | 40,57 s | 2 / 21 | 19 |
| Users | `POST /api/login` | 14:55:43 | 14:55:51 | 14:56:21 | 37,77 s | 7 / 8 | 1 |
| Pharmacy | `GET /api/drug` | 14:56:25 | 14:56:32 | 14:57:00 | 34,95 s | 18 / 19 | 1 |

Los conteos incluyen solicitudes antes, durante y después de cada falla. Una respuesta válida devolvió cuatro medicamentos o un token de login según la ruta. El valor `http: 0` en la evidencia representa una solicitud sin respuesta HTTP con un timeout de cliente de 2 s. Al terminar, los tres Deployments recuperaron su dotación completa (1 Gateway, 2 Users y 2 Pharmacy) y los tres endpoints de salud de cada servicio respondieron `Healthy`.

[Cronología y resultados en JSON](proof.json). El archivo contiene los estados observados, las muestras HTTP, los eventos, fragmentos de arranque y las series OTLP de las rutas visibles al consultar Prometheus. El ensayo cubre pérdida de un proceso. La topología local aloja las réplicas de cada servicio en un solo nodo Kubernetes. La continuidad durante rollout y rollback se evalúa en la #8 y la protección por rate limiting en la #9.

## Comandos

Se usó el flujo de construcción y carga de imágenes de la [guía Kubernetes](../../../Implementacion%20K8S/Codigo/k8s/README-k8s.md) y el Job de migración completó antes del despliegue. Pasaron las 23 pruebas de regresión y el despliegue de las tres imágenes.

```powershell
$ctx = 'pharmago-issue3'
$k8s = 'Implementacion K8S/Codigo/k8s'
$py = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
$secrets = '.runtime/secrets.local.json' # Ajustar a la ruta local del entorno
& $py -m unittest discover -s $k8s
& $py "$k8s/manage.py" apply --context $ctx --image-tag issue7-recovery-20261110 --secrets-file $secrets
kubectl --context $ctx -n pharmago get deploy pharmago-api-gateway pharmago-users-service pharmago-pharmacy-service
```

La [guía de probes](../../aiops-k8s-probes.md) detalla las comprobaciones, la inyección acotada, los eventos y las consultas de Prometheus.
