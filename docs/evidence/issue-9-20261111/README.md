# Issue #9 — auditoría y prueba del rate limiting

Ensayo del **11/11/2026** en la rama `feature/issue-9-rate-limiting`, creada desde `obligatorio` (`9862903`). Se compiló el Gateway de `obligatorio` sin cambios (**antes**) y el de la rama (**después**) con `dotnet publish -c Release` (SDK 10.0.401, target `net6.0`, ejecutado con `DOTNET_ROLL_FORWARD=Major` sobre ASP.NET Core 10). Cada escenario usó un proceso nuevo del Gateway, con contadores vacíos, en `ASPNETCORE_ENVIRONMENT=Production`. Como upstream se usó un servidor HTTP local que responde 404 al instante: cualquier código distinto de 429 indica que la solicitud **atravesó el limitador**. Todas las solicitudes salieron de una única IP real (127.0.0.1). Política resultante: [aiops-rate-limiting.md](../../aiops-rate-limiting.md). Datos: [results.json](results.json).

**No se ejecutó en Kubernetes**: Docker Desktop no estaba activo en esta máquina. La parte multipod se simuló con dos procesos del Gateway en round-robin; falta repetirla con `kubectl scale deploy/pharmago-api-gateway --replicas=2` (ver pendientes).

## Intentos de evasión (150 solicitudes salvo que se indique)

| Modo | Escenario | Antes: atravesaron / 429 | Después: atravesaron / 429 |
|---|---|---:|---:|
| IP | Sin headers (referencia) | 100 / 50 | 100 / 50 |
| IP | `X-Real-IP` rotado | **150 / 0** — bypass | 100 / 50 |
| IP | `X-Forwarded-For` rotado | 100 / 50 | 100 / 50 |
| IP | Rutas distintas `/api/drug/{i}` | **150 / 0** — bypass | 100 / 50 |
| IP | Login, 30 `POST /api/login` | 10 / 20 | 10 / 20 |
| User | Sin headers (referencia) | 100 / 50 | 100 / 50 |
| User | `X-Forwarded-For` rotado | **150 / 0** — bypass | 100 / 50 |
| User | `X-User-Id` rotado | **150 / 0** — bypass | 100 / 50 |
| User | 450 tokens aleatorios | **450 / 0** — bypass | 300 / 150 (techo por IP) |
| User | Rutas distintas | 100 / 50 | 100 / 50 |
| User | Ráfaga concurrente de 200, un token, 50 hilos | **106** / 94 — carrera | **100** / 100 |
| IP, proxy 127.0.0.1 declarado | `X-Forwarded-For` rotado | — | 150 / 0 (esperado: proxy confiable) |
| User, proxy 127.0.0.1 declarado | `X-Forwarded-For` rotado | — | 150 / 0 (esperado) |

Las dos últimas filas prueban que la configuración `RateLimiting:TrustedProxies` sí habilita la IP reenviada cuando el proxy está declarado.

Durante la corrección se detectaron dos fallas de la primera versión del arreglo, que quedaron documentadas:

1. Con `KnownProxies` y `KnownNetworks` vacíos, `ForwardedHeadersMiddleware` acepta `X-Forwarded-For` de cualquier origen (150/0).
2. AspNetCoreRateLimit sigue leyendo `X-Real-IP` aunque se quite `RealIpHeader` del JSON (150/0).

Ambas se corrigieron y se cubrieron con pruebas unitarias.

La corrida de tokens aleatorios del "después" se repitió dentro de un único minuto. La primera vez cruzó el cambio de ventana y aceptó 450: es el efecto de borde de la ventana fija, documentado en la política.

## Usuarios legítimos

- Un cliente por debajo del límite no recibe ningún 429. En todas las referencias, las primeras 100 solicitudes pasaron.
- Las pruebas unitarias cubren dos usuarios con tokens distintos detrás de la misma IP: ambos conservan su propio cupo de 5/5 con límites reducidos. También cubren tokens con el mismo prefijo, que antes compartían cupo.
- El 429 trae `Retry-After` con los segundos hasta el fin de la ventana (55–59 s en las ráfagas iniciadas a comienzo de minuto).

## Réplicas: límite local frente a global

Fueron 300 solicitudes del mismo cliente, iniciadas al comienzo de un minuto:

| Modo | Réplicas | Atravesaron | 429 | Por réplica |
|---|---:|---:|---:|---|
| IP | 1 | 100 | 200 | 100 |
| IP | 2 | **200** | 100 | 100 + 100 |
| User | 1 | 100 | 200 | 100 |
| User | 2 | **200** | 100 | 100 + 100 |

El contador es **por instancia**. El Gateway del clúster corre con `replicas: 1`, así que el límite efectivo hoy es global. Escalarlo multiplica el cupo; las opciones están en la política.

## Validaciones

- **Gateway: 15/15 pruebas** (`PharmaGo.ApiGateway.Test`, proyecto nuevo agregado a `PharmaGo.sln`).
- **Solución: 290/291 en `PharmaGo.Test`**. Es la misma falla preexistente de `PurchasesDetailRepositoryTest.Test_GetOneByExpression` documentada en el issue #8; no se relaciona con este cambio.
- La evidencia no contiene tokens ni cuerpos HTTP: los tokens aleatorios no se guardan y las URLs de réplica están anonimizadas.

## Reproducción

Desde `Implementacion K8S/Codigo/Backend`:

```bash
DOTNET_ROLL_FORWARD=Major dotnet test PharmaGo.ApiGateway.Test/PharmaGo.ApiGateway.Test.csproj
dotnet publish PharmaGo.ApiGateway/PharmaGo.ApiGateway.csproj -c Release -o out/gw
```

Para cada escenario, iniciar un Gateway limpio con el upstream apuntando a un servidor local:

```bash
cd out/gw
env ASPNETCORE_ENVIRONMENT=Production ASPNETCORE_URLS=http://127.0.0.1:5099 RateLimiting__Mode=IP \
  "ReverseProxy__Clusters__pharmacy-cluster__Destinations__destination1__Address=http://127.0.0.1:5098" \
  "ReverseProxy__Clusters__users-cluster__Destinations__destination1__Address=http://127.0.0.1:5098" \
  dotnet PharmaGo.ApiGateway.dll
python ../../../scripts/probe-rate-limit.py --base http://127.0.0.1:5099 --mode IP --scenario spoof_x_real_ip_rotating --out r.json
python ../../../scripts/probe-rate-limit-replicas.py --base http://127.0.0.1:5099 --base http://127.0.0.1:5100 --count 300 --out rep.json
```

## Pendiente para cerrar el issue

- [ ] Repetir la tabla de réplicas en el clúster: `kubectl -n pharmago scale deploy/pharmago-api-gateway --replicas=2` y lanzar el sondeo desde un pod del clúster contra el Service. Con ClusterIP, kube-proxy reparte las conexiones; el resultado esperado es más de 100 y como máximo 200.
- [ ] Definir con el equipo si se mantiene `replicas: 1` (límite global de hecho) o si se adopta afinidad o Redis al escalar.
