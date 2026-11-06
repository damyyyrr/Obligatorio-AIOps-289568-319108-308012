# Borradores de issues

No publicados. Antes de crear cualquiera en `damyyyrr/Obligatorio-AIOps-289568-319108-308012`, revisar issues existentes y obtener autorización de escritura remota. Estos identificadores son locales, no números de GitHub.

## BASE-01 Arranque aislado y evidencia funcional

Prioridad P0; etiquetas propuestas: infra, observability, docs.

Tareas: Compose acotado, espera SQL, credenciales locales, builds secuenciales, arranque/parada, seed opt-in y smoke funcional/métricas/logs. Depende de Docker disponible. Cierre: ocho servicios operativos, evidencia reproducible, credenciales ignoradas y datos preservados; no cerrar por archivos escritos.

Resultado local 06/11/2026: verificado para el baseline; dos ejecuciones de catorce comprobaciones aprobadas, antes y después de parada/reinicio. Evidencia: `evidence/baseline-20261106/`. No se publicó ni cerró ningún issue remoto. La interacción real del frontend en navegador queda pendiente.

## K8S-01 Topología física y scheduling compatible con rollout

Prioridad P0; etiquetas propuestas: kubernetes, infra.

Tareas: resolver Q01, inventariar recursos, definir nodos por servicio/réplicas y margen de surge. Depende del baseline y aclaración/infraestructura física. Cierre: manifests validados, pod/node/host mapping y prueba real; dejar bloqueo físico visible si solo se dispone de simulación local.

## DB-01 Disponibilidad, persistencia y migraciones

Prioridad P0; etiquetas propuestas: kubernetes, resilience.

Tareas: Q02, inspección de migraciones al arranque, afinidad de datos hostPath, compatibilidad durante rollout/rollback y solución de DB si corresponde. Depende de topología/alcance. Cierre: pruebas sin pérdida de datos sobre el alcance confirmado; una DB Recreate no se declara altamente disponible.

## OBS-01 Telemetría completa en Kubernetes

Prioridad P1; etiquetas propuestas: observability, kubernetes.

Tareas: métricas individuales por pod/nodo, trazas OTLP consultables, logs JSON y ELK/equivalente, cinco reglas Grafana verificadas. Depende de K8S-01. Cierre: inventario/targets coincidentes, trace y correlation IDs verificables y cada alerta Firing → OK. La salida JSON de Docker no cierra por sí sola el requisito completo.

## ML-01 IF y One-Class SVM sobre material docente

Prioridad P1; etiquetas propuestas: ml.

Tareas: Q03, implementar IF/OCSVM con escalado y protocolo identificados, comparar y reproducir resultados. Independiente del despliegue. Cierre: ejecución reproducible sobre dataset autorizado, métricas si existen etiquetas y límites declarados. k-sigma/MAD son ampliación salvo confirmación.

## OPS-01 Seis escenarios de caos y plan de incidentes

Prioridad P1; etiquetas propuestas: chaos, resilience, docs.

Tareas: hacer seguros los cuatro scripts, añadir interrupción de red/desconexión interna, completar runbooks y ensayar war-room. Depende de telemetría, restauración y límites probados. Cierre: seis escenarios con efectos, aborto/limpieza, recuperación y evidencias; no ejecutar contra sistemas externos.
