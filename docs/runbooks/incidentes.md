# Runbooks de incidentes de PharmaGo

Aplicar junto con [el plan](../baseline-incidents.md) y [la ficha](../templates/incidente.md). Los mecanismos de #17 están en [la guía](../../Implementacion%20K8S/Codigo/chaos-engineering/README.md) y cuentan con [seis ensayos técnicos locales aprobados](../evidence/issue-17-20261112/fix-after-review/README.md). Requieren contexto/namespace, roles, inventario, límite temporal y reversión registrados antes de actuar. La ejecución automatizada no acredita reconocimiento ni comunicaciones humanas: la revisión por compañero de #16 continúa pendiente.

## RB-01: exceso de solicitudes o solicitudes fallidas reiteradas

**Detectar:** aumento de requests, 429/5xx, p95 o fallas funcionales. El alertado de 5xx no detecta 429 ni todo fallo de negocio. Separar rechazos esperados al generador de errores a usuarios legítimos.

1. **Diagnosticar:** comparar tráfico por ruta/estado, logs Gateway y número de réplicas. Filtrar `service_name="PharmaGo.ApiGateway"` para contar tráfico entrante una vez. Revisar `Retry-After` y [cuotas](../aiops-rate-limiting.md).
2. **Contener:** detener el PID/job exacto del generador, sin volver a dispararlo para confirmar la falla. Mantener rate limiting activo y no confiar en headers de identidad elegidos por el cliente.
3. **Restaurar:** esperar vencimiento de la ventana aplicable (minuto u hora), respetando `Retry-After`. No reiniciar el Gateway para vaciar contadores ni escalarlo como arreglo: el estado es local por pod, también durante surge. Con port-forward todos pueden compartir IP; registrar ese efecto.
4. **Validar:** ventana funcional del plan a baja carga, cuota efectiva y retiro del exceso. Los 429 del tráfico legítimo cuentan como fallos. Si persisten 5xx con carga normal, RB-06; si hay saturación, RB-02/RB-03.

**Abortar/escalar:** origen/PID desconocido o tráfico ajeno: contactar al operador del origen, sin cortar recursos de otros proyectos. Presión del host → S1. **Guardar:** solicitudes enviadas/aceptadas/rechazadas/timeouts, cuotas, réplicas, horas y efecto en clientes legítimos.

## RB-02: saturación de CPU

**Detectar:** `pharmago-pod-cpu`, p95 elevado, throttling o probes lentos. CPU del nodo y CPU del contenedor son medidas distintas.

1. **Diagnosticar:** [consultas](../aiops-k8s-metrics.md) y dashboard Infra por pod/nodo; comparar con límites, réplicas y eventos. `kubectl --context $ctx -n $ns top pod $pod --containers` requiere Metrics Server; su ausencia no significa CPU cero.
2. **Contener:** detener el PID/generador de CPU registrado por #17 y comprobar que terminó. Cerrar `kubectl exec` no prueba que sus hijos terminen. La versión heredada de `cpu-spike.sh` dejaba bucles sin limpieza garantizada; ahora el wrapper usa el controlador, agente con PID identificado, trap/timeout y recuperación por journal. Su validación real aún está pendiente.
3. **Restaurar:** si la inyección persiste dentro de un pod stateless y se perdió el PID, coordinación puede recrear solo el servicio elegido con el procedimiento acotado al final. Detener antes cualquier proceso que pudiera reinyectar. No aumentar CPU/réplicas a ciegas ni operar sobre todo el nodo.
4. **Validar:** consumo próximo al baseline, sin nuevos fallos de probes, alerta vuelve a OK con datos y ventana funcional completa. Distinguir retiro del estímulo de efecto de un reinicio.

**Abortar/escalar:** presión host/nodo, efecto fuera del destino o duración excedida → S1. **Guardar:** series/límites, PID y duración, eventos/reinicios, latencias, retirada y limpieza.

