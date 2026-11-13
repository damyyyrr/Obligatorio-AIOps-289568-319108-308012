# Issue #12 — logs JSON centralizados y persistencia

Validación nueva del 12/11/2026, Uruguay (13/11 UTC). **PASS local** para ingestión, búsquedas, reconstrucción por ID y persistencia comprobadas. Base integrada `1eaef3426ef8f208b260de5d8078d1b6ad558c83`. Los resultados corresponden a esta ejecución, no a una recuperación de evidencia del PR #34.

## Verificaciones

| Requisito | Resultado y archivo |
| --- | --- |
| Flujo central real | Fluent Bit del nodo lee logs CRI, interpreta el JSON .NET y envía a `pharmago-logs-*` en Elasticsearch 8.11.0. ConfigMap desplegada idéntica al repositorio: `provenance.json`. Se consultó Elasticsearch dentro de Kubernetes; no se usaron logs locales como sustituto. |
| Eventos de varios servicios | `logs-final.json`: consultas de servicio+tiempo devuelven 1.725 eventos de Gateway, 50 de Users y 58 de Pharmacy. Totales en el instante de la consulta, no volúmenes exclusivos del generador. |
| Severidad y tiempo | Consultas por `LogLevel` y `@timestamp >= 2026-11-13T01:52:00Z`: 1.696 Information, 37 Warning y 100 Error. Los filtros y respuestas HTTP 200 están guardados. |
| Reconstrucción por correlation ID | Login de usuario inexistente: `evidence-login-failure-61ee5fadd3e81460`, tres eventos de Gateway y Users. Las muestras contienen servicio, timestamp, nivel, categoría, TraceId, SpanId y correlation_id cuando están presentes. |
| Reconstrucción por trace ID | Trace de login `96d05eb4640ff5ec6fe890e98732365d`: tres eventos de Gateway y Users. Trace del fallo SQL `e32dc7e5c47fc351ed181c113efabdec`: tres eventos de Gateway y Pharmacy. En este último, correlation_id solo devuelve Gateway; se utiliza TraceId para enlazar la excepción del servicio. |
| Persistencia real | `persistence.json`: se eliminó el pod Elasticsearch con UID `30a2b432-06ea-40fa-a37c-d0eca53a78a7`; el reemplazo tiene UID `9abf84f8-a377-4440-be4b-90905c5c1281`. `_mget` recuperó **7/7 documentos originales por índice e ID**. PV/PVC mantuvieron sus UIDs. |
| Kibana | La vista `pharmago-logs` faltaba (HTTP 404). El script existente `kibana-data-view.py` la creó (HTTP 200), con patrón `pharmago-logs-*` y campo temporal `@timestamp`. Tras reiniciar Elasticsearch, la API de Kibana devolvió la vista con HTTP 200. Archivos `kibana-view-create.json` y `logs-after-restart.json`. No se afirma una validación visual en navegador. |
| Sanitización | `privacy-audit.json`: las muestras consultadas no contienen los secretos SQL/Grafana ni la contraseña inválida usada para la prueba. Los archivos públicos omiten mensajes/cuerpos libres, credenciales y excepciones completas. |

## Auditoría de stdout y alcance

Los tres servicios usan consola JSON con scopes. La auditoría estática de código productivo encontró un `Console.Error.WriteLine` restante en `DatabaseMigration.cs:51`: es el fallback cuando falla la construcción del host y todavía no existe logger; el mensaje es acotado y sanitizado. **No se afirma que toda salida, incluidos errores previos al host, sea JSON.** El camino normal del Job usa ILogger. No se provocó un fallo de configuración del Job para probar ese fallback en vivo.

No hay servicio Logstash en el Compose actual. Esta evidencia valida centralización **en Kubernetes** con Fluent Bit; no atribuye ingestión de logs al Compose ni sostiene el flujo Logstash descripto por tutoriales anteriores. La revisión de ese alcance no cambió archivos.

El primer arranque tardó en publicar los endpoints de Elasticsearch/Kibana por las probes y la recuperación de índices; inicialmente las consultas devolvieron URLError. Después respondieron HTTP 200. Elasticsearch quedó yellow en un nodo por réplicas de shards sin asignar; primarios disponibles y documentos consultables. El reemplazo de Elasticsearch también provocó un reinicio de Kibana por su liveness antes de recuperar. Esto verifica persistencia de datos, **no disponibilidad continua del stack de logs**.

## Repetición

1. Generar una request con `traceparent` y `X-Correlation-ID` conocidos. Para obtener un evento de negocio sin crear sesiones, usar POST `/api/login` con usuario inexistente y contraseña inválida de prueba.
2. Esperar el flush de Fluent Bit (5 s) y refresco/indexación. Ejecutar POST `http://elasticsearch:9200/pharmago-logs-*/_search` con los cuerpos de consulta guardados en `logs-final.json`. Una muestra reproducible:

```json
{"size":30,"sort":[{"@timestamp":"asc"}],"query":{"query_string":{"query":"\"96d05eb4640ff5ec6fe890e98732365d\""}}}
```

3. Leer/crear la vista con `scripts/kibana-data-view.py --kibana http://kibana:5601`; consultar `/api/data_views/data_view/pharmago-logs`.
4. Guardar IDs e índices seleccionados, eliminar únicamente el pod Elasticsearch del laboratorio, esperar Ready y consultar POST `/_mget` con esos IDs. Comparar UIDs de PV/PVC antes/después. Los nombres y tiempos exactos de esta ejecución están en `persistence.json`.

Los JSON son proyecciones sanitizadas de respuestas reales, con `_id`/índice y campos observables. Publican hasta cinco muestras por consulta y conservan los totales y el número de hits devueltos antes de esa selección. De la vista Kibana se conservan ID, nombre, patrón y campo temporal. No son documentos originales íntegros de Elasticsearch. `manifest.json` contiene hashes de los artefactos públicos: texto UTF-8 normalizado a LF y gzip por sus bytes exactos. Ver [trazas #11](../issue-11-20261112/README.md) y [alertas #13](../issue-13-20261112/README.md).
