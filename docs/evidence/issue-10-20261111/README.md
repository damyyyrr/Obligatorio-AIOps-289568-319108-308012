# Issue #10 — timeouts y contención de fallas entre servicios

Ensayo del **11/11/2026** en Docker Desktop 29.0.1 con Kubernetes v1.34.1 (un nodo). Rama `feature/issue-10-timeouts-resiliencia`. Política resultante: [aiops-interservice-resilience.md](../../aiops-interservice-resilience.md). Datos por fase: [summary.json](summary.json).

## Entorno

- Namespace aislado `pharmago-resilience-test` ([manifiesto](../../../Implementacion%20K8S/Codigo/k8s/tests/interservice-resilience.yaml)), eliminado al terminar. El despliegue `pharmago` no se tocó.
- Componentes: SQL Server Express con el mismo digest que producción y PVC; Job de migración (10 migraciones); Users, Pharmacy y Gateway con los probes de los manifiestos reales; un pod cliente.
- La contraseña SA se generó al azar para la corrida y no se guardó.
- Rate limiting desactivado en este Gateway de prueba: la carga supera los 100/min de un único cliente.

Imágenes construidas con los Dockerfiles de cada servicio:

| Versión | Commit | Gateway | Users | Pharmacy |
|---|---|---|---|---|
| **antes** | `obligatorio` `acfb9ce` | `c8395995fa35` | `06257f40736a` | `6e0aa51b0feb` |
| **después** | rama `1572993` | `0bb932cceefc` | `662fe337c86a` | `677b9bd078c0` |

**Carga:** [probe-resilience.py](../../../Implementacion%20K8S/Codigo/scripts/probe-resilience.py), desde el pod cliente hacia el Service del Gateway.

- 4 solicitudes/s alternando `GET /api/drug` (Pharmacy → SQL) y `GET /api/roles` (Users → SQL).
- Cada solicitud corre en su propio hilo, así las colgadas no frenan el ritmo de envío.
- El cliente espera hasta 120 s por solicitud. Solo se envían GET y el generador no reintenta.

**Escenarios:** 20 s normales, falla, restauración y medición hasta completar 100 s (150 s en SQL caída).

1. **SQL colgada:** `docker pause` del contenedor de SQL durante 25 s.
2. **Pharmacy colgado:** `docker pause` del contenedor de Pharmacy durante 18 s, por debajo de la ventana de liveness para medir el timeout y no un reinicio.
3. **SQL caída:** `kubectl scale deploy/pharmago-db --replicas=0` durante 40 s y vuelta a 1.

## Resultados (solicitudes iniciadas durante la falla)

| Escenario | Ruta | Antes: espera máxima | Después: espera máxima | Después: respuestas |
|---|---|---:|---:|---|
| SQL colgada | `/api/drug` | 32,4 s | **10,0 s** | 30×500, 6×502, 4×504, 11×200 |
| SQL colgada | `/api/roles` | 32,5 s | **9,7 s** | 29×500, 11×502, 1×504, 11×200 |
| Pharmacy colgado | `/api/drug` | 18,0 s (la falla entera) | **10,0 s** | 20×504, 14×502, 3×200 |
| Pharmacy colgado | `/api/roles` | 0,26 s | 0,51 s | 37×200: Users no se ve afectado |
| SQL caída | `/api/drug` | **120 s** (cortó el cliente) | **10,0 s** | 72×500, 5×502, 2×504, 1×200 |
| SQL caída | `/api/roles` | **120 s** (cortó el cliente) | **10,0 s** | 31×504, 28×500, 21×502, 1×200 |

En "antes", muchas de las solicitudes lentas terminaban en 200, pero recién cuando volvía la dependencia: quedaban esperando la conexión con el Gateway.

**Impacto en recursos** (solicitudes simultáneas en vuelo y segundos de espera acumulados en el cliente):

