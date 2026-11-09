# Issue #4 — secretos externos, persistencia y restauración

Validación local del 09/11/2026 en `feature/issue-4-secretos-restauracion`, basada en `428720d` de `obligatorio`. Se reutilizó el perfil de ensayo de la #3 para comprobar una actualización sobre datos existentes. Entorno: Minikube 1.39.0, Docker Engine 29.0.1, Kubernetes y kubectl 1.34.1, containerd 2.3.4, tres nodos en una PC Windows/WSL2 y la imagen SQL Server fijada en `db-deployment.yaml`.

| Prueba | Resultado |
|---|---|
| Actualización a credenciales externas | 16 pods Ready. Los Secrets contienen solo las claves esperadas y carecen de la anotación `last-applied`. La consulta anterior al apply coincidió con la posterior. |
| Acceso a la aplicación | Frontend, catálogo y login HTTP 200. Grafana devolvió HTTP 200 en `/api/user` con la credencial local. Los 11 Services quedaron como ClusterIP. |
| Credencial SQL diferente | El apply la rechazó antes de modificar recursos. |
| Reinicio y reaplicación | Se reemplazó el pod SQL, reaplicó el mismo tag y confirmó la misma consulta, los mismos cuatro PV y los mismos cuatro PVC. Se verificaron la colocación de los pods con PVC y su afinidad al hostname propietario. |
| Respaldo SQL | `BACKUP DATABASE` con `COPY_ONLY, CHECKSUM` y `RESTORE VERIFYONLY` aprobados. La copia local y la que recibió SQL de destino tuvieron el mismo SHA-256. |
| Restauración aislada | Una segunda instancia SQL, con otra credencial, restauró en un PV/PVC nuevos y un `hostPath` distinto. Coincidieron los cuatro medicamentos, el total de tres usuarios y el marcador de prueba. Pasó `DBCC CHECKDB`. |

[proof.json](proof.json) contiene el mapa de volúmenes, sus UIDs, el hash del respaldo y los resultados sanitizados. Los archivos de credenciales y el `.bak` permanecen en el directorio local ignorado. El ensayo verifica recuperación de los datos SQL y persistencia de los volúmenes de origen. Los respaldos de observabilidad son específicos de cada componente.

## Comandos de reproducción

Se cargaron en un archivo ignorado las credenciales vigentes de la instalación previa. El test reutilizó las imágenes de aplicación de la #3.

```powershell
$ctx = 'pharmago-issue3'
$k8s = 'Implementacion K8S/Codigo/k8s'
$py = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
$localSecrets = '.runtime/issue4-upgrade-secrets.local.json'
& $py -m unittest discover -s $k8s
& $py "$k8s/manage.py" apply --context $ctx --image-tag issue2-live-20261108-125407 --secrets-file $localSecrets
kubectl --context $ctx -n pharmago get pods,pvc,svc -o wide
kubectl --context $ctx -n pharmago rollout restart deployment/pharmago-db
kubectl --context $ctx -n pharmago rollout status deployment/pharmago-db
& $py "$k8s/manage.py" apply --context $ctx --image-tag issue2-live-20261108-125407 --secrets-file $localSecrets
```

El ensayo consultó `Id, Code, Stock, Price, Deleted` de `dbo.Drugs` ordenados por ID, el total de `dbo.Users` y un marcador en `dbo.Issue4Validation`. Se ejecutaron `BACKUP DATABASE`, `RESTORE VERIFYONLY`, `RESTORE FILELISTONLY`, `RESTORE DATABASE ... WITH MOVE` y `DBCC CHECKDB` según la [guía de recuperación](../../aiops-k8s-recovery.md). El archivo se transfirió en binario con `kubectl exec -- cat` a un archivo local y `kubectl exec -i` desde ese archivo al pod de restauración. El destino se creó en `pharmago-restore-test` y se detuvo el origen durante la restauración para liberar RAM.

Pasaron 21 pruebas de regresión. Se validó `docker compose config --quiet` para los dos archivos Compose, se inspeccionó el render sin objetos Secret ni NodePort y se validó contra el API server un PV nuevo fijado por hostname.
