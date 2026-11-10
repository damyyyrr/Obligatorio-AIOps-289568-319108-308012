# PharmaGo en Kubernetes — despliegue y topología

PowerShell y Bash ejecutan el mismo `manage.py`. Se requiere Python 3.10+, las dependencias fijadas en `requirements.txt`, kubectl, Docker y Minikube para construir/cargar imágenes. El clúster debe existir y ser accesible. No se instala ni se cambia de contexto automáticamente.

## Preparación

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .runtime/k8s-venv
$python = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
& $python -m pip install -r 'Implementacion K8S/Codigo/k8s/requirements.txt'
kubectl config current-context
kubectl get nodes --show-labels
```

En Linux/macOS, usar `.runtime/k8s-venv/bin/python` y exportar su ruta absoluta como `PHARMAGO_PYTHON` para los scripts Bash. Se pueden ejecutar desde cualquier directorio; las rutas con espacios se pasan como argumentos separados.

Elegir un perfil propio y dimensionar CPU/RAM/disco según la suma de requests/límites de los manifiestos y la capacidad libre del host. El conjunto incluye SQL, Elasticsearch, Kibana, Prometheus y Grafana; no se presume que 6 GB sean suficientes. Para un clúster local nuevo, crear explícitamente el perfil con `minikube start -p <perfil> --nodes <cantidad> --memory <MiB-por-nodo> --cpus <cpu-por-nodo>` y seleccionar su contexto con `kubectl config use-context <contexto>`.

El modo predeterminado requiere tres roles de servicio y un único nodo de almacenamiento. Para un clúster nuevo de tres nodos, sustituir los nombres por los de `kubectl get nodes`:

```text
kubectl --context <contexto> label node <nodo-gateway> node-type=ops pharmago.io/service=gateway
kubectl --context <contexto> label node <nodo-users> node-type=frontend pharmago.io/service=users
kubectl --context <contexto> label node <nodo-pharmacy> pharmago.io/service=pharmacy
```

Ver [topología y dimensionamiento](../../../docs/aiops-k8s-topology.md). Las etiquetas se establecen deliberadamente, nunca por el script. El clúster de desarrollo de un solo nodo se puede seguir usando: etiquetar ese nodo `node-type=all` y pasar `-Topology single-node` (PowerShell) o `--topology single-node` (Bash y render). Este modo no es válido para comprobar la separación.

## Construcción y carga

```powershell
$k8s = 'Implementacion K8S/Codigo/k8s'
& "$k8s/build-images.ps1" -Context '<contexto>' -Profile '<perfil>' -ImageTag 'k8s-20261108-01' -Python $python
```

Equivalente Bash:

```bash
bash 'Implementacion K8S/Codigo/k8s/build-images.sh' --context '<contexto>' --profile '<perfil>' --image-tag k8s-20261108-01
```

Elegir un tag nuevo por construcción; se rechaza sobrescribir uno existente. Se comprueba que perfil y contexto identifiquen los mismos nodos por UID. Las cuatro imágenes se construyen desde sus Dockerfiles, se cargan mediante Minikube y se verifica su presencia y digest de configuración con `crictl images` en cada nodo. El digest de configuración se obtiene de una exportación Docker en streaming: el ID OCI de Docker puede diferir del ID de CRI. El reporte local registra ambos IDs, commit y estado del árbol. Si una construcción queda a medias, usar un nuevo tag al repetirla.

`build-ui.sh` admite las mismas opciones y construye/carga solo UI; ya no reinicia un Deployment por sorpresa. El despliegue posterior es explícito. Para evitar que el tag seleccionado cambie otras aplicaciones, usar el flujo completo con cuatro imágenes para una instalación integral.

## Render y despliegue

Antes del primer apply, copiar `secrets.example.json` a `secrets.local.json` y reemplazar ambos valores. Git ignora `secrets.local.json`. Usar una contraseña de SQL Server con la complejidad requerida por SQL y otra para Grafana. Para un clúster con datos previos, usar las contraseñas ya vigentes en SQL y Grafana. Se puede elegir otro archivo ignorado con `-SecretsFile` (PowerShell) o `--secrets-file` (Bash). Ver [guía de datos y recuperación](../../../docs/aiops-k8s-recovery.md).

Inspección sin clúster:

```powershell
& $python "$k8s/manage.py" render --image-tag k8s-20261108-01 --output .runtime/k8s-render.json
```

El render muestra las referencias a los Secrets y las reglas base de almacenamiento. Usar el script de apply para configurar los Secrets y resolver el nodo de almacenamiento real. Los manifiestos originales de aplicación tienen el tag de referencia `k8s-local`; el flujo soportado los renderiza con el tag elegido. Las imágenes operativas tienen versión fija; SQL usa el digest ya conservado en `docs/evidence/baseline-20261106/runtime-images.json`. No se hace pull de `latest`.

```powershell
& "$k8s/apply-k8s.ps1" -Context '<contexto>' -ImageTag k8s-20261108-01 -Python $python -Timeout 600
```

Equivalente Bash:

```bash
bash 'Implementacion K8S/Codigo/k8s/apply-k8s.sh' --context '<contexto>' --image-tag k8s-20261108-01 --timeout 600
```

El contexto actual debe coincidir con el solicitado; todas las llamadas usan además `--context`. Se comprueban nodos Ready, etiquetas y namespace. Un PV `Released`, `Failed`, en eliminación o asociado a otro claim detiene la ejecución antes del apply. Su recuperación requiere diagnóstico manual; no se borra ni se fuerza el rebind.

Los PV nuevos registran el UID del nodo propietario como anotación `pharmago.io/storage-node-uid` y quedan restringidos a su hostname. El apply aborta si el UID cambia. Conserva la afinidad de los PV existentes y restringe los Deployments que usan PVC al hostname verificado. Antes de adoptar un PV anterior sin anotación en modo separado, verificar el host y el contenido del directorio original. Solo entonces anotar su UID real con `kubectl annotate pv`. Mantener la etiqueta `node-type=ops` exclusivamente en el nodo propietario.

Orden de apply: namespace, Secrets, almacenamiento, ConfigMaps, RBAC, Services, SQL con espera, Job de migración, Elasticsearch con espera, resto de Deployments y DaemonSets. El Job ejecuta la imagen de Users con `--migrate` y debe terminar antes de actualizar los consumidores. Ver [migraciones y rollback](../../../docs/aiops-sql-migrations.md). Se incluye Fluent Bit y todo su RBAC en ambos sistemas. Cada fallo y cada timeout termina con código distinto de cero. Una falla puede dejar un despliegue parcial que se puede diagnosticar y reaplicar.

Al finalizar se esperan los rollouts de todos los Deployments y DaemonSets. Se comparan las identidades de PV y de sus claims previamente enlazados y se guarda un JSON en `k8s/.runtime/`, con pods e imágenes observadas, contexto, versión y hora UTC. `--output` (PowerShell: `-OutputPath`) permite elegir otra ruta. Ready y PV UID estable no prueban por sí solos que los datos de negocio estén intactos.

## Validación de la issue en un clúster de prueba

1. Construir/cargar y aplicar; conservar el JSON y `kubectl --context <contexto> -n pharmago get pods -o wide`.
2. Abrir dos terminales con `kubectl --context <contexto> -n pharmago port-forward service/pharmago-ui 4200:80` y `kubectl --context <contexto> -n pharmago port-forward service/pharmago-api-gateway 5000:80`. El frontend actual apunta a `http://127.0.0.1:5000`. Los Services son ClusterIP y el port-forward escucha en loopback por defecto.
3. Verificar login y catálogo. En una instalación nueva, cargar datos de prueba de forma explícita usando el SQL docente y la guía del backend; el apply no carga seed ni resetea datos. Conservar una consulta SQL de solo lectura con identificadores y conteos de registros de prueba conocidos, sin datos personales ni credenciales.
4. Repetir **exactamente el mismo apply y tag** con otro archivo de salida. Comparar PV/PVC UIDs, consulta SQL, login y catálogo. Las dos ejecuciones deben ser funcionales y conservar registros.
5. Ejecutar la parada y volver a aplicar; repetir las comprobaciones. Adjuntar comandos, versiones y resultados sanitizados a `docs/evidence/`. Validar en otro equipo o desde una instalación nueva siguiendo esta guía, sin borrar el clúster anterior.

