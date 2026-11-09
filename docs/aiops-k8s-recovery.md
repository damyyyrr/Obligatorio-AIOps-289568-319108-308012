# Credenciales, volúmenes y recuperación de PharmaGo

## Credenciales locales

Copiar `Implementacion K8S/Codigo/k8s/secrets.example.json` a `secrets.local.json` en la misma carpeta. El archivo local está ignorado por Git. Completar `sqlPassword` y `grafanaAdminPassword` con contraseñas independientes. SQL Server requiere una contraseña que cumpla su política de complejidad. El mismo valor de SQL configura el servidor y la conexión de Users y Pharmacy. Grafana usa su propio Secret. Ver el [flujo de despliegue](../Implementacion%20K8S/Codigo/k8s/README-k8s.md).

El apply crea o actualiza los Secrets por entrada estándar, sin guardar su contenido en la anotación `last-applied`, el render o la evidencia. En un clúster existente, usar la contraseña de SQL ya vigente y la contraseña vigente de Grafana. Cambiar el archivo local por sí solo no cambia una contraseña guardada en una base de datos. El apply rechaza una discrepancia con un Secret existente y preserva sus demás datos. Si se pierde el Secret SQL y el PV sigue presente, recuperar el Secret con la credencial vigente antes de reaplicar. Rotar contraseñas previas de manera coordinada con las aplicaciones y los Secrets.

Para Compose, usar `.env.example` como plantilla del `.env` ignorado. El arranque del baseline puede generar sus valores. En el Compose anterior, elegir para SQL una contraseña alfanumérica con símbolos como `!` o `_`, sin comillas dobles, para que su interpolación en la cadena de conexión sea válida. Al conservar volúmenes de Compose usar primero la credencial vigente.

## Acceso a los servicios

Los Services de Kubernetes quedan como ClusterIP. Para la demo, abrir solo los port-forward necesarios en `127.0.0.1`. UI usa 4200, Gateway 5000, Grafana 3000, Kibana 5601 y Prometheus 9090. SQL, Users y Pharmacy se consumen normalmente dentro del clúster. Elasticsearch está configurado sin autenticación para el entorno de prueba y debe permanecer en una red confiable. Node Exporter usa la red del nodo para sus métricas en 9100, por lo que se debe restringir ese puerto a la red privada de monitoreo. En el Compose anterior, todos los puertos publicados escuchan en loopback.

## Propietario de los volúmenes

| PV / PVC | Directorio del nodo | Consumidor |
|---|---|---|
| `sql-pv` / `sql-pvc` | `/mnt/data/sql` | SQL Server |
| `elasticsearch-pv` / `elasticsearch-pvc` | `/mnt/data/elasticsearch` | Elasticsearch |
| `prometheus-pv` / `prometheus-pvc` | `/mnt/data/prometheus` | Prometheus |
| `grafana-pv` / `grafana-pvc` | `/mnt/data/grafana` | Grafana |

El apply requiere un único nodo de almacenamiento disponible. Para cada PV nuevo registra su UID en `pharmago.io/storage-node-uid` y restringe el volumen a su etiqueta `kubernetes.io/hostname`. Los cuatro Deployments con PVC se fijan a ese hostname. Para PV anteriores se conserva su afinidad original y se verifica su UID anotado. Si falta la anotación en un clúster separado, primero identificar el nodo original y comprobar allí los directorios y datos. Después se puede adoptar cada PV con el UID verificado:

```powershell
$ctx = '<contexto>'
$owner = '<nodo-propietario-verificado>'
$uid = kubectl --context $ctx get node $owner -o 'jsonpath={.metadata.uid}'
kubectl --context $ctx annotate pv sql-pv elasticsearch-pv prometheus-pv grafana-pv "pharmago.io/storage-node-uid=$uid"
kubectl --context $ctx -n pharmago get pods,pvc -o wide
```