## RB-03: presión de RAM / OOM

**Detectar:** `pharmago-pod-memory`, OOMKilled, reinicios o MemoryPressure. Exit 137 por sí solo no prueba OOM; contrastar motivo/eventos y consumo, porque también puede ser SIGKILL por otra causa.

1. **Diagnosticar:** memoria frente al límite, memoria libre del nodo/host, `describe pod`, terminación anterior y logs previos. Distinguir heap, tmpfs (`/dev/shm`) y disco (`/tmp`). La versión heredada de `ram-spike.sh` tenía fallback a disco; el nuevo agente usa dd/FIFO sin ese fallback. Si el incidente proviene de scripts antiguos o de otro origen, comprobar también RB-04.
2. **Contener:** detener el proceso retenedor identificado. Si creó un archivo, verificar pertenencia/ruta según RB-04 antes de retirarlo. No usar `pkill` general ni matar SQL/Elasticsearch para liberar RAM.
3. **Restaurar:** permitir recuperación por kubelet; si se repite, detener inyección y diagnosticar, sin mantener un crash loop. Recrear un servicio stateless solo cuando sea necesario, mediante el procedimiento acotado. Conservar logs previos si la estabilidad del host lo permite.
4. **Validar:** memoria recuperada, dotación esperada, sin nuevos OOM/reinicios/presión y ventana funcional. Running tras OOM no acredita Ready. Esperar OK real con métricas frescas.

**Abortar/escalar:** OOM fuera del destino, reinicios repetidos o host inestable → S1. **Guardar:** causa de terminación observada, límites/consumo, estímulo, respuestas, retirada y limpieza; no confundir síntoma con causa raíz confirmada.

## RB-04: almacenamiento lleno / presión de disco

**Detectar:** errores de escritura/espacio, DiskPressure/evicciones o crecimiento efímero. No hay alerta específica de disco entre las cinco reglas actuales: vigilar filesystem y síntomas; ausencia de Firing no demuestra disco sano.

1. **Diagnosticar:** identificar pod, nodo, filesystem y si la escritura cae en capa efímera, tmpfs o PVC. Revisar mounts y `df -h` si existe en la imagen. Bytes efímeros no miden ocupación de PVC; revisar filesystem del nodo propietario.
2. **Contener:** detener el PID escritor. Registrar espacio libre y tamaño del archivo exacto. No crear más archivos para confirmar el llenado. No tocar MDF/LDF, backups, índices de Elasticsearch ni bloques de Prometheus.
3. **Restaurar:** retirar solo artefactos registrados del ensayo, verificando UID/contenedor, ruta absoluta y ausencia de symlinks. #17 debe usar directorio exclusivo con ID único fuera de PVC e inversa exacta. `/tmp/chaos_fill`, `/tmp/fill` y `/dev/shm/fill` heredados no prueban pertenencia: no borrar por nombre. Si no puede demostrarse propiedad, escalar al dueño del disco.
4. **Validar:** bytes liberados, escritura detenida, nodo sin presión, datos y operaciones funcionales. Si se sospecha corrupción, aislar y seguir [restauración](../aiops-k8s-recovery.md) en volumen independiente; no sobrescribir origen.

**Abortar/escalar:** piso de espacio libre acordado, DiskPressure, escritura sobre datos o impacto del host → S1. Sin presupuesto de bytes/espacio inicial no comenzar. **Guardar:** mount/ruta/tamaño propios, espacio antes/durante/después, presión, datos y limpieza. Reiniciar un pod no limpia necesariamente PVC o hostPath.

## RB-05: interrupción del tráfico de red

**Detectar:** timeouts, conexión rechazada, targets o rutas inaccesibles. Un port-forward roto no demuestra corte de red interno.

**Observación de #17:** Calico bloqueó conexiones nuevas del cliente al Service Pharmacy, mientras el catálogo por Gateway siguió respondiendo. El comportamiento de conexiones establecidas no se deduce de la creación de una NetworkPolicy. Medir y registrar ambas rutas; no reiniciar el Gateway para forzar artificialmente el resultado.