La [validación de la #2](../../../docs/evidence/issue-2-20261108/live/README.md) registró estas pruebas en un nodo de desarrollo. Para la #3 se agrega la comprobación de nodos separados y del pod adicional de cada rollout.

Para consultar Prometheus, comparar targets con el inventario y abrir los paneles provisionados de Grafana, ver la [guía de métricas](../../../docs/aiops-k8s-metrics.md).

Para verificar salud, réplicas y recuperación de Gateway, Users y Pharmacy, ver la [guía de probes](../../../docs/aiops-k8s-probes.md).

## Parada y recuperación

```powershell
& "$k8s/cleanup.ps1" -Context '<contexto>' -Python $python
```

```bash
bash 'Implementacion K8S/Codigo/k8s/cleanup.sh' --context '<contexto>'
```

**Cambio de comportamiento:** `cleanup` ahora escala todos los Deployments de `pharmago` a cero; conserva namespace, servicios, Secret, ConfigMaps, PVC y PV. Los DaemonSets de Fluent Bit y node-exporter permanecen activos. No equivale a apagar el clúster completo. El próximo apply restaura las réplicas declaradas. No se ofrece borrado automático de datos. Las antiguas opciones `KeepVolumes`/`--keep-volumes` ya no son necesarias ni se aceptan.

## Diagnóstico y pruebas locales

```powershell
kubectl --context '<contexto>' -n pharmago get events --sort-by=.lastTimestamp
kubectl --context '<contexto>' -n pharmago describe pod '<pod>'
kubectl --context '<contexto>' -n pharmago logs '<pod>' --tail=100
& $python -m unittest discover -s 'Implementacion K8S/Codigo/k8s' -p 'test_*.py' -v
```

Ante `ErrImageNeverPull`, comprobar tag y presencia en cada nodo. Ante Pending, revisar etiquetas, afinidades, capacidad y estado de PVC/PV. Ante SQL/Elasticsearch sin Ready, consultar sus logs y recursos; el script no avanza ocultando el timeout. No usar borrado de namespace/PV o `minikube delete` como procedimiento de reparación.
