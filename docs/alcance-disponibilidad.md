# Disponibilidad durante el reemplazo de componentes

Revisión del 11/11/2026. Este documento distingue el resultado medido del requisito completo y reúne los pendientes generales. Se basa en los manifiestos, el código y la evidencia existente; esta revisión documental no agrega pruebas de ejecución.

## Requisito y criterio de interpretación

La letra del obligatorio, en «Despliegues seguros» (5 puntos), establece:

> El sistema debe poder reemplazar sus componentes garantizando 100% de disponibilidad.
>
> Se necesita documentar y explicar la técnica elegida.

El apartado no enumera los componentes ni excluye la base de datos o la observabilidad. No hay una excepción docente registrada. Por eso se conserva el conjunto de componentes como alcance de trabajo; una consulta pendiente sobre su interpretación no acredita cumplimiento ni permite excluirlos.

**El reemplazo de SQL Server sin interrupción sigue sin implementar ni demostrar. El requisito completo de despliegues seguros está incompleto.** Conservar datos, recuperar un proceso y mantener el servicio durante su reemplazo son resultados que necesitan comprobaciones diferentes.

## Resultado demostrado

Se observaron **226/226 solicitudes funcionalmente válidas durante 282,139 segundos**, al actualizar y revertir Gateway, Users y Pharmacy. Se consultaron catálogo, roles y login por Gateway hacia los servicios y SQL, sin reintentos del generador y sin errores HTTP, timeouts o fallos de validación. Se observaron versiones Ready coexistentes y se restauraron las plantillas anteriores, conservando los registros comprobados y el esquema.

Ese resultado corresponde a una prueba local, con carga baja, operaciones cortas y nodos disponibles. SQL, UI y observabilidad permanecieron estables. La política de drenaje ya estaba instalada antes de comenzar la ventana medida. No se reemplazó toda la plataforma ni se probó navegación o escritura de negocio durante el recambio. El porcentaje describe las solicitudes observadas bajo esas condiciones; no demuestra disponibilidad universal. El generador y las condiciones están en la [guía de rollout](aiops-k8s-rollout.md) y en [verify_rollout.py](../Implementacion%20K8S/Codigo/k8s/verify_rollout.py).

## Componentes pendientes y efecto sobre el requisito

| Componente | Configuración o evidencia actual | Consecuencia y pendiente |
|---|---|---|
| SQL Server | Una réplica Express, volumen local y estrategia `Recreate` en [su Deployment](../Implementacion%20K8S/Codigo/k8s/deployments/ops/db-deployment.yaml). | El recambio retira la instancia anterior antes de disponer de la nueva. Las operaciones de negocio dependen de SQL. Falta una solución de continuidad y una prueba durante el reemplazo. El backup, Retain y las migraciones controladas cubren persistencia y despliegue, pero no esa continuidad. |
| Elasticsearch | Una réplica con `Recreate` en [su Deployment](../Implementacion%20K8S/Codigo/k8s/deployments/ops/elasticsearch-deployment.yaml). | El recambio deja temporalmente sin instancia de consulta e ingestión. Falta demostrar continuidad del servicio de logs y conservación de los eventos enviados durante la transición. |
| Prometheus | Una réplica con `Recreate` en [su Deployment](../Implementacion%20K8S/Codigo/k8s/deployments/ops/prometheus-deployment.yaml). | Durante el recambio queda sin instancia de recolección y consulta. Conservar su volumen no demuestra continuidad del muestreo o de las consultas. |
| Kibana | Una réplica con `Recreate` en [su Deployment](../Implementacion%20K8S/Codigo/k8s/deployments/ops/kibana-deployment.yaml). | La interfaz de consulta deja de estar servida por esa instancia durante el recambio. La persistencia de Elasticsearch no acredita acceso continuo a Kibana. |
| UI | Una réplica, readiness sobre `/`, sin estrategia de actualización explícita ni hook de drenaje en [su Deployment](../Implementacion%20K8S/Codigo/k8s/deployments/frontend/ui-deployment.yaml). | No se midió su reemplazo. Hace falta verificar carga de páginas, recursos estáticos y operaciones desde el navegador durante actualización y reversión. Un HTTP 200 en `/` no alcanza para comprobar esos flujos. |
| Grafana | Una réplica, PVC compartido por la plantilla, readiness TCP y sin estrategia explícita en [su Deployment](../Implementacion%20K8S/Codigo/k8s/deployments/ops/grafana-deployment.yaml). | Falta validar el recambio, acceso a dashboards y evaluación de alertas. Antes de asumir que se pueden solapar instancias, revisar la compatibilidad del almacenamiento y de la configuración usada. El probe TCP no verifica esas funciones. |
| Collector OTLP y agentes por nodo | Collector central con una réplica y sin readiness en [su Deployment](../Implementacion%20K8S/Codigo/k8s/deployments/ops/otel-collector-deployment.yaml); agentes desplegados como DaemonSets. | Falta medir actualizaciones de la cadena de telemetría, disponibilidad de los receptores, tratamiento de datos en vuelo y posibles huecos o pérdidas. La existencia de métricas antes y después no prueba continuidad durante su propio recambio. |

