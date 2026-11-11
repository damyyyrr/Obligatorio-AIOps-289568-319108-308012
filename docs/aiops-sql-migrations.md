# Migraciones de SQL Server y rollback de PharmaGo

## Qué cambia

Users ejecutaba `Database.Migrate()` al arrancar. Cada réplica repetía la llamada y EF Core 6 no serializa las migraciones de varios procesos. Users y Pharmacy comparten `PharmaDb`. En Kubernetes, `manage.py apply` espera a SQL, crea un Job con la imagen de Users de la versión a desplegar y espera su finalización antes de aplicar los Deployments de aplicación. El Job recibe la conexión desde el mismo Secret y ejecuta `--migrate`. Los procesos HTTP de Users solo sirven la aplicación. Compose usa un servicio de ejecución única y espera su salida exitosa antes de arrancar Users y Pharmacy. [Migraciones en EF Core](https://learn.microsoft.com/en-us/ef/core/managing-schemas/migrations/applying) · [Jobs de Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

El comando toma un bloqueo exclusivo `PharmaGo.SchemaMigration` de SQL Server en `master`, que existe incluso en una instalación nueva. Conserva la misma sesión para aplicar el esquema de la base destino y libera el bloqueo al cerrar la conexión. Los comandos de migración de una instancia SQL se serializan aunque se creen varios Jobs. El bloqueo espera hasta 120 segundos. La aplicación conserva la credencial SQL del entorno actual y el Job reutiliza el Secret de la #4. [Bloqueos de aplicación de SQL Server](https://learn.microsoft.com/en-us/sql/relational-databases/system-stored-procedures/sp-getapplock-transact-sql)

El comando comprueba que el historial sea un prefijo ordenado de las migraciones compiladas. Una repetición con el esquema al día termina con cero migraciones pendientes. Un historial que la imagen desconoce, un error o un timeout detienen el despliegue antes de actualizar los consumidores. El Job conserva su nombre en el reporte y queda disponible para diagnóstico durante una hora después de terminar. El despliegue de WebApi monolítico tiene su flujo propio. No arrancarlo sobre la misma base mientras se ejecuta este procedimiento.

## Arranque y diagnóstico

En Kubernetes, usar el apply de la [guía de despliegue](../Implementacion%20K8S/Codigo/k8s/README-k8s.md) y la imagen de Users compilada con este flujo. Si falla, consultar el Job y corregir la causa antes de repetir:

```powershell
$ctx = '<contexto>'
kubectl --context $ctx -n pharmago get jobs
kubectl --context $ctx -n pharmago logs job/<nombre-del-job>
```

En Compose, construir Users antes de un arranque con `--no-build`. El script `start-baseline.ps1` ya construye esa imagen cuando se ejecuta normalmente. Para correr la migración por separado con la imagen de Users disponible y el `.env` local, usar `docker compose up -d pharmago-db-migrate` y luego `docker compose wait pharmago-db-migrate`. Para ejecutar Users fuera de contenedores contra una base vacía, configurar `ConnectionStrings__DefaultConnection` y ejecutar `dotnet run --project PharmaGo.UsersService -- --migrate` desde `Backend` antes de arrancar la API.

## Compatibilidad y rollback

La #5 conserva las migraciones históricas de EF Core y el esquema. Al pasar desde una versión que migraba al arranque, comprobar que la base existente tenga el historial completo de esa versión. Si tiene migraciones pendientes, coordinar una ventana, detener los procesos antiguos que podrían migrar y revisar el cambio antes de aplicar la nueva versión.

Para versiones futuras, agregar primero cambios compatibles con ambas versiones, como columnas opcionales. Probar el código anterior y el nuevo con ese esquema. Completar los datos nuevos sin romper a los consumidores anteriores. Quitar columnas o cambiar su significado en una entrega posterior, una vez cerrada la ventana de rollback. Revisar el SQL de cualquier migración nueva, conservar un [backup comprobado](aiops-k8s-recovery.md) y coordinar un release a la vez. El bloqueo serializa los cambios de esquema y la coordinación del release evita que dos versiones compitan por los mismos Deployments.

Ante un problema de aplicación, volver a una revisión compatible del Deployment. Mantener el esquema y comprobar login, catálogo y registros. El rollback de aplicación se puede verificar sin ejecutar migraciones `Down`:

```powershell
kubectl --context $ctx -n pharmago rollout history deployment/pharmago-users-service
kubectl --context $ctx -n pharmago rollout undo deployment/pharmago-users-service --to-revision=<revision-compatible>
kubectl --context $ctx -n pharmago rollout status deployment/pharmago-users-service
```

Si el esquema ya es incompatible con esa revisión, corregir hacia adelante o planificar la recuperación con un respaldo en un volumen separado. En la primera transición, la versión anterior todavía ejecuta `Migrate()` al arrancar. Usarla para rollback únicamente con su historial al día y con una réplica, como en el ensayo.

## Disponibilidad de SQL y Q02

**Pendiente al 11/11/2026: el reemplazo de SQL Server sin interrupción no está implementado ni demostrado. R03 completo sigue sin cumplirse.**

La letra, en «Despliegues seguros» (5 puntos), exige: «El sistema debe poder reemplazar sus componentes garantizando 100% de disponibilidad.» y «Se necesita documentar y explicar la técnica elegida.». Ese apartado no enumera los componentes ni excluye SQL. La [consulta Q02](aiops-open-questions.md) es una aclaración solicitada por el equipo, sin respuesta docente registrada; mientras tanto se conserva SQL dentro del alcance de trabajo. Su limitación técnica actual no constituye una excepción al requisito.

SQL Server 2019 Express sigue con una réplica, un volumen local y estrategia `Recreate`, como declara `k8s/deployments/ops/db-deployment.yaml`. Al reemplazar ese pod se retira la instancia anterior antes de disponer de la nueva. Retain, el respaldo y el Job de migración protegen datos y orden de despliegue; la continuidad del servicio SQL durante ese reemplazo queda pendiente.

| Trabajo | Resultado demostrado | Pendiente de disponibilidad |
|---|---|---|
| [#5 — migraciones y alcance SQL](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/5) | Migraciones serializadas, esquema compatible, persistencia y rollback funcional de Users tras estabilizar sus endpoints. El primer recambio tuvo un 502, conservado en la [evidencia](evidence/issue-5-20261109/README.md). | El pod SQL no fue reemplazado durante ese ensayo. La tarea de resolver el alcance Q02 sigue pendiente, aunque la issue figure cerrada. |
| [#8 — rollout y rollback](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/8) | 226/226 solicitudes válidas durante 282,139 s al actualizar y revertir Gateway, Users y Pharmacy, con SQL estable. [Evidencia](evidence/issue-8-20261111/README.md). | No se reemplazaron SQL, frontend ni observabilidad durante la ventana medida. El resultado de los tres procesos no acredita R03 completo. |

El cierre administrativo de #5 o #8 no da por resuelto este pendiente. Para acreditar el reemplazo de SQL hacen falta una solución implementada y una prueba funcional por Gateway que acceda a DB antes, durante y después del reemplazo y de la recuperación o reversión prevista. Registrar todos los intentos, códigos HTTP, timeouts, validación de datos y latencias; conservar evidencia de continuidad y persistencia. No basta comprobar que SQL vuelve a Ready o que conserva sus datos después de reiniciar. Frontend y observabilidad también conservan su validación pendiente conforme al alcance general de componentes.

Para cubrir SQL hay que evaluar una solución viable para la edición y los recursos disponibles. Express carece de grupos de disponibilidad Always On. Una opción a evaluar es SQL Server Standard con un grupo básico para `PharmaDb`, dos instancias con almacenamiento independiente y un punto de conexión común. En Linux, el failover automático requiere Pacemaker, quórum, fencing y una réplica de configuración. Harían falta máquinas y almacenamiento con capacidad separada, licencia o infraestructura autorizada y pruebas de reconexión con tráfico real. Un grupo básico por sí solo no acredita 100 % de disponibilidad. [Ediciones de SQL Server 2019](https://learn.microsoft.com/en-us/sql/sql-server/editions-and-components-of-sql-server-2019?view=sql-server-ver17) · [Grupos de disponibilidad en Linux](https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-availability-group-overview)