| Escenario | Antes | Después |
|---|---|---|
| SQL colgada | 58 en vuelo, 1.192 s | 26 en vuelo, 479 s |
| Pharmacy colgado | 21 en vuelo, 219 s | 15 en vuelo, 150 s |
| SQL caída | **205** en vuelo, 9.623 s | **28** en vuelo, 1.094 s |

## Hallazgo intermedio: el Gateway se escondía

Una primera versión de la rama (`9b84557`, tag `issue10-after`) traía solo los timeouts. Con ella, Pharmacy colgado ya cortaba a los 10,4 s, pero con SQL colgada o caída seguían apareciendo esperas de 32 y 65 s, que terminaban en 200.

Esos tiempos (15, 31 y 63 s) son los reintentos de SYN de TCP. Cuando caían los dos upstreams, el Gateway pasaba a NotReady y quedaba fuera del Service. En este clúster, el SYN a un Service sin endpoints se descarta en vez de rechazarse, y el cliente reintentaba hasta que todo volvía.

La versión final mantiene el Gateway Ready después de su primer contacto con los upstreams y limita su conexión a 2 s. Con eso, todas las solicitudes del cliente llegaron al Gateway: `gateway_proxied` = solicitudes enviadas en los tres escenarios (401/401/601). Antes, en SQL caída, llegaron 516 de 601.

## Sin reintentos ni duplicación

En la versión final, cada solicitud del cliente generó **exactamente un** reenvío del Gateway: las líneas `Proxying to` coinciden con las solicitudes enviadas. No hay reintentos automáticos en el Gateway ni en EF/SqlClient: `EnableRetryOnFailure` sigue apagado y `ConnectRetryCount` mantiene su valor por defecto, que solo reabre conexiones ociosas antes de enviar el comando. Por eso una escritura no puede duplicarse por un reintento de la plataforma.

## Recuperación y reinicios

- Al restaurar la dependencia, la primera respuesta 200 llegó en menos de 1 s en los escenarios de pausa, en las dos versiones.
- En SQL caída, la base tardó unos 23 s en quedar Ready (arranque de SQL Server). Las rutas se estabilizaron entre 1 y 8 s después en las dos versiones. La señal de Ready de SQL se revisa cada 10 s, así que esta medición no alcanza para atribuir una mejora al cambio de `PoolBlockingPeriod`.
- Ningún pod se reinició en la versión final. El reinicio de Pharmacy que figura en "antes" viene de una corrida descartada, con 25 s de pausa, que superó la ventana de liveness.

## Validaciones

- `PharmaGo.ApiGateway.Test`: **21/21**. Incluye los timeouts por cluster y las decisiones de readiness.
- `PharmaGo.Test`: **295/296**. Suma 5 pruebas nuevas de `SqlResilience`. Falla `Test_GetOneByExpression`, preexistente (ver #8).
- Migración ejecutada con la imagen nueva: 10 migraciones aplicadas con el nuevo timeout de 10 minutos.

## Reproducción

```bash
docker build -f PharmaGo.ApiGateway/Dockerfile -t pharmago-api-gateway:issue10-after .      # ídem Users y Pharmacy
kubectl apply -f "Implementacion K8S/Codigo/k8s/tests/interservice-resilience.yaml"
kubectl -n pharmago-resilience-test create secret generic db-secret \
  --from-literal=SA_PASSWORD='<generada>' \
  --from-literal=CONNECTION_STRING='Server=pharmago-db;Database=PharmaDb;User Id=sa;Password="<generada>";TrustServerCertificate=True'
# Job de migración con la imagen de Users y args ["--migrate"]
kubectl -n pharmago-resilience-test cp probe-resilience.py client:/tmp/
kubectl -n pharmago-resilience-test exec client -- python /tmp/probe-resilience.py --base http://pharmago-api-gateway \
  --path /api/drug --path /api/roles --rate 4 --duration 100 --out /tmp/r.json
docker pause <contenedor k8s_pharmago-db_...>; sleep 25; docker unpause <...>   # durante la carga
python summarize-resilience.py r.json --out summary.json   # junto a r.meta.json con las marcas de la falla
kubectl delete namespace pharmago-resilience-test
```
