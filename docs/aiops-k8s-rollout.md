# Rollout y rollback funcional de la aplicación

La issue #8 mide Gateway → Users/Pharmacy → SQL. Usa RollingUpdate con `maxUnavailable: 0`, `maxSurge: 1` y los probes funcionales de la [#7](aiops-k8s-probes.md). Cada pod nuevo debe permanecer Ready durante 10 s antes de retirar el anterior. El plazo de progreso del Deployment es 240 s; un timeout requiere diagnóstico y no provoca rollback automático de Kubernetes.

Al retirar un pod, Kubernetes actualiza sus EndpointSlices y ejecuta `preStop` antes de enviar SIGTERM. El hook espera 10 s manteniendo el servidor disponible mientras se propaga la retirada de endpoints. Después ASP.NET Core dispone de 20 s para completar solicitudes en vuelo. El pod tiene 40 s de gracia total: hook, apagado y 10 s de margen. Los 5 s del probe de liveness siguen siendo exclusivos de los reinicios por proceso bloqueado. Esta espera de drenaje debe medirse de nuevo si cambia la red o la duración de las operaciones. [Terminación de pods](https://v1-34.docs.kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination) · [RollingUpdate](https://v1-34.docs.kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-update-deployment)

Users y Pharmacy conservan dos réplicas y Gateway una. El surge cabe en el nodo de cada servicio; los pods en terminación pueden exceder temporalmente `réplicas + surge`. Reservar también su memoria: durante este recambio pueden coexistir cuatro pods de un backend (requests de 400m/512Mi) o dos de Gateway (200m/256Mi). Ver [topología](aiops-k8s-topology.md). Esta técnica cubre recambios planificados con el nodo disponible.

## Compatibilidad entre versiones

Antes de actualizar consumidores, el Job de la imagen nueva ejecuta `--migrate`, con el bloqueo y la comprobación del historial de la [#5](aiops-sql-migrations.md). El ensayo de #8 conserva las diez migraciones históricas: A usa los binarios de #7 y B agrega el timeout explícito de apagado. Se comparan las huellas de medicamentos, usuarios e historial antes, después de B y después del rollback. Las sesiones creadas por login se excluyen de esa huella. No se ejecutan migraciones Down.

La política de drenaje se instala en A **antes** de la ventana medida para que las revisiones guardadas también sean seguras al volver. La primera adopción de esta política desde manifests anteriores queda fuera de esa medición. En una futura versión con cambios de esquema hay que demostrar compatibilidad de A y B con ese esquema antes del ensayo; este resultado no la presupone.

## Repetición en un clúster de pruebas

1. Confirmar contexto, nodos y capacidad; desplegar una versión A sana con la política de drenaje. Conservar las credenciales y los datos existentes. Construir B con un tag nuevo y cargar/verificar sus imágenes en los nodos elegibles mediante el flujo de la [guía Kubernetes](../Implementacion%20K8S/Codigo/k8s/README-k8s.md).
2. Usar un usuario de prueba existente y asignar su contraseña a `PHARMAGO_TEST_PASSWORD` en la terminal local. No pasarla por argumentos ni guardarla en evidencia.
3. Ejecutar desde la raíz:

```powershell
$py = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
$k8s = 'Implementacion K8S/Codigo/k8s'
& $py -m unittest discover -s $k8s
& $py "$k8s/verify_rollout.py" --context '<contexto>' --image-tag '<tag-B>' --output '.runtime/rollout-proof.json'
Remove-Item Env:PHARMAGO_TEST_PASSWORD
```

El generador usa `curl` del pod estable de Elasticsearch para acceder al ClusterIP normal de Gateway. Un port-forward directo a Gateway quedaría ligado al pod retirado y no mediría el Service. Los `GET /api/drug` y `GET /api/roles` se envían cada 3 s, y `POST /api/login` cada 8 s desde la misma IP, sin reintentos de curl. El timeout HTTP es 2 s. Son aproximadamente 48 solicitudes/min y 8 logins/min, por debajo de las cuotas actuales de 100/min y 10 logins/min. No cambiar ni desactivar el limitador para mejorar el resultado.

Para adoptar la política de drenaje en una A ya instalada, antes de medir se pueden aplicar solo los tres Deployments con el tag A, desde la raíz. Sustituir contexto y tag por los valores verificados del entorno:

```powershell
@'
import sys
sys.path.insert(0, 'Implementacion K8S/Codigo/k8s')
import manage
cluster = manage.Cluster('<contexto>')
cluster.preflight()
apps = {'pharmago-api-gateway', 'pharmago-users-service', 'pharmago-pharmacy-service'}
for doc in manage.resources('<tag-A>'):
    if doc['kind'] == 'Deployment' and doc['metadata']['name'] in apps:
        cluster.apply([doc])
        cluster.wait(doc, 240)
'@ | & $py -
```

El tráfico empieza 20 s antes de migrar. Se actualizan Users, Pharmacy y Gateway secuencialmente y se esperan sus rollouts y el drenaje de los pods antiguos. Se mantienen 20 s con B y luego se ejecuta `rollout undo --to-revision` en orden inverso. Se compara la plantilla completa restaurada y se mantienen otros 20 s de tráfico. La carga queda acotada a 900 s; superar ese plazo invalida la prueba. Coordinar un único release a la vez.

El JSON registra todos los intentos, códigos, timeouts, errores de transporte/validación, percentiles de latencia, fases, pods/digests, EndpointSlices, revisiones y contadores OTLP por instancia. Catálogo y roles deben conservar su contenido, y login devolver un token y el usuario esperado. Los 429 cuentan como errores. No se almacenan tokens, contraseñas ni cuerpos de respuesta. La prueba sale con código distinto de cero si falla el tráfico, el rollback, la conservación de datos o la observación de versiones Ready coexistentes.

Ante un fallo del candidato el generador intenta restaurar las revisiones guardadas y registra el resultado. Observar recursos del host durante la prueba; ante OOM, reinicios reiterados o presión sostenida, interrumpir el ensayo y verificar la recuperación de esos tres Deployments. No borrar PV/PVC, ejecutar seed ni modificar SQL para recuperar un rollout. Conservar el JSON fallido y diagnosticar antes de repetir.

## Alcance

Se reemplazan los tres procesos de aplicación, con el frontend, SQL y observabilidad estables. SQL Express conserva una réplica y `Recreate`: su reemplazo sin interrupción sigue sin implementar ni probar. El frontend no forma parte del tráfico medido. Q01 sigue pendiente para separación física. Q02 no autoriza excluir SQL u observabilidad de la letra; R03 completo permanece incompleto aunque se cierre #8. Ver el [pendiente SQL y el alcance de #5/#8](aiops-sql-migrations.md#disponibilidad-de-sql-y-q02). Un éxito local debe informarse como “100% observado en N solicitudes durante T y bajo estas condiciones”. [Evidencia de #8](evidence/issue-8-20261111/README.md).
