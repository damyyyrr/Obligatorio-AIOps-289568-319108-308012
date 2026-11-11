# Issue #5 — migraciones y rollback de aplicación

**Aclaración de alcance del 11/11/2026:** la issue #5 figura cerrada, pero su ensayo no acredita reemplazo de SQL sin interrupción y Q02 sigue sin respuesta docente registrada. SQL mantuvo el mismo pod; el 502 del recambio de Users se conserva como fallo observado. La #8 verificó después el rollout de aplicación con SQL estable. El [pendiente SQL de R03](../../aiops-sql-migrations.md#disponibilidad-de-sql-y-q02) continúa sin implementar ni probar, independientemente del cierre de estas issues.

Ensayo del 09/11/2026 en `feature/issue-5-migraciones-sql` sobre `525c458` de `obligatorio`. Se reutilizó el perfil local de la #3, con los datos de la #4. Minikube 1.39.0, Kubernetes y kubectl 1.34.1, Docker Engine 29.0.1, containerd 2.3.4, SQL Server 2019 Express y EF Core 6.0.8.

El Job de despliegue terminó con cero migraciones pendientes sobre `PharmaDb`. En una base de ensayo separada se ejecutaron dos Jobs con el mismo esquema inicial. Ambos esperaron un bloqueo tomado desde una sesión SQL de prueba. Al liberarlo, un Job aplicó las diez migraciones y el otro encontró cero pendientes. La base de ensayo quedó con diez entradas únicas en el historial. Una prueba adicional agregó temporalmente un ID de migración desconocido al historial de otra base de ensayo. El Job falló antes de modificar ese historial y se retiró la fila sintética. Ver [control de historial](history-guard.json).

## Resultado del escalado y rollback

| Etapa | Resultado |
|---|---|
| Release con Job separado | Imagen nueva de Users activa y cero migraciones pendientes en la base existente. |
| Escalado y RollingUpdate | Dos réplicas Ready. Se reemplazaron las dos y se verificaron catálogo y login con HTTP 200 después de estabilizar sus endpoints. |
| Rollback a la imagen anterior | Una réplica Ready. Tras estabilizar sus endpoints, el catálogo devolvió los cuatro medicamentos y el login dio HTTP 200. |
| Regreso a la imagen nueva | Una réplica Ready. Catálogo y login HTTP 200. El UID del pod SQL, los cuatro pares PV/PVC y el hash de la consulta de historial y registros fueron iguales en todas las etapas comparadas. |

En el primer intento, el login dio HTTP 502 durante el recambio. El gateway registró `Connection refused` hacia Users y el login dio 200 al quedar estable el endpoint. Se conserva esa observación en [proof.json](proof.json). El ensayo mide compatibilidad de esquema y recuperación funcional tras el rollback. La continuidad durante el cambio con tráfico se evalúa en #8 y el alcance de SQL queda en Q02.

Pasaron 23 pruebas de regresión, la construcción de la imagen de Users y `docker compose config --quiet` para los dos archivos Compose. En un proyecto Compose aislado se levantaron SQL y el servicio de migración del baseline con un volumen vacío. `docker compose wait pharmago-db-migrate` devolvió 0 después de aplicar las diez migraciones. Se retiraron los recursos del proyecto de ensayo. Ver [resultado Compose](compose-proof.json).

## Reproducción

Construir y cargar la imagen con el flujo de la [guía Kubernetes](../../../Implementacion%20K8S/Codigo/k8s/README-k8s.md). Para el ensayo se reconstruyó Users con el tag `issue5-migrations-20261109` y se etiquetaron con ese mismo tag las imágenes de Gateway, Pharmacy y UI de la prueba anterior, cuyo código no cambió.

```powershell
$ctx = 'pharmago-issue3'
$k8s = 'Implementacion K8S/Codigo/k8s'
$py = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
& $py -m unittest discover -s $k8s
& $py "$k8s/manage.py" apply --context $ctx --image-tag issue5-migrations-20261109 --secrets-file .runtime/issue4-upgrade-secrets.local.json --output .runtime/issue5-apply.json
$job = (Get-Content .runtime/issue5-apply.json -Raw | ConvertFrom-Json).migrationJob
kubectl --context $ctx -n pharmago logs "job/$job"
kubectl --context $ctx -n pharmago rollout history deployment/pharmago-users-service
kubectl --context $ctx -n pharmago scale deployment/pharmago-users-service --replicas=2
kubectl --context $ctx -n pharmago rollout restart deployment/pharmago-users-service
kubectl --context $ctx -n pharmago rollout status deployment/pharmago-users-service
```

Para el ensayo de concurrencia, crear un namespace de prueba con un Secret `db-secret` que contenga `CONNECTION_STRING` apuntando a una base nueva en el SQL de ensayo. Crear dos Jobs usando `migration_job` de `manage.py`, con esa imagen, el argumento `--migrate` y el selector del nodo Users. En una sesión de SQL en `master`, tomar temporalmente `sp_getapplock` en modo Exclusive y con propietario Session sobre `PharmaGo.SchemaMigration`. Crear los dos Jobs mientras se mantiene la sesión y comprobar en los logs que ambos esperan. Al cerrarla, consultar `kubectl logs job/<job>` y `SELECT COUNT(*) FROM dbo.__EFMigrationsHistory` en la base nueva.

Para el rollback, volver a una réplica, elegir la revisión anterior con `rollout history` y ejecutar `rollout undo` según la [guía de migraciones](../../aiops-sql-migrations.md). Comparar el UID del pod SQL y los cuatro pares PV/PVC. Comparar también el historial de EF, los campos de los cuatro medicamentos, el total de tres usuarios y el marcador de la #4. Para las pruebas funcionales usar el port-forward del Gateway y consultar catálogo y login. Se conservaron únicamente estados HTTP, conteos, nombres y hashes.

Para la prueba Compose, usar un nombre de proyecto aislado y el archivo `compose.baseline.yaml` con credenciales locales nuevas. Se usó un override local para elegir las imágenes ya disponibles y omitir el puerto de SQL. Ejecutar `docker compose up -d --no-build pharmago-db-migrate`, `docker compose wait pharmago-db-migrate` y `docker compose logs pharmago-db-migrate` en ese proyecto.