1. **Diagnosticar:** comparar camino externo y Service interno desde el cliente de pruebas identificado. Revisar `svc`, EndpointSlices, Ready, DNS, red de nodo y salto afectado (cliente→Gateway o Gateway→backend); contrastar logs/trazas y [timeouts](../aiops-interservice-resilience.md).
2. **Contener:** detener la inyección registrada. #17 debe guardar regla/selección previa e inversa específica. No vaciar iptables, borrar todas las NetworkPolicies, reiniciar kube-proxy ni cambiar el contexto global.
3. **Restaurar:** revertir exactamente objeto/regla/proceso temporal preservando configuración previa. Verificar identidad antes. Si solo perdió port-forward, reconectar con contexto explícito y verificar que el servicio era accesible internamente.
4. **Validar:** DNS, endpoints y tráfico por Service; targets/trazas; ventana funcional por el camino original y ausencia de regla temporal. Dependencia todavía desconectada → RB-06.

**Abortar/escalar:** pérdida de control del clúster, alcance en otros namespaces o inversa desconocida → parar y escalar al dueño de red; S1 si afecta host/otros proyectos. **Guardar:** origen/destino/puerto, regla/diff sanitizado, accesos internos/externos y reversión. La implementación de los mecanismos de red sigue en #17.

## RB-06: desconexión interna de SQL o un microservicio

**Detectar:** Users/Pharmacy NotReady, 500/502/503/504, spans SQL lentos o sin endpoints. Gateway puede seguir Ready/Degraded con ambos backends caídos. Si cae Pharmacy, comprobar si roles/login siguen atendidos.

**Observación de #17:** al agregar el selector temporal, el Service Pharmacy quedó sin endpoints y fallaron las conexiones nuevas, pero la ruta existente del Gateway siguió atendiendo. Validar conexiones nuevas y existentes por separado. Retirar únicamente la clave propia, comprobar selector/UID originales y verificar los 120 s estables; esto no equivale a detener SQL ni a eliminar pods.

1. **Diagnosticar:** identificar dependencia y operación. Revisar SQL, Job de migración, endpoints, eventos, logs y trace ID. Distinguir pausa de contenedor, escala a cero, bloqueo de proceso, corte de red y SQL sin capacidad. Liveness sana/readiness fallida no justifica reiniciar todos los consumidores.
2. **Contener:** detener carga/estímulo; evitar reintentos masivos y escrituras duplicadas de resultado incierto. Conservar rutas disponibles, sin retirar manualmente el único Gateway para ocultar errores. Comunicar alcance parcial o total.
3. **Restaurar:** aplicar inversa registrada: cantidad previa exacta de réplicas, reanudar contenedor pausado con UID/runtime confirmado o revertir regla según RB-05. Un ID Docker no es un ID containerd. Esperar SQL/Job y readiness de consumidores. Para esquema/datos seguir [migración](../aiops-sql-migrations.md) y [recuperación](../aiops-k8s-recovery.md); no recrear DB, repetir seed o borrar PVC.
4. **Validar:** dependencias, endpoints, roles/catálogo/login y datos. Separar primer HTTP válido, Ready y ventana estable. Comparar ruta no afectada, trazas y OK de alertas con datos presentes.

**Abortar/escalar:** inconsistencia, Secret perdido/incompatible, restauración fallida o réplica previa desconocida → responsable de datos/entorno; no improvisar credenciales/versiones. S1 si hay riesgo de corrupción. **Guardar:** dependencia, UID/runtime, réplicas antes/después, errores/timeouts, migraciones, datos y transiciones.

## Recuperación acotada de un servicio stateless

Solo con la inyección detenida y dependencia/capacidad/revisión comprobadas, por decisión registrada de coordinación. Reinicia pods y puede interrumpir tráfico, especialmente con un único Gateway. No garantiza 100% de disponibilidad. No usar en SQL ni componentes con almacenamiento.

