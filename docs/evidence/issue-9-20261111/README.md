# Issue #9 — auditoría y prueba del rate limiting

Ensayo del **11/11/2026** en la rama `feature/issue-9-rate-limiting`, creada desde `obligatorio` (`9862903`). Se compiló el Gateway de `obligatorio` sin cambios (**antes**) y el de la rama (**después**) con `dotnet publish -c Release` (SDK 10.0.401, target `net6.0`, ejecutado con `DOTNET_ROLL_FORWARD=Major` sobre ASP.NET Core 10). Cada escenario usó un proceso nuevo del Gateway, con contadores vacíos, en `ASPNETCORE_ENVIRONMENT=Production`. Como upstream se usó un servidor HTTP local que responde 404 al instante: cualquier código distinto de 429 indica que la solicitud **atravesó el limitador**. Todas las solicitudes salieron de una única IP real (127.0.0.1). Política resultante: [aiops-rate-limiting.md](../../aiops-rate-limiting.md). Datos: [results.json](results.json).

La parte multipod se probó primero con dos procesos locales en round-robin y después **en Kubernetes** con la imagen Docker real. Ver [Kubernetes multipod](#kubernetes-multipod).

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

## Kubernetes multipod

Entorno: Docker Desktop 29.0.1 con Kubernetes v1.34.1, un nodo (kubeadm). La imagen se construyó desde el commit de esta rama con el Dockerfile del Gateway: `pharmago-api-gateway:issue9-ratelimit-20261111`, ID `sha256:05be0aa9acf5`, 318 MB.

Se usó el manifiesto aislado [rate-limit-multipod.yaml](../../../Implementacion%20K8S/Codigo/k8s/tests/rate-limit-multipod.yaml), con namespace propio `pharmago-ratelimit-test`, eliminado al terminar. El despliegue `pharmago` no se tocó. Contiene:

- el Gateway;
- un nginx como upstream: 200 en `/health/ready` y 404 en el resto;
- un pod cliente que llama al **Service ClusterIP** `gateway`, con la IP del pod intacta.

Antes de cada corrida se reinició el Deployment para empezar con contadores vacíos. Datos: [k8s-results.json](k8s-results.json).

**Intentos de evasión con 1 pod, modo IP:** sin headers, `X-Real-IP` rotado, `X-Forwarded-For` rotado y rutas distintas dieron todos **100 pasan / 50 reciben 429**. Login: 10 / 20. Coincide con la prueba local.

**Réplicas:** 300 solicitudes por el Service, iniciadas al comienzo de un minuto.

| Modo | Pods | Atravesaron | 429 | 429 por pod (logs) |
|---|---:|---:|---:|---|
| IP | 1 | 100 | 200 | 200 |
| IP | 2 | **200** | 100 | 46 + 54 |
| User | 1 | 100 | 200 | 200 |
| User | 2 | **200** | 100 | 50 + 50 |

kube-proxy repartió las conexiones (146/154 y 150/150) y cada pod aplicó su propio límite de 100. Queda confirmado en el clúster que el límite es **local a cada pod**.

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

Para Kubernetes, construir la imagen con `docker build -f PharmaGo.ApiGateway/Dockerfile -t pharmago-api-gateway:issue9-ratelimit-20261111 .` y luego:

```bash
kubectl apply -f "Implementacion K8S/Codigo/k8s/tests/rate-limit-multipod.yaml"
kubectl -n pharmago-ratelimit-test cp probe-rate-limit-replicas.py client:/tmp/
kubectl -n pharmago-ratelimit-test scale deploy/gateway --replicas=2
kubectl -n pharmago-ratelimit-test exec client -- python /tmp/probe-rate-limit-replicas.py --base http://gateway --count 300 --out /tmp/r.json
kubectl delete namespace pharmago-ratelimit-test
```

## Pendiente para cerrar el issue

- [x] Repetir la tabla de réplicas en el clúster con 2 pods detrás del Service (hecho en Docker Desktop).
- [ ] Definir con el equipo si se mantiene `replicas: 1` (límite global de hecho) o si se adopta afinidad o Redis al escalar.
