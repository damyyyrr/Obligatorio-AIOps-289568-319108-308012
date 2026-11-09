# Issue #3 — validación de topología Kubernetes

Fecha: 09/11/2026 (Uruguay). Rama `feature/issue-3-topologia-k8s`, basada en `14cae7f` de `obligatorio` con cambios locales de la issue. Clúster aislado `pharmago-issue3`: Minikube 1.39.0, driver Docker, Kubernetes y kubectl 1.34.1, containerd 2.3.4, Docker Desktop 4.52.0 y Engine 29.0.1. El host Windows 11/WSL2 tenía 12 CPU lógicas, 15,95 GiB físicos, 7,73 GiB para Docker y aproximadamente 54 GiB libres en C: durante la prueba. Todos los nodos Kubernetes de la prueba comparten ese host.

[capacity.json](capacity.json) registra las sumas de recursos de los manifiestos y los límites reales de los nodos. [images.json](images.json) registra el digest de configuración comprobado con CRI en cada nodo elegible. Pasaron las 19 pruebas de regresión y el dry run del API server para los cinco Deployments modificados. Se comprobó que el modo `single-node` renderiza para `node-type=all` y que el apply lo rechaza en este clúster de tres nodos.

## Resultado local: aprobado

El primer apply dejó **16/16 pods Ready**. Durante el reinicio simultáneo se observó, para cada servicio, el pod original Ready y el nuevo ya programado en el mismo nodo. Los tres rollouts terminaron y los 16 pods volvieron a estar Ready. En el muestreo de Kubernetes no hubo ninguna observación con cero pods Ready de alguno de los tres servicios.

| Servicio | Nodo | Máximo de pods activos durante el rollout | Mínimo de pods Ready observado |
|---|---|---:|---:|
| Gateway | `pharmago-issue3` | 2 | 1 |
| Users | `pharmago-issue3-m02` | 2 | 1 |
| Pharmacy | `pharmago-issue3-m03` | 2 | 1 |

[rollout.json](rollout.json) guarda los pods antes, durante y después. Tras el rollout, se cargó el seed de prueba una vez; frontend, catálogo y login respondieron HTTP 200, con cuatro medicamentos y token presente ([smoke.json](smoke.json)). Se repitió el apply con el mismo tag: 16 pods Ready, los cuatro PV y cuatro PVC conservaron sus UIDs y el mismo nodo de almacenamiento ([apply.json](apply.json)).

## Reproducción

Se conservó el perfil de la #2 detenido. El perfil nuevo se creó y se etiquetó siguiendo la [guía Kubernetes](../../../Implementacion%20K8S/Codigo/k8s/README-k8s.md). Estos comandos muestran los ajustes usados después de iniciar los tres nodos:

```powershell
minikube start -p pharmago-issue3 --nodes 3 --driver=docker --container-runtime=containerd --kubernetes-version=v1.34.1 --cpus=2 --memory=2500
docker update --cpus 4 --memory 4200m --memory-swap 4200m pharmago-issue3
docker update --memory 2100m --memory-swap 2100m pharmago-issue3-m02
docker update --memory 1100m --memory-swap 1100m pharmago-issue3-m03
kubectl --context pharmago-issue3 label node pharmago-issue3 node-type=ops pharmago.io/service=gateway
kubectl --context pharmago-issue3 label node pharmago-issue3-m02 node-type=frontend pharmago.io/service=users
kubectl --context pharmago-issue3 label node pharmago-issue3-m03 pharmago.io/service=pharmacy
kubectl --context pharmago-issue3 get nodes -L pharmago.io/service,node-type
```

En este equipo se pasó además `--base-image=pharmago-kicbase:issue2` para usar el alias local del kicbase de Minikube v0.0.51. Se reutilizaron las [imágenes construidas en #2](../issue-2-20261108/live/build.json) porque el código de backend y frontend es el mismo. Se cargaron solo en sus nodos elegibles con `docker save` en streaming a `docker exec -i <nodo> ctr -n k8s.io images import -`. Se precargó Elasticsearch desde Docker local. Para reproducir en otro equipo, se pueden construir las cuatro imágenes y cargarlas en todos los nodos con `build-images` según la guía.

```powershell
$k8s = 'Implementacion K8S/Codigo/k8s'
$python = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
& $python -m unittest discover -s $k8s
& "$k8s/apply-k8s.ps1" -Context pharmago-issue3 -ImageTag issue2-live-20261108-125407 -Python $python
kubectl --context pharmago-issue3 -n pharmago get pods -o wide
kubectl --context pharmago-issue3 -n pharmago get pvc
```

Para observar el solapamiento, empezar a consultar `get pods -o json` en una terminal antes de disparar el reinicio desde otra. Guardar por pod nombre, nodo, condición Ready y si está terminando, sin exportar el spec completo. El reinicio modifica la plantilla de los tres Deployments y conserva el tag y el código; no aplica una migración nueva.

```powershell
kubectl --context pharmago-issue3 -n pharmago rollout restart deployment/pharmago-api-gateway deployment/pharmago-users-service deployment/pharmago-pharmacy-service
kubectl --context pharmago-issue3 -n pharmago rollout status deployment/pharmago-api-gateway
kubectl --context pharmago-issue3 -n pharmago rollout status deployment/pharmago-users-service
kubectl --context pharmago-issue3 -n pharmago rollout status deployment/pharmago-pharmacy-service
kubectl --context pharmago-issue3 -n pharmago get pods -o wide
```

Para la comprobación funcional se usó `Backend/seed-data.sql` y port-forward a UI y Gateway como en la guía; solo se guardaron estados HTTP y conteos. El apply repetido no volvió a cargar el seed.

Ver [diagrama, presupuesto y mapa de hosts](../../aiops-k8s-topology.md). El ensayo local sirve para verificar colocación y surge. La prueba en máquinas físicas diferentes (Q01) y el rollout/rollback con tráfico y dos versiones (#8) son verificaciones separadas.
