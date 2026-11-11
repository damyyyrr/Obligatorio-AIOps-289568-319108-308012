# Rate limiting del API Gateway — política (RES-02, issue #9)

Se conserva el mecanismo existente: **AspNetCoreRateLimit** en modo `IP` (por defecto) y `UserRateLimitMiddleware` en modo `User`. No se agregó un tercer mecanismo. Se seleccionan con `RateLimiting:Mode` (`IP`, `User` o `Disabled`). Los endpoints de health (`/health/*`) y `/metrics` quedan excluidos.

## Identidad del cliente

| Fuente | ¿Se usa? | Motivo |
|---|---|---|
| IP de la conexión TCP (`RemoteIpAddress`) | **Sí** | No la controla el cliente. |
| `X-Forwarded-For` / `X-Forwarded-Proto` | Solo desde un proxy declarado en `RateLimiting:TrustedProxies` o `TrustedNetworks` | Sin proxy declarado, `UseForwardedHeaders` **no se registra**: con listas vacías ASP.NET Core confía en cualquier origen y `kubectl port-forward` entra por loopback. |
| `X-Real-IP` | **No** | AspNetCoreRateLimit lo lee por defecto aunque no figure en la configuración; `GatewayRateLimitConfiguration` registra solo el resolvedor de conexión. |
| `X-User-Id` | **No** | Lo elige el cliente. |
| `Authorization` (modo `User`) | Sí, **valor completo hasheado** (SHA-256, 16 hex) | Antes se usaban los 8 primeros caracteres. No se guarda ni se registra el token en claro. El Gateway no valida el token; por eso existe además el techo por IP. |

## Límites

**Modo `IP`** (`appsettings.json` → `IpRateLimiting`), contados por regla y no por ruta concreta (`EndpointCounterKeyBuilder`):

- `POST:/api/login`: 10/min por IP.
- `*`: 100/min y 1000/h por IP, **en total** entre todas las rutas. Antes cada ruta distinta (`/api/drug/1`, `/api/drug/2`, …) tenía su propio cupo.

**Modo `User`** (`RateLimiting`):

- Por sesión (o por IP si no hay token): `MaxRequestsPerMinute` 100 y `MaxRequestsPerHour` 1000.
- Techo agregado por IP para toda solicitud: `IpMaxRequestsPerMinute` 300 y `IpMaxRequestsPerHour` 3000. Limita la rotación de tokens inventados y permite varios usuarios legítimos detrás de una misma IP.
- Comprobación e incremento atómicos (un lock): una ráfaga concurrente no supera el límite. Las solicitudes rechazadas no consumen cupo.

Ambos modos responden **429** con `Retry-After`. El modo `User` agrega además `X-RateLimit-Reason` y un cuerpo JSON.

## Límite local, no global

Los contadores viven **en memoria de cada pod del Gateway**. Con N réplicas y balanceo uniforme, un mismo cliente obtiene hasta **N × límite** por ventana (medido: 2 réplicas → 200 de 300 en lugar de 100). Hoy el Gateway corre con `replicas: 1`, así que en la práctica el límite es global. Si se escala el Gateway hay que elegir una de estas opciones:

1. dividir los límites por la cantidad de réplicas (aproximado, depende del balanceo);
2. usar afinidad por IP en el Service (`sessionAffinity: ClientIP`);
3. usar un almacén distribuido (Redis, `AddDistributedRateLimiting`) para tener un límite global real.

Las ventanas son **fijas**: en el cambio de minuto un cliente puede concentrar hasta 2 × límite en pocos segundos. Se observó una vez: 450 tokens rotados aceptados en 6 s que cruzaron el minuto, frente a 300 dentro de un mismo minuto. Se acepta para este alcance.

## Detrás de un proxy o Ingress

Si se agrega un Ingress o LoadBalancer que haga SNAT, todas las solicitudes llegarán con la IP del proxy y compartirán el cupo. En ese caso hay que declarar la IP o red del proxy:

```yaml
env:
- name: RateLimiting__TrustedNetworks__0
  value: "10.244.0.0/16"   # ejemplo: red de pods del controlador Ingress
```

Con eso el Gateway toma la IP del cliente del último salto de `X-Forwarded-For` (`ForwardLimit = 1`), agregado por ese proxy.

Evidencia: [issue-9-20261111](evidence/issue-9-20261111/README.md).
