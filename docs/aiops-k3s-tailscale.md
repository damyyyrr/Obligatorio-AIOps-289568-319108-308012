# Despliegue de PharmaGo en tres PCs con k3s y Tailscale

Esta guía reúne la preparación del clúster físico y el despliegue de la aplicación. La [evidencia de ejecución](evidence/chaos-3pc-20261116/README.md) acredita el entorno usado por el equipo; la instalación nueva descrita aquí se revisó contra el código y la documentación oficial, sin repetirla desde cero durante esta revisión.

## Entorno y requisitos

| PC | Nodo | Aplicaciones y recursos principales |
|---|---|---|
| A | `pharmago-a`, servidor k3s | Gateway, SQL, Elasticsearch, Prometheus, Grafana, Jaeger y Collector |
| B | `pharmago-b`, agente | Users ×2, UI y Kibana |
| C | `pharmago-c`, agente | Pharmacy ×2 y clientes de caos |

Cada PC necesita Ubuntu 24.04 en WSL2, systemd, acceso a Internet y capacidad reservada para sus pods. El laboratorio registró 16/16/8 GB físicos; WSL expone menos memoria a Kubernetes. Consultar [topología y capacidad](aiops-k8s-topology.md). Una PC con Docker Linux construye las cuatro imágenes; la estación que administra el clúster necesita Git, PowerShell, Python 3.10+ y kubectl.

