# Contraste documental — 14/11/2026

Revisión de estados, instrucciones y evidencias sobre `2f125b89bf5c8c34a8748367b068bbdb8cd17975`, que integra el PR #42. Solo se editan documentos y se agregan resúmenes documentales; código de aplicación, pruebas, escenarios y configuración permanecen iguales. El [estado actual](../../estado-actual.md) concentra los resultados y pendientes.

## Fuentes y comprobaciones

- [Consulta de las issues #1–#20](issues.json), con estado y fecha de cierre devueltos por GitHub y el texto del cierre acordado de #16. Cerrada no equivale a requisito académico completo; #1, #18, #19 y #20 seguían abiertas al consultar.
- [Verificación documental y de evidencia](verification.json): enlaces locales, sintaxis de bloques Bash sin ejecutarlos, manifiestos originales por tamaño/SHA-256 y contraste de los resultados citados con los JSON/CSV originales. La [sintaxis PowerShell](powershell-syntax.json) se comprobó con el parser de PowerShell, sin ejecutar comandos de esos bloques.
- [Suite .NET nueva](../test-isolation-20261114/README.md): 319/319 sobre el código con la corrección de aislamiento integrada. El resumen publica conteos y metadatos extraídos de los TRX; el árbol tenía cambios documentales y se declara así.
- [BDD](../issue-15-20261112/live-after-fix/summary.json): 4/4, navegador real, commit limpio y cero omisiones. [Incidentes del operador](../issue-16-20261113/README.md): seis reportes originales PASS, journals finalizados, limpieza verificada y ventanas estables de al menos 120 s; tAck null se conserva.
- [Alertas](../issue-13-20261112/alert-verdicts.json): cinco reglas con Firing y retorno a OK registrados. [Logs](../issue-12-20261112/persistence.json): 7/7 documentos recuperados tras el reemplazo. [ML](../issue-14-20261112/results/metrics.csv): métricas IF/OCSVM citadas desde el CSV publicado.

La revisión estática de `manage.py` y de sus wrappers confirma los parámetros de las instrucciones Kubernetes. `compose.baseline.yaml` confirma la dependencia `pharmago-db-migrate` antes de Users/Pharmacy y retención Prometheus de dos días. El Compose heredado no contiene Logstash. El manifiesto Fluent Bit confirma la etiqueta de los comandos de diagnóstico; la configuración, la evidencia #12 y `kibana-data-view.py` sustentan la guía de logs. `environment.apiUrl` y `nginx.conf` sustentan la aclaración del recorrido navegador → Gateway en la guía de rate limiting.

Las instrucciones corregidas se contrastaron con esos archivos y se verificó su sintaxis; no se presentan como una nueva instalación o una nueva prueba en vivo. Los resultados de infraestructura, navegador, ML y caos citados conservan sus fechas originales. Esta revisión solo ejecutó nuevamente la suite .NET.

## Conservación de antecedentes

Los informes iniciales ahora identifican su etapa histórica y enlazan el resultado posterior. No se convierten dry-runs en ejecuciones reales, no se sustituyen fallos por PASS y no se rellenan reconocimientos humanos o comunicaciones ausentes.

El paquete del operador del 13/11, incluidas sus capturas, README, JSON comprimidos y manifiesto, permanece intacto: sus textos anteriores al acuerdo de cierre se interpretan junto con la issue #16 y el estado actualizado. También se preservan las fuentes originales de las demás evidencias con manifiesto. Los cambios de texto en los índices/antecedentes de #15/#16/#17 son actualizaciones de seguimiento, no nuevas corridas.

Permanecen explícitos Q01–Q04, el alcance de SQL, la falta de defensa realizada, la revisión independiente no realizada, los límites de RAM/disco de 32 MiB y la continuidad observada de conexiones existentes en los ensayos de red/desconexión. Esta documentación no acredita efectos que los reportes no midieron.