Estas interrupciones de observabilidad afectan la disponibilidad de esas herramientas y la capacidad de observar el sistema. La revisión no demuestra que cada una interrumpa también las rutas de negocio; ambos efectos deben medirse por separado.

## Otras condiciones que limitan la conclusión

- **Almacenamiento y nodos.** SQL, Elasticsearch, Prometheus y Grafana usan volúmenes locales ligados al nodo propietario. Mover una etiqueta no mueve los datos. Las réplicas de cada backend comparten su nodo elegible y Gateway tiene una réplica estable. La prueba local usa tres nodos Kubernetes en una sola PC: no demuestra continuidad ante pérdida del nodo o del host físico. Ver [topología](aiops-k8s-topology.md) y [recuperación de datos](aiops-k8s-recovery.md).
- **Capacidad de recambio.** Debe caber el pod de surge y el consumo de los pods que siguen terminando. La medición fue secuencial; no prueba actualizaciones simultáneas de todos los componentes ni carga máxima.
- **Esquema y dependencias.** Las versiones ensayadas usaron el mismo esquema SQL. Un Job de migración serializa ejecuciones, pero un cambio futuro que rompa compatibilidad puede afectar a las versiones antiguas que siguen atendiendo. Hay que probar ambos binarios con el esquema nuevo y el rollback previsto. El [apply integral](../Implementacion%20K8S/Codigo/k8s/manage.py) también aplica SQL y observabilidad; el resultado de recambiar solo tres Deployments no se extiende automáticamente a ese flujo completo.
- **Solicitudes largas y operaciones con efectos.** El apagado de los tres procesos tiene un timeout explícito de 20 s; los clientes HTTP entre servicios tienen un timeout configurado de 30 s. Eso exige revisar operaciones largas o encadenadas: las pruebas con solicitudes cortas no acreditan que terminen dentro del presupuesto ni que una recuperación evite operaciones duplicadas. No se midieron compras o cambios de stock durante el recambio.
- **Readiness y protección de tráfico.** Gateway puede quedar Ready en estado degradado cuando solo un backend está disponible; ese estado no significa que todas las rutas funcionen. Además, el rate limiting en memoria del Gateway no conserva un contador compartido entre versiones. La prueba a baja carga no acredita continuidad de esa protección al reemplazar o solapar instancias. Ver [readiness](../Implementacion%20K8S/Codigo/Backend/PharmaGo.ApiGateway/GatewayReadinessCheck.cs) y [configuración del Gateway](../Implementacion%20K8S/Codigo/Backend/PharmaGo.ApiGateway/Program.cs).

Los puntos anteriores distinguen limitaciones configuradas y escenarios no probados. No se presentan como fallos reproducidos donde solo hubo inspección estática.

## Evidencia necesaria para completar el requisito

Definir una matriz de reemplazo que incluya cada componente, su técnica, dependencias y operación funcional que debe seguir disponible. Probar actualización y reversión o recuperación prevista, con tráfico antes, durante y después, conservando todas las respuestas y verificando los datos. Para la aplicación, incluir navegación y operaciones de negocio representativas; para observabilidad, medir ingestión, consultas, dashboards y alertas mientras se reemplaza su propia cadena.

Registrar ventana, cadencia, carga, solicitudes enviadas, éxitos, errores HTTP incluidos los 429, timeouts, validación y latencia. Para telemetría registrar también posibles huecos o pérdidas. Distinguir pruebas de reemplazo planificado de pruebas de pérdida de nodo. Mantener explícito el alcance observado hasta contar con evidencia suficiente o una aclaración docente documentada que precise los componentes exigidos.
