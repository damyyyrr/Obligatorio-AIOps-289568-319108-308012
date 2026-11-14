# Consultar logs de PharmaGo en Elasticsearch y Kibana

## Flujo actual y evidencia

En Kubernetes, el flujo implementado es stdout/stderr de pods → Fluent Bit (DaemonSet) → Elasticsearch → Kibana. Fluent Bit interpreta los formatos CRI/Docker y eleva campos del JSON de consola .NET, como `Message`, `Category` y `LogLevel`. Los índices usan el patrón `pharmago-logs-*`.

La [evidencia #12](../../../docs/evidence/issue-12-20261112/README.md) registró ingestión de Gateway, Users y Pharmacy, consultas por servicio/nivel/tiempo y por IDs, y recuperación de 7/7 documentos tras reemplazar Elasticsearch conservando PV/PVC. Esas pruebas son de API en el laboratorio indicado; no se presenta como validación visual de Discover ni como disponibilidad continua del stack.

El Compose actual no tiene servicio Logstash. El [baseline Compose](../BASELINE.md) consulta logs de sus contenedores con Docker y no acredita este pipeline central. La arquitectura anterior con Logstash no es una instrucción de instalación vigente.

## Acceso al laboratorio Kubernetes

Con el clúster ya desplegado según [la guía Kubernetes](../k8s/README-k8s.md), sustituir el contexto y abrir cada port-forward en una terminal separada:

```powershell
kubectl --context '<contexto>' -n pharmago port-forward service/kibana 5601:5601
```

```powershell
kubectl --context '<contexto>' -n pharmago port-forward service/elasticsearch 9200:9200
```

Son accesos locales de diagnóstico; los componentes no se inician con estos comandos. Comprobar su estado antes de interpretar una conexión fallida como ausencia de logs:

```powershell
kubectl --context '<contexto>' -n pharmago get pods -l k8s-app=fluent-bit-logging
kubectl --context '<contexto>' -n pharmago logs -l k8s-app=fluent-bit-logging --tail=50
```

La etiqueta del DaemonSet es la del manifiesto actual. Revisar los logs localmente antes de publicar muestras: pueden contener mensajes o datos que no deben copiarse completos.

## Vista y consultas

Abrir http://127.0.0.1:5601. En Stack Management → Data Views, comprobar o crear `pharmago-logs`, patrón `pharmago-logs-*` y campo temporal `@timestamp`. El script [kibana-data-view.py](../scripts/kibana-data-view.py) también permite leer/crear la vista por API; seguir sus opciones `--help` y usar el destino del laboratorio.

En Discover, seleccionar esa vista y un intervalo que incluya la operación observada. Ejemplos KQL sobre los campos que conserva el pipeline:

```text
kubernetes.labels.app: "pharmago-users-service"
```

```text
kubernetes.namespace_name: "pharmago" AND LogLevel: "Error"
```

Para reconstruir una petición, usar el trace ID o correlation ID de una operación real y los cuerpos de consulta publicados en [logs-final.json](../../../docs/evidence/issue-12-20261112/logs-final.json). No se presupone que correlation ID y TraceId estén presentes en todas las líneas; la evidencia indica en qué operaciones se pudo usar cada uno.

Comprobar índices y conteos desde otra terminal:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:9200/_cat/indices?format=json'
Invoke-RestMethod -Uri 'http://127.0.0.1:9200/pharmago-logs-*/_count'
```

Si la vista está vacía, revisar intervalo temporal, índices, estado de Elasticsearch y salida de Fluent Bit. La existencia del data view no prueba que haya documentos. El arranque puede requerir tiempo de recuperación de índices; el reinicio de Elasticsearch de #12 también interrumpió Kibana antes de recuperarse.

## Generar y conservar evidencia

Usar una consulta de catálogo o una operación de laboratorio identificada por tiempo/IDs. Para login, emplear una cuenta de prueba existente o un fallo controlado acordado; esta guía no publica contraseñas ni asume un nombre de usuario predeterminado. La [guía de trazas](../../../docs/evidence/issue-11-20261112/README.md) explica la propagación y la correlación comprobadas.

Guardar consultas, tiempos, servicio, estado y muestras sanitizadas suficientes para sustentar el resultado. Los informes #11/#12 documentan sus filtros de privacidad; no copiar respuestas de login, Secrets o logs completos como evidencia pública.