Los directorios viven en el disco de ese nodo y los PV tienen política Retain. Reiniciar el nodo con su disco permite volver a montar los mismos datos. Si se pierde el nodo o el disco, recuperar el almacenamiento original o restaurar un respaldo en otro volumen y verificarlo antes de reconectar aplicaciones. Mover una etiqueta no mueve los datos. La afinidad de un PV existente se conserva para evitar recrearlo. Ver [documentación de Persistent Volumes](https://v1-34.docs.kubernetes.io/docs/concepts/storage/persistent-volumes/#node-affinity).

## Backup y restauración de SQL

Usar un contexto explícito y un directorio local ignorado o externo al repositorio para el archivo `.bak`. El ejemplo supone PowerShell y un Deployment SQL de PharmaGo. `sqlcmd` toma la contraseña de la variable del contenedor. Ajustar la ruta a `/opt/mssql-tools/bin/sqlcmd` si la imagen usa la versión anterior y omitir `-C` en ese caso.

```powershell
$ctx = '<contexto-origen>'
$sourcePod = kubectl --context $ctx -n pharmago get pod -l app=pharmago-db -o 'jsonpath={.items[0].metadata.name}'
$backup = "pharmago-$([guid]::NewGuid().ToString('N')).bak"
$inPod = "/var/opt/mssql/$backup"
$local = ".runtime/$backup"
$sqlcmd = 'export SQLCMDPASSWORD="$MSSQL_SA_PASSWORD"; exec /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -b'
"BACKUP DATABASE [PharmaDb] TO DISK = N'$inPod' WITH COPY_ONLY, CHECKSUM; RESTORE VERIFYONLY FROM DISK = N'$inPod' WITH CHECKSUM;" |
    kubectl --context $ctx -n pharmago exec -i $sourcePod -- sh -c $sqlcmd
kubectl --context $ctx cp "pharmago/${sourcePod}:$inPod" $local
Get-FileHash -Algorithm SHA256 $local
```

Guardar una copia del respaldo fuera del nodo propietario y controlar quién puede leerla. Para comprobar persistencia, guardar el UID de cada PV/PVC y consultar filas conocidas antes y después de reiniciar el perfil. Reaplicar sin volver a cargar el seed. Comparar los UIDs y el resultado de la consulta.

Para restaurar, preparar una instancia SQL vacía en un entorno aislado. En un mismo clúster se puede usar `pharmago-restore-test` como namespace. Copiar el Deployment SQL y el par PV/PVC a un archivo local. Cambiar los nombres y las referencias del claim, elegir un directorio `hostPath` nuevo, fijar el PV y el pod al nodo que contiene ese directorio y crear el Secret SQL en ese namespace. Para el ensayo se usaron una instancia y un volumen independientes, con el origen detenido durante la restauración para liberar RAM. La credencial de la instancia destino se configura por separado del contenido del backup.

```powershell
$restoreCtx = '<contexto-destino>'
$targetNs = 'pharmago-restore-test'
$targetPod = '<pod-sql-destino>'
kubectl --context $restoreCtx cp $local "${targetNs}/${targetPod}:$inPod"
kubectl --context $restoreCtx -n $targetNs exec $targetPod -- sha256sum $inPod
"RESTORE VERIFYONLY FROM DISK = N'$inPod' WITH CHECKSUM; RESTORE FILELISTONLY FROM DISK = N'$inPod';" |
    kubectl --context $restoreCtx -n $targetNs exec -i $targetPod -- sh -c $sqlcmd
```

Comparar el SHA-256 de la copia y usar los nombres lógicos de datos y log que devuelve `FILELISTONLY`. Ejecutar la restauración en el destino vacío, con rutas bajo el nuevo volumen. El siguiente ejemplo usa los nombres lógicos habituales de PharmaDb.

```powershell
@"
RESTORE DATABASE [PharmaDb] FROM DISK = N'$inPod' WITH CHECKSUM,
    MOVE N'PharmaDb' TO N'/var/opt/mssql/data/PharmaDb.mdf',
    MOVE N'PharmaDb_log' TO N'/var/opt/mssql/data/PharmaDb_log.ldf';
DBCC CHECKDB (N'PharmaDb') WITH NO_INFOMSGS, ALL_ERRORMSGS;
"@ | kubectl --context $restoreCtx -n $targetNs exec -i $targetPod -- sh -c $sqlcmd
```

Comparar los registros restaurados con la consulta de origen. El procedimiento probado cubre el respaldo de los datos de negocio en SQL Server. Elasticsearch, Prometheus y Grafana conservan sus discos en reinicios y tienen procedimientos de respaldo propios. Ver [restauración de SQL a una ubicación nueva](https://learn.microsoft.com/en-us/sql/relational-databases/backup-restore/restore-a-database-to-a-new-location-sql-server).
