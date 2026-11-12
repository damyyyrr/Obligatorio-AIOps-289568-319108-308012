# Corrección del aborto y validación posterior de #17

**Estado final: seis ensayos reales PASS en Kubernetes local con Calico**, con 120 s estables por escenario y limpieza independiente. [Resumen verificable](trial-summary.json) · [Limpieza independiente](cleanup-verification.json).

| Ensayo | Efecto observado | Resultado y ficha |
|---|---|---|
| Requests | Generador: 100 HTTP 200 y 140 HTTP 429; cliente normal conservó catálogo/roles | [PASS](real-trials/requests/README.md) |
| CPU | De 0,00196 a 0,50019 cores en el pod; alerta CPU Inactive → Pending → Firing → Inactive | [PASS](real-trials/cpu/README.md) |
| RAM | Working set de 83,38 a 116,73 MiB, incremento de 33,36 MiB con bloque solicitado de 32 MiB | [PASS](real-trials/ram/README.md) |
| Disco | 33.554.432 bytes sincronizados fuera de PVC y posteriormente retirados | [PASS](real-trials/storage/README.md) |
| Red | Cuatro conexiones nuevas a Pharmacy fallaron durante la política y se restauraron; Gateway mantuvo catálogo/roles | [PASS](real-trials/network/README.md) |
| Desconexión | Nueve conexiones nuevas al Service sin endpoints fallaron y se restauraron; Gateway mantuvo su ruta existente | [PASS](real-trials/disconnect/README.md) |

Los códigos 0 de los probes significan fallo de transporte, no un estado HTTP. Red y desconexión acreditan aislamiento de conexiones nuevas; la ruta Gateway existente se registra de forma separada y siguió disponible. No se presenta esto como una caída total de PharmaGo.

## Fallos reproducidos y corregidos

La revisión identificó una carrera: el controlador podía enviar un RPC de CPU/RAM/disco, abortar antes del arranque remoto y declarar limpieza verificada con el RPC aún pendiente. Se liberaba el lock y terminaba el watchdog; un arranque tardío podía reintroducir carga después del aborto.

Los tres agentes de recursos ahora conservan cancelación por run-id, serializan el check/arranque/registro de PIDs/limpieza mediante `flock` y reciben un plazo absoluto. No pueden comenzar después de una cancelación ni reiniciar el estímulo después de vencer el plazo, aunque se haya retirado el tombstone. El controlador trata por igual los RPC inciertos de requests, CPU, RAM y disco: conserva controles/lock/journal y exige recuperación manual en lugar de declarar limpieza verificada. Solo retira los controles con RPC finalizado o deadline + 15 s, después de confirmar el fin del watchdog.

Al ejecutar el shell real desde Windows también se reprodujo un fallo de transporte: `text=True` traducía LF a CRLF en stdin y `sh` rechazaba el script. El controlador envía ahora bytes UTF-8 y decodifica únicamente la salida. Una regresión verifica que stdin conserve LF.

## Pruebas aprobadas

- **45 tests del controlador**, incluidos aborto inmediatamente después del despacho, timeout, conservación del lock, deadline vencido, segunda reversión tras RPC terminado, watchdog que no confirma parada y medición separada de rutas/conexiones nuevas. Sin Kubernetes ni carga.
- **Cinco tests del agente real en Docker**, con subcasos CPU/RAM/disco: cancelación antes de arrancar; deadline vencido incluso después de retirar cancelación; aborto de procesos activos; corte de un agente activo al vencer el plazo; preservación de un control ajeno.
- El contenedor efímero usó la imagen local Pharmacy, 256 MiB, 0,5 CPU, límite de 64 procesos y red deshabilitada. Se comprobaron ausencia de procesos identificados y payload después del aborto y retirada de controles al finalizar. El contenedor propio se eliminó; no accedió a datos ni servicios PharmaGo.
- Sintaxis de siete scripts shell y seis wrappers en dry-run aprobados.
- **26 controles de configuración Kubernetes** aprobados después del ajuste de Grafana. CI [Chaos safety, run 43319356240](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/actions/runs/43319356240) aprobado en Ubuntu/Python 3.11 con los 45 + 5 + 26 tests. La ejecución local usa Python 3.14.

[Log controlador](controller-tests.txt) · [Log agente](agent-tests.txt) · [Configuración Kubernetes](k8s-config-tests.txt) · [Commit, hashes y conteos](checks.json).

Los hashes corresponden a los archivos locales ejecutados; el commit identifica el contenido Git. Windows/Linux pueden materializar distintos finales de línea en archivos Python. Los scripts shell se conservan LF por `.gitattributes`.

## Laboratorio para los seis ensayos integrales

En esta validación el equipo dispone de aproximadamente 15,95 GiB físicos y el motor Docker de 7,73 GiB. Se creó un perfil nuevo `pharmago-issue17-validation`, de un nodo con presupuesto de 6144 MiB/4 CPU y Calico, sin modificar los perfiles anteriores ni sus datos. Esto no prueba separación física ni disponibilidad multinodo.

Las cuatro imágenes se construyeron y cargaron desde el commit limpio `28b3b8b`, tag `chaos-fix-20261112-01`; las modificaciones posteriores hasta `5c42fc0` agregan tests, CI y documentación, sin cambiar el código de aplicación o del controlador. La base usa las versiones operativas declaradas por el repositorio. El primer apply agotó 240 s durante la descarga inicial de SQL; se conservó la instalación parcial, se cargó la imagen fijada desde la caché local y se retomó el mismo apply con el timeout soportado de 600 s. No se redujeron pisos de capacidad ni controles del runner. SQL y migraciones terminaron saludables y se insertó el seed docente sin reset.

