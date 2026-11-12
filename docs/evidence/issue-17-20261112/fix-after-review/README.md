# Corrección del aborto y validación posterior de #17

## Fallos reproducidos y corregidos

La revisión identificó una carrera: el controlador podía enviar un RPC de CPU/RAM/disco, abortar antes del arranque remoto y declarar limpieza verificada con el RPC aún pendiente. Se liberaba el lock y terminaba el watchdog; un arranque tardío podía reintroducir carga después del aborto.

Los tres agentes de recursos ahora conservan cancelación por run-id, serializan el check/arranque/registro de PIDs/limpieza mediante `flock` y reciben un plazo absoluto. No pueden comenzar después de una cancelación ni reiniciar el estímulo después de vencer el plazo, aunque se haya retirado el tombstone. El controlador trata por igual los RPC inciertos de requests, CPU, RAM y disco: conserva controles/lock/journal y exige recuperación manual en lugar de declarar limpieza verificada. Solo retira los controles con RPC finalizado o deadline + 15 s, después de confirmar el fin del watchdog.

Al ejecutar el shell real desde Windows también se reprodujo un fallo de transporte: `text=True` traducía LF a CRLF en stdin y `sh` rechazaba el script. El controlador envía ahora bytes UTF-8 y decodifica únicamente la salida. Una regresión verifica que stdin conserve LF.

## Pruebas aprobadas

- **41 tests del controlador**, incluidos aborto inmediatamente después del despacho, timeout, conservación del lock, deadline vencido, segunda reversión tras RPC terminado y watchdog que no confirma parada. Sin Kubernetes ni carga.
- **Cinco tests del agente real en Docker**, con subcasos CPU/RAM/disco: cancelación antes de arrancar; deadline vencido incluso después de retirar cancelación; aborto de procesos activos; corte de un agente activo al vencer el plazo; preservación de un control ajeno.
- El contenedor efímero usó la imagen local Pharmacy, 256 MiB, 0,5 CPU, límite de 64 procesos y red deshabilitada. Se comprobaron ausencia de procesos identificados y payload después del aborto y retirada de controles al finalizar. El contenedor propio se eliminó; no accedió a datos ni servicios PharmaGo.
- Sintaxis de siete scripts shell y seis wrappers en dry-run aprobados.
- CI [Chaos safety, run 43311565405](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/actions/runs/43311565405) aprobado en Ubuntu/Python 3.11, incluido el agente aislado sobre la misma imagen base .NET 6. La ejecución local usa Python 3.14.

[Log controlador](controller-tests.txt) · [Log agente](agent-tests.txt) · [Commit, hashes y conteos](checks.json).

Los hashes corresponden a los archivos locales ejecutados; el commit identifica el contenido Git. Windows/Linux pueden materializar distintos finales de línea en archivos Python. Los scripts shell se conservan LF por `.gitattributes`.

## Laboratorio para los seis ensayos integrales

En esta validación el equipo dispone de aproximadamente 15,95 GiB físicos y el motor Docker de 7,73 GiB. Se creó un perfil nuevo `pharmago-issue17-validation`, de un nodo con presupuesto de 6144 MiB/4 CPU y Calico, sin modificar los perfiles anteriores ni sus datos. Esto no prueba separación física ni disponibilidad multinodo.

Las cuatro imágenes se construyeron y cargaron desde el commit limpio `28b3b8b`, tag `chaos-fix-20261112-01`; las modificaciones posteriores hasta `5c42fc0` agregan tests, CI y documentación, sin cambiar el código de aplicación o del controlador. La base usa las versiones operativas declaradas por el repositorio. El primer apply agotó 240 s durante la descarga inicial de SQL; se conservó la instalación parcial, se cargó la imagen fijada desde la caché local y se retomó el mismo apply con el timeout soportado de 600 s. No se redujeron pisos de capacidad ni controles del runner. SQL y migraciones terminaron saludables y se insertó el seed docente sin reset.

**Los seis ensayos sobre la aplicación todavía no están completados en este registro.** Los tests del agente aislado no acreditan alertas, impacto funcional, restauración estable de PharmaGo ni la aplicación humana del plan de incidentes. #17 y #16 permanecen abiertas; se anexarán los resultados reales disponibles y sus límites sin inventar tiempos de reconocimiento ni comunicaciones.

## Primer intento integral: precheck bloqueado por memoria libre

El apply completo terminó con todos los pods Ready, SQL con datos de demostración, Elasticsearch green, Jaeger disponible, nueve targets `up=1`, métricas de CPU/RAM/storage de 19 pods, métricas de nodo y cinco alertas sanas/inactivas. La captura [health-before.json](health-before.json) registra ese estado y **1,67 GiB libres en el host**. La dotación total de 16 GiB no equivale a memoria disponible para inyectar carga.

Se invocó `requests --context pharmago-issue17-validation --duration 60 --megabytes 32 --execute` mediante el helper local que proporciona las credenciales por entorno, desde el commit limpio `9f81d3c967d04c0a88974cde39ceda43490d8da5`, el 12/11/2026 a las 18:44:48 de Uruguay. El [reporte original](precheck-blocked.json) terminó con exit 1/status FAIL por `Precheck: menos de 2 GiB de RAM libre en el host; no se inyectará carga`.

La clasificación de aceptación de este intento es **BLOCKED antes de inyección**, no un experimento de requests aprobado o un fallo observado de PharmaGo: no hay evento `inject-requested`, muestras, observaciones, journal ni lock de ensayo. Se comprobó la ausencia del ConfigMap de lock. `liveValidation=true` en el reporte identifica el modo solicitado, no prueba que se haya llegado a inyectar. El piso de 2 GiB se conservó y no se continuó con CPU/RAM/disco/red/desconexión mientras faltara ese margen.