```powershell
$allowed = @('pharmago-api-gateway','pharmago-users-service','pharmago-pharmacy-service')
if ($app -notin $allowed) { throw 'Servicio fuera del alcance de este procedimiento' }
kubectl --context $ctx -n $ns rollout history "deployment/$app"
if ($LASTEXITCODE -ne 0) { throw 'No se pudo comprobar la revisión' }
kubectl --context $ctx -n $ns rollout restart "deployment/$app"
if ($LASTEXITCODE -ne 0) { throw 'No se pudo solicitar el recambio' }
kubectl --context $ctx -n $ns rollout status "deployment/$app" --timeout=240s
if ($LASTEXITCODE -ne 0) { throw 'Recambio incompleto: conservar evidencia y escalar' }
```

Volver al plan para validar funcionalidad, estabilidad y limpieza. Si falla, no repetir en bucle. #17 debe verificar cada runbook con el mecanismo efectivamente usado y corregirlo con sus resultados.

## Aprendizajes de la ejecución guiada del 13/11/2026

La [ejecución de los seis casos por el operador](../evidence/issue-16-20261113/README.md) registró dificultades de uso y estas aclaraciones. Los seis casos dieron PASS y limpieza verified; la sesión fue guiada y no constituye revisión independiente por otra persona.

1. **Variables por terminal.** PowerShell no comparte variables entre ventanas. Desde la raíz, inicializar `$ctx = 'pharmago-issue17-validation'` y `$codigo = Join-Path (Get-Location) 'Implementacion K8S/Codigo'` solo si ese es el laboratorio que se ha verificado. En una segunda ventana usar rutas absolutas a los helpers locales; no asumir el mismo directorio ni las mismas variables. Si se usa un worktree, `$codigo` debe apuntar al código de ese worktree, con ruta entre comillas.
2. **Inicio y baseline.** Tras iniciar Minikube pueden aparecer estados transitorios. Esperar que todos los pods esperados estén Ready, comprobar operaciones reales y evaluación de alertas antes de inyectar. `Running` aislado no alcanza. No avanzar si persiste un error de configuración.
3. **Acceso a Grafana.** Usar el valor de la credencial privada, no el nombre de una clave como `grafanaAdminPassword`. Evitar capturas que muestren contraseñas. Mantener abierta la terminal del port-forward mientras se usa el panel.
4. **Gráficas de recursos.** En un intervalo que incluya antes/durante/después, localizar el nombre y UID del objetivo en el journal; desplazar la leyenda o aislar su serie para que otros pods no oculten el cambio. La hora y escala de una captura no sustituyen las muestras del reporte. Capturar subida y regreso al baseline, además de resultado y comprobaciones finales.
5. **Solicitudes y alertas.** Acompañar 429 con solicitudes por servicio/pod, 5xx, latencia y scrape. Una tasa en req/s no es el conteo total; la latencia media no es p95. Los 429 esperados demuestran rechazo por cuota, no indisponibilidad general. No alterar umbrales para obtener una captura Firing.
6. **Red y Service.** Comprobar conexiones nuevas directas a Pharmacy y roles por Gateway antes, durante y después; conexiones ya abiertas del Gateway pueden sobrevivir. Distinguir timeout de conexión rechazada. Si se ejecutó `durante` después de la reversión, preservar la fila original y añadir otra consulta `despues`; usar timestamps para interpretarlas.
7. **Bitácora y cierre.** Registrar solo lo observado, con hora actual. Una revisión tardía se identifica como retrospectiva, sin retrodatación ni reconocimiento inventado. Después de confirmar recuperación y limpieza, retirar únicamente clientes propios con identidad comprobada y detener el perfil conservando datos. Conservar captura de cierre y no confundir apagar el laboratorio con borrar sus volúmenes.