Después de que el usuario liberó memoria, quedaron aproximadamente 3,5–4 GiB disponibles y se ejecutaron los seis ensayos, uno a uno. Todos finalizaron con PASS y `cleanup=verified`. Se contrastaron por escenario los UIDs de PV/PVC y configuración, fingerprints de catálogo/roles y una ventana funcional estable de al menos 120 s sin nuevos reinicios. La comprobación independiente final confirmó ausencia de procesos/archivos propios, cancelaciones, locks y políticas temporales, además del selector original del Service.

## Dos problemas encontrados durante los ensayos reales

### Grafana/SQLite

El primer ensayo de disco escribió y retiró los bytes previstos, pero abortó durante recuperación porque el endpoint de reglas Grafana respondió HTTP 500. Sus logs registraron `database is locked` al autenticar, también antes de ese ensayo. La vista [del fallo](failed-storage-before-wal.json) y su original `.json.gz` se conservan; la clasificación FAIL se mantuvo.

Se activó `GF_DATABASE_WAL=true` en el manifiesto Grafana, opción de la [versión 10.4.2](https://github.com/grafana/grafana/blob/v10.4.2/conf/defaults.ini#L145), sin cambiar reglas ni ignorar errores HTTP. Tras el rollout se confirmó WAL mediante el API de configuración y pasaron [60/60 consultas autenticadas](grafana-wal-check.json), con máximo de 32,02 ms. Disco se repitió y pasó; las observaciones posteriores de red/desconexión conservaron evaluación sana. Esto valida la corrección observada en el laboratorio, sin prometer ausencia de toda contención futura.

### Conexiones nuevas y existentes

Los primeros ensayos de red/desconexión fueron FAIL porque el catálogo vía Gateway seguía respondiendo. El [diagnóstico de red](network-diagnostic.json) comprobó que Calico sí bloqueaba conexiones nuevas directas a Pharmacy y las restauraba al retirar la política. El [diagnóstico de Service](disconnect-diagnostic.json) observó endpoints vacíos y fallo de conexión nueva, con Gateway todavía disponible. La supervivencia de conexiones existentes al cambiar NetworkPolicy depende de la implementación, según [Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/#networkpolicy-s-impact-on-existing-connections); la reutilización de conexiones del Gateway es una interpretación compatible, sin captura de identidades TCP.

El probe ahora registra `target` y `path`, mide la conexión nueva al Service y el camino por Gateway por separado y compara cada fingerprint por destino/ruta. PASS sigue exigiendo un fallo real en el acceso nuevo aislado y su restauración; crear una política o cambiar un selector sin efecto observado continúa siendo FAIL. Los seis intentos rechazados/fallidos se conservan en `failed-attempts/`, listados en [trial-summary.json](trial-summary.json).

## Proveniencia, formato y límites

Los ensayos se ejecutaron desde commits limpios distintos, identificados en cada ficha: requests/CPU/RAM en `a807b04`; disco en `0a47b7b` después de WAL; red en `1280e45`; desconexión en `b808ed4` con medición separada. Se verificaron los hashes de cada fuente contra los blobs del commit correspondiente, contemplando la materialización LF/CRLF de Windows. Las cuatro imágenes de aplicación conservaron el tag construido desde `28b3b8b`; los cambios posteriores afectan controlador/probe, configuración Grafana, tests, CI y documentación.

Cada `report.json` es una vista compacta con estados, muestras y comprobaciones de telemetría; `artifactView` indica los snapshots repetidos/etiquetas omitidos y el SHA-256 del original. El archivo `report.json.gz` conserva el JSON original íntegro, sin modificaciones, con hash verificado. El mismo formato se aplica a los intentos fallidos. Se conservaron 16 vistas/originales (incluidas referencias duplicadas a fallos) en aproximadamente 2,8 MB. Para inspeccionar el detalle: `python -c "import gzip; print(gzip.open('report.json.gz','rt',encoding='utf-8').read())"`.

Las fichas aportan hipótesis, comando, efecto, alertas, tiempos observados, restauración y conclusión. `tAck` permanece null: no se inventaron reconocimiento humano, TTA, comunicaciones ni promedios. La evidencia técnica local de #17 queda lista para revisión e integración. La validación por compañero de roles y comunicaciones del proceso #16 permanece pendiente. El laboratorio es de un nodo en una PC; no demuestra separación física, caída de nodo ni disponibilidad en producción.

## Primer intento integral: precheck bloqueado por memoria libre

El apply completo terminó con todos los pods Ready, SQL con datos de demostración, Elasticsearch green, Jaeger disponible, nueve targets `up=1`, métricas de CPU/RAM/storage de 19 pods, métricas de nodo y cinco alertas sanas/inactivas. La captura [health-before.json](health-before.json) registra ese estado y **1,67 GiB libres en el host**. La dotación total de 16 GiB no equivale a memoria disponible para inyectar carga.

Se invocó `requests --context pharmago-issue17-validation --duration 60 --megabytes 32 --execute` mediante el helper local que proporciona las credenciales por entorno, desde el commit limpio `9f81d3c967d04c0a88974cde39ceda43490d8da5`, el 12/11/2026 a las 18:44:48 de Uruguay. El [reporte original](precheck-blocked.json) terminó con exit 1/status FAIL por `Precheck: menos de 2 GiB de RAM libre en el host; no se inyectará carga`.

La clasificación de aceptación de este intento es **BLOCKED antes de inyección**, no un experimento de requests aprobado o un fallo observado de PharmaGo: no hay evento `inject-requested`, muestras, observaciones, journal ni lock de ensayo. Se comprobó la ausencia del ConfigMap de lock. `liveValidation=true` en el reporte identifica el modo solicitado, no prueba que se haya llegado a inyectar. El piso de 2 GiB se conservó y no se continuó con CPU/RAM/disco/red/desconexión mientras faltara ese margen.
