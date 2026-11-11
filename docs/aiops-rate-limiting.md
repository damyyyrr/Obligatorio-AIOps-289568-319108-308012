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

Los contadores viven **en memoria de cada pod del Gateway**. Con N réplicas y balanceo uniforme, un mismo cliente obtiene hasta **N × límite** por ventana. Medido en Kubernetes: con 2 pods detrás del Service pasan 200 de 300; con 1 pod, 100.

### Decisión de escalado

**Se mantiene el Gateway con `replicas: 1`.** Así el límite en memoria funciona como un límite global, sin componentes nuevos. Se descartaron las otras opciones por lo que pide la letra:

| Opción | Decisión | Motivo |
|---|---|---|
| `sessionAffinity: ClientIP` en el Service | **Descartada (medido)** | kube-proxy la implementa con el módulo `recent` de iptables, que el kernel WSL2 de Docker Desktop no trae (`Extension recent is not supported`). Como kube-proxy aplica todas las reglas en una sola carga, esta falla deja sin red a **todos** los Services del clúster, no solo al Gateway: el Gateway y otro Service sin afinidad dejaron de responder hasta quitarla. Minikube con driver Docker comparte ese kernel. Pone en riesgo la disponibilidad del 100 % (R03). |
| Redis (`AddDistributedRateLimiting`) | Descartada | Agrega un componente con estado del que dependería **cada** solicitud. Si cae, el Gateway queda sin protección (fail-open) o rechaza tráfico (fail-closed, contra R03). Ese Redis necesitaría además su propia alta disponibilidad. El plan pide auditar y corregir lo existente antes de sumar sistemas. |
| Más réplicas con límites divididos | No se aplica ahora | Hoy no hace falta: un pod del Gateway aguanta la carga del obligatorio. Si en algún momento se escala, se ajusta por configuración sin tocar código: `IpRateLimiting__GeneralRules__N__Limit` y `RateLimiting__MaxRequestsPerMinute` divididos por la cantidad de réplicas. Es una aproximación, porque kube-proxy no reparte exactamente igual (146/154 en la prueba). |

**Efecto del rollout:** con `maxSurge: 1` conviven 2 pods del Gateway durante unos segundos y el pod nuevo arranca con los contadores vacíos. En esa ventana un cliente puede obtener hasta 2× el límite. Se acepta, porque es breve y prioriza la disponibilidad (R03) sobre la exactitud del contador.

**Acceso por `kubectl port-forward`:** el frontend llama a `http://127.0.0.1:5000` y el Gateway ve **127.0.0.1 para todos los usuarios**. En modo `IP` todos comparten un cupo de 100/min y 10 logins/min. Alcanza para la demo y la defensa. Se mantiene el modo `IP` porque es el único con regla propia contra fuerza bruta en `POST /api/login`. Si se publica el sistema detrás de un Ingress, hay que declarar el proxy confiable (ver abajo).

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