Comprobar systemd dentro de Ubuntu con `ps -p 1 -o comm=` y seguir la [configuración de WSL de Microsoft](https://learn.microsoft.com/en-us/windows/wsl/systemd) si hace falta habilitarlo. Mantener las sesiones Ubuntu abiertas y las PCs sin suspensión durante el ensayo; no ejecutar `wsl --shutdown` con el laboratorio en uso.

## Conectar Ubuntu mediante Tailscale

Instalar Tailscale **dentro de Ubuntu**, según la [guía oficial para WSL2](https://tailscale.com/docs/install/windows/wsl2). Conectar los tres nodos a la misma red del equipo. En cada Ubuntu:

```bash
sudo systemctl enable --now tailscaled
sudo tailscale up --hostname=pharmago-a --accept-dns=false
tailscale ip -4
tailscale status
```

Cambiar el hostname por `pharmago-b` o `pharmago-c` en sus PCs. La autenticación es interactiva; no guardar claves de acceso en el repositorio. Registrar las tres IPs de `tailscale0` para los pasos siguientes. Verificar comunicación entre pares antes de instalar k3s.

Permitir entre esos nodos el puerto TCP 6444 del servidor, TCP 10250 y UDP 8472 para VXLAN, además del tráfico de pods/servicios que requiera el firewall de Ubuntu. Restringir las reglas al laboratorio y comprobar las [reglas de red de k3s](https://docs.k3s.io/installation/requirements). El puerto 9100 de node-exporter debe estar libre y accesible desde el monitoreo. El puerto 6444 conserva la elección del laboratorio; no se expone la API a Internet.

## Preparar k3s en un laboratorio nuevo

Estos pasos son para nodos sin otra instalación k3s. Si ya hay clúster, configuración o volúmenes, conservarlos y revisar con su responsable; los scripts históricos de migración desinstalan agentes y no son el punto de entrada para una instalación nueva.

En PC A, crear con permisos de root `/etc/rancher/k3s/config.yaml`, sustituyendo la IP por la de `tailscale0`:

```yaml
node-name: pharmago-a
node-ip: "<IP_TAILSCALE_A>"
flannel-iface: tailscale0
https-listen-port: 6444
tls-san:
  - "<IP_TAILSCALE_A>"
```

Instalar el servidor desde Ubuntu A, con la versión registrada en las evidencias:

```bash
curl -sfL https://get.k3s.io -o /tmp/pharmago-install-k3s.sh
sudo env INSTALL_K3S_VERSION='v1.34.1+k3s1' sh /tmp/pharmago-install-k3s.sh server
sudo systemctl is-active k3s
```

El responsable de A comparte por un canal privado el token de unión generado en `/var/lib/rancher/k3s/server/node-token`. En B y C guardarlo como `/root/.k3s-token`, legible solo por root (`chmod 600`). No imprimirlo en reportes ni adjuntarlo como evidencia.

En cada agente, preparar `/etc/rancher/k3s/config.yaml`; cambiar el nombre y la IP local para C:

```yaml
server: "https://<IP_TAILSCALE_A>:6444"
token-file: /root/.k3s-token
node-name: pharmago-b
node-ip: "<IP_TAILSCALE_B>"
flannel-iface: tailscale0
```

Instalar dentro de Ubuntu B y C:

```bash
curl -sfL https://get.k3s.io -o /tmp/pharmago-install-k3s.sh
sudo env INSTALL_K3S_VERSION='v1.34.1+k3s1' sh /tmp/pharmago-install-k3s.sh agent
sudo systemctl is-active k3s-agent
```

La [configuración de k3s](https://docs.k3s.io/installation/configuration), las [opciones del servidor](https://docs.k3s.io/cli/server) y las [opciones de agente](https://docs.k3s.io/cli/agent) describen esos parámetros. Conservar el controlador de NetworkPolicy de k3s para los ensayos de red; el laboratorio físico no usa Calico.

## Acceso y etiquetas del clúster

En A, `sudo k3s kubectl get nodes -o wide` debe mostrar los tres nodos Ready. Para administrar desde Windows, crear `.runtime/` en el checkout y transferir allí de forma privada `/etc/rancher/k3s/k3s.yaml` como `k3s.yaml`. Esa credencial tiene permisos administrativos; mantenerla fuera de Git. Cambiar únicamente el campo `server` a `https://<IP_TAILSCALE_A>:6444`, conservando los certificados, según la [guía de acceso de k3s](https://docs.k3s.io/cluster-access).

Desde la raíz del repositorio, en PowerShell:

```powershell
$env:KUBECONFIG = (Resolve-Path '.runtime/k3s.yaml').Path
kubectl config rename-context default pharmago-3pc
kubectl config use-context pharmago-3pc
$ctx = 'pharmago-3pc'
kubectl --context $ctx get nodes -o wide
kubectl --context $ctx label node pharmago-a node-type=ops pharmago.io/service=gateway
kubectl --context $ctx label node pharmago-b node-type=frontend pharmago.io/service=users
kubectl --context $ctx label node pharmago-c pharmago.io/service=pharmacy
```

Si las etiquetas ya existen, comprobar sus valores; no mover el rol de almacenamiento para resolver un Pending. Comprobar DNS y conexiones entre pods ubicados en PCs distintas: tres nodos Ready solo verifican el plano de control, no toda la red de aplicación.

## Construir e importar imágenes

`k8s/build-images.*` usa Minikube. Para k3s, construir desde los mismos Dockerfiles/contextos que define `k8s/manage.py`, con un tag nuevo. En PowerShell, desde la raíz del checkout:

```powershell
$code = 'Implementacion K8S/Codigo'
$tag = 'k3s-entrega-01'
docker build -f "$code/Backend/PharmaGo.UsersService/Dockerfile" -t "pharmago-users-service:$tag" "$code/Backend"
docker build -f "$code/Backend/PharmaGo.PharmacyService/Dockerfile" -t "pharmago-pharmacy-service:$tag" "$code/Backend"
docker build -f "$code/Backend/PharmaGo.ApiGateway/Dockerfile" -t "pharmago-api-gateway:$tag" "$code/Backend"
docker build -f "$code/Frontend/Dockerfile" -t "pharmago-ui:$tag" "$code/Frontend"
docker save --output .runtime/pharmago-images.tar "pharmago-users-service:$tag" "pharmago-pharmacy-service:$tag" "pharmago-api-gateway:$tag" "pharmago-ui:$tag"
Get-FileHash .runtime/pharmago-images.tar -Algorithm SHA256
```

Ejecutar cada construcción por separado y detenerse si falla. No reutilizar un tag con contenido distinto. Transferir el archivo tar a las tres PCs, comprobar su SHA-256 y, dentro de cada Ubuntu, importar usando su ruta Linux real:

```bash
sudo k3s ctr -n k8s.io images import '/ruta/al/pharmago-images.tar'
sudo k3s crictl images
```

Comprobar las cuatro referencias `docker.io/library/pharmago-…:<tag>` en **cada nodo**, junto con sus IDs/digests. Docker y containerd tienen almacenes distintos; construir una imagen en Docker no la pone en k3s. La [importación de imágenes de k3s](https://docs.k3s.io/add-ons/import-images) permite trabajar con los manifiestos de aplicación que usan `imagePullPolicy: Never`. Las imágenes de infraestructura requieren acceso a sus registros, salvo que también se precarguen. No versionar el tar.

## Aplicar, cargar datos y comprobar

Seguir la [preparación Python, Secrets y apply comunes](<../Implementacion K8S/Codigo/k8s/README-k8s.md>). Con las dependencias instaladas, `$python` apuntando al entorno virtual y el mismo `$ctx` y `$tag`:

```powershell
$k8s = 'Implementacion K8S/Codigo/k8s'
& "$k8s/apply-k8s.ps1" -Context $ctx -ImageTag $tag -Python $python -Timeout 600
kubectl --context $ctx -n pharmago get pods -o wide
kubectl --context $ctx -n pharmago get pv,pvc
```

El apply ejecuta las migraciones, pero no carga datos demo. Para una base nueva de laboratorio, revisar `Implementacion K8S/Codigo/Backend/seed-data.sql`, que agrega los datos docentes ausentes. Cargarlo solo después de las migraciones, con la credencial vigente del contenedor SQL:

```powershell
$sqlPod = kubectl --context $ctx -n pharmago get pod -l app=pharmago-db -o jsonpath='{.items[0].metadata.name}'
$sqlcmd = 'export SQLCMDPASSWORD="$MSSQL_SA_PASSWORD"; exec /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -b'
Get-Content -Raw 'Implementacion K8S/Codigo/Backend/seed-data.sql' | kubectl --context $ctx -n pharmago exec -i $sqlPod -- sh -c $sqlcmd
```

Si la imagen SQL usa herramientas anteriores, seguir el ajuste de ruta de la [guía de datos y recuperación](aiops-k8s-recovery.md). Detenerse ante un error; no resetear una DB existente para obtener un PASS.

Abrir UI y Gateway con los port-forward de la guía común, y comprobar catálogo, roles y login. Registrar nodos/pods, imágenes, resultados funcionales y UIDs de PV/PVC. Consultar [métricas](aiops-k8s-metrics.md), [probes](aiops-k8s-probes.md) y [plan de incidentes](baseline-incidents.md). Para caos, usar su [guía](<../Implementacion K8S/Codigo/chaos-engineering/README.md>) y sus prechecks; el fallo de cualquiera de ellos impide iniciar una inyección.

## Parada y antecedentes

`k8s/cleanup.ps1` escala Deployments a cero y conserva datos; deja activos los DaemonSets y no apaga k3s ni WSL. Coordinar la parada de los equipos después de verificar la limpieza y guardar las evidencias. Reaplicar restaura las réplicas; no ejecutar desinstaladores o borrado de PV como rutina de parada.

Los archivos `unirse-nodo.ps1` y `abrir-firewall.ps1` del paquete original corresponden a Hamachi; `migrar-tailscale.ps1` y `migrate-node.sh` trasladaron agentes ya preparados. Requieren archivos privados y un tar que no se publican. Se conservan como evidencia del procedimiento usado y no deben ejecutarse automáticamente para seguir esta guía.
