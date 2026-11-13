# Issue #11 — trazas OTLP consultables

Validación nueva, realizada el 12/11/2026 en Uruguay (13/11 UTC), sobre el backend integrado en `obligatorio`, base `1eaef3426ef8f208b260de5d8078d1b6ad558c83`. **PASS local** para los criterios de #11. No se reconstruyen ni se atribuyen resultados a la ejecución original del PR #33.

## Criterios y resultados

| Criterio de la issue | Evidencia observada |
| --- | --- |
| Request real, spans enlazados y consulta por trace ID | `success-pharmacy.json`: GET `/api/drug`, HTTP 200, cuatro spans Gateway servidor → Gateway cliente HTTP/YARP → Pharmacy servidor → cliente SQL `PharmaDb`, `db.system=mssql`. Trace `b361ca929f605f5e1a62f6985ec02f33`. |
| Instrumentación de Users y DB | `success-users-correct.json`: GET `/api/roles`, HTTP 200, cuatro spans con la misma cadena a Users y SQL. Trace `c6549c93c02d96f178dff37108903be1`. |
| Operación fallida acotada | `failure-sql.json`: pausa temporal del proceso SQL en el laboratorio; GET `/api/drug`, HTTP 500 en 5,224 s y tres spans con `error=true`/`otel.status_code=ERROR`. Trace `e32dc7e5c47fc351ed181c113efabdec`. En este fallo de conexión no se observó un span SQL; no se afirma que lo haya. |
| Propagación de contexto | Cada petición envió `traceparent` W3C con un trace ID aleatorio conocido y padre externo `0123456789abcdef`. Los spans devueltos por Jaeger conservaron ese trace ID y las relaciones padre/hijo. Los archivos guardan IDs, operaciones, tiempos y tags permitidos. |
| Correlación con logs JSON | `logs-final.json`: búsqueda central por trace ID del fallo SQL devuelve tres eventos de Gateway y Pharmacy. El login controladamente rechazado (`login-failure.json`, HTTP 404 por usuario inexistente) devuelve tres eventos de Gateway y Users por trace ID y por correlation ID. Ver también [#12](../issue-12-20261112/README.md). |
| Pipeline y backend consultable | `provenance.json` comprueba igualdad de la ConfigMap desplegada con el repositorio: OTLP gRPC → Collector/batch 5 s → OTLP Jaeger. Las consultas se hicieron a `/api/traces/{traceID}` dentro del clúster. |

## Backend elegido y alcance

Se valida el Jaeger all-in-one 1.62.0 existente: interfaz y API consultables, receptor OTLP, máximo de 20.000 trazas, request de 128 MiB y límite de 512 MiB. Resulta adecuado para este laboratorio de una máquina sin incorporar otro almacenamiento de trazas. **Usa memoria: las trazas se pierden al reiniciar Jaeger**. Los JSON versionados conservan las muestras de esta ejecución; no prueban retención durable, alta disponibilidad ni hosts físicos independientes.

El backend de las imágenes `chaos-fix-20261112-01` fue construido desde `28b3b8bb2f1795026977bb526372c1f9cc639b16`; la comparación de todo `Backend/` contra la base actual dio diff vacío. Los IDs de imágenes y hashes están en `provenance.json`. No se modificó código ni configuración del repositorio para esta validación.

## Reproducción y sanitización

Desde un cliente Python dentro del namespace `pharmago`, ejecutar el script existente:

```sh
python probe-trace.py --base http://pharmago-api-gateway --path /api/drug --jaeger http://jaeger:16686 --out trace.json
python probe-trace.py --base http://pharmago-api-gateway --path /api/roles --jaeger http://jaeger:16686 --out users-trace.json
```

El script está en `Implementacion K8S/Codigo/scripts/`. La prueba guardada usó la misma secuencia HTTP/Jaeger, añadió `X-Correlation-ID`, seleccionó tags permitidos y registró UTC. Para repetir el fallo y su restauración, consultar los comandos y el diario de [#13](../issue-13-20261112/README.md).

No se publican cuerpos HTTP, datos de login, headers de autorización, cadenas de conexión, SQL ni excepciones completas. `privacy-audit.json` revisa los documentos reales seleccionados buscando los secretos del laboratorio y la contraseña inválida de prueba: ninguno apareció. Es una comprobación de estas muestras, no una garantía sobre todos los eventos históricos. `manifest.json` permite verificar los hashes.

## Incidencia del procedimiento

`success-users.json` conserva el intento inicial a `/api/role`, que devolvió 404. La ruta existente es `/api/roles`; su repetición correcta quedó en `success-users-correct.json`. El intento inicial no se cuenta como operación exitosa.
