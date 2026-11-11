# Timeouts y resiliencia entre servicios (RES-03, issue #10)

## Inventario de dependencias

| Llamada | Mecanismo | Operaciones | Antes | Ahora |
|---|---|---|---|---|
| Cliente → Gateway | Service ClusterIP | todas | Gateway **NotReady** si caían Users y Pharmacy: sin endpoints, los clientes quedaban reintentando la conexión TCP (15/31/63 s) | Gateway sigue Ready después de alcanzar los upstreams por primera vez |
| Gateway → Users / Pharmacy | YARP | GET, POST, PUT, DELETE | Espera por solicitud de **100 s** (valor por defecto de YARP) y conexión sin límite propio | `ActivityTimeout` **10 s** por cluster y `ConnectTimeout` **2 s** |
| Users / Pharmacy → SQL Server | EF Core / SqlClient | lecturas y escrituras | Conexión **15 s**, comando **30 s** y pool bloqueado hasta 1 min después de un fallo | Conexión **5 s**, comando **8 s** y `PoolBlockingPeriod=NeverBlock` |
| Users ↔ Pharmacy | `PharmacyServiceClient` / `UsersServiceClient` | GET por id | Registrados, con timeout de 30 s, **sin uso en el código** | Timeout de 5 s; si se empiezan a usar, solo para lecturas |
| Job de migraciones → SQL | EF Core | DDL | Comando de 30 s | 10 min, independiente del límite de la aplicación |

**Escrituras no idempotentes:** aprobar o rechazar compras (`PUT` en `/api/purchases`), solicitudes de stock, alta y edición de medicamentos, invitaciones y login (que crea sesión). Ninguna lleva clave de idempotencia.

## Políticas

- **Timeouts escalonados:** conexión SQL 5 s < comando SQL 8 s < Gateway 10 s. El servicio contesta su propio 500 antes de que el Gateway corte con 504, y el Gateway corta antes que cualquier cliente razonable. Los valores se pueden configurar: `Database:ConnectTimeoutSeconds`, `Database:CommandTimeoutSeconds`, `Gateway:UpstreamConnectTimeoutSeconds` y `ReverseProxy:Clusters:*:HttpRequest:ActivityTimeout`.
- **Sin reintentos** en el Gateway ni en SQL (`EnableRetryOnFailure` sigue apagado). Un reintento automático puede duplicar compras o cambios de stock. En las lecturas, el beneficio no compensa el riesgo de multiplicar la carga sobre una dependencia que ya está degradada. Si hace falta reintentar, lo hace el usuario o el frontend sobre un GET.
- **Sin circuit breaker:** hay un solo destino por cluster (el Service de Kubernetes) y la readiness ya actúa como corte. Kubernetes saca de los endpoints al pod que no puede llegar a SQL en ≤ 5 s, y el Gateway responde 502 en ≤ 2 s. Un breaker en proceso duplicaría esa función y sumaría un estado por pod.
- **Readiness del Gateway:** sin upstreams listos, el Gateway solo queda NotReady **hasta alcanzarlos por primera vez**. Eso protege el arranque y el rollout (#8): un pod nuevo no recibe tráfico antes de poder reenviarlo. Después responde `Degraded` (HTTP 200) aunque caigan los upstreams. Hay un único Gateway: sacarlo del Service no deriva el tráfico a ningún lado y deja a los clientes colgados. Users y Pharmacy mantienen su readiness contra SQL (#7).

Evidencia: [issue-10-20261111](evidence/issue-10-20261111/README.md).
