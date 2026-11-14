# Almacenamiento: refuerzo de I/O sostenida — 14/11/2026

**Estado: PASS del ensayo nuevo sobre PharmaGo, con I/O sostenida observada y limpieza verificada.** [Resumen del resultado real](summary.json), [pruebas e intentos previos](checks.json), [reporte original comprimido](report.json.gz), [journal](journal.json.gz) y [hashes del paquete](manifest.json). Los seis ensayos anteriores siguen siendo evidencia de sus fuentes originales; no se presentan como ejecuciones de este mecanismo. Este PASS no demuestra saturación del dispositivo ni resuelve por sí solo la interpretación académica de “sobrecarga”.

El resultado también se añadió como complemento al [documento de los seis ensayos con capturas](../issue-16-20261113/README.md#complemento-de-almacenamiento-del-14112026) y a su [ficha de almacenamiento](../issue-16-20261113/ensayos/storage/README.md). Las 37 capturas anteriores y los archivos originales de las corridas permanecen intactos; la [verificación de la actualización](operator-doc-update.json) conserva sus hashes y el [manifiesto original](operator-package-original-manifest.json).

## Brecha observada

En el [ensayo del operador del 13/11](../issue-16-20261113/ensayos/storage/README.md), el script escribió una vez 32 MiB y esperó. El reporte original registra ocupación del pod de 0,0977 MiB antes, máximo de 32,1133 MiB durante y 0,1055 MiB al final. El filesystem del nodo observado tenía un mínimo aproximado de 895,02 GiB libres: los 32 MiB eran alrededor del 0,0035% de ese espacio. Las 16 sondas durante la inyección devolvieron 200. Es evidencia de escritura, ocupación y limpieza, no de saturación de capacidad.

## Cambio del mecanismo

El escenario `storage` del [controlador](../../../Implementacion%20K8S/Codigo/chaos-engineering/chaos.py) conserva su categoría y destino Pharmacy. El [agente](../../../Implementacion%20K8S/Codigo/chaos-engineering/fault.sh) reescribe un archivo exclusivo bajo `/tmp` usando `conv=notrunc,fdatasync`. Mantiene un solo escritor, tamaño de archivo de hasta 64 MiB y presupuesto máximo de 1024 MiB lógicos escritos por ensayo; espacia las pasadas para cubrir la duración, entre 30 y 180 s en el controlador. Comprueba el margen de 1 GiB libre en cada pasada. La ruta queda fuera de PV/PVC.

El agente publica pasadas completadas, bytes acumulados e instantes de primera/última escritura. Cada nuevo spawn y registro de PID se realiza bajo el mismo lock que cleanup, comprobando cancelación y deadline; los archivos de progreso propios se retiran al limpiar. Se conservan la recuperación por identidad y los controles del controlador.

El [probe](../../../Implementacion%20K8S/Codigo/chaos-engineering/probe.py) consulta el contador `container_fs_writes_bytes_total` del pod y su tasa de un minuto, con los filtros cAdvisor usados por el dashboard Infra. El preflight exige baseline I/O del pod antes de inyectar. El veredicto requiere progreso repetido durante la ventana, al menos tres pasadas y la mitad de la duración cubierta, contador creciente sin reset y dos muestras con tasa superior al baseline en más de 1024 bytes/s. Ese margen distingue cambio observable; no es una definición de saturación.

El reporte agrega `storageWorkload` y, solo si se acredita el efecto, `storageEvidence.classification=sustained_io_observed`, con el progreso, delta de contador y tasas observadas. `deviceSaturation` queda null. El contador del pod también puede incluir escrituras de la aplicación: no se presenta como medición exclusiva del generador. Las sondas conservan códigos, validación de contenido y latencias antes/durante/después. La recuperación sigue exigiendo 120 s estables, alertas sanas y comparación de recursos/datos.

Referencias técnicas: [GNU dd: notrunc/fdatasync](https://github.com/coreutils/coreutils/blob/master/src/dd.c) y [métricas cAdvisor](https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md). I/O sostenida observada no equivale por sí sola a dispositivo saturado, disco lleno, fallo de aplicación o aceptación académica del requisito de sobrecarga. El ensayo real deberá conservar esa distinción y documentar el efecto encontrado.

## Pruebas realizadas

- **54/54 pruebas del controlador**, sin infraestructura. Las nuevas regresiones rechazan escritura única, progreso fuera de la ventana, falta de telemetría del destino, reset de contador, tasa sin incremento, NaN, exceso de presupuesto y duración insuficiente. El caso positivo verifica que el resultado no declare saturación.
- **7/7 pruebas del agente real**, en un contenedor Docker efímero con 256 MiB, 0,5 CPU, 64 procesos como límite, red deshabilitada y sin volúmenes de aplicación. Las nuevas pruebas verifican varias pasadas sobre el mismo archivo, tamaño estable, progreso, deadline y limpieza; las anteriores cubren cancelación/aborto y propiedad. El contenedor fue retirado al terminar.
- Fuente ejecutada: rama `codex/storage-sustained-io`, base `baec66bb304fa5d923fb3e604e49a7d5fcacc6bc`, árbol modificado. Los hashes de las cinco fuentes y de los logs originales locales están en `checks.json`; no se atribuye la ejecución a un commit limpio.

La [comparación de fuentes publicadas](source-publication.json) conserva los hashes originales de la ejecución y los de los blobs preparados para Git. `core.autocrlf=true` normaliza CRLF a LF en los cuatro archivos Python; se comparó su contenido completo tras esa normalización. `fault.sh` conserva los mismos bytes. Los reportes originales y sus hashes permanecen intactos. La [capacidad y versiones del equipo](environment.json) se registran por separado.

Se incluyen los logs originales de las [54 pruebas del controlador](storage-controller-final.log) y las [siete del agente](storage-agent-tests.log), con hashes en `checks.json` y `manifest.json`. Se comprobó que el paquete no contiene las credenciales empleadas. No se cambió código de producción, imágenes o configuración de PharmaGo para estas pruebas.

## Intentos de laboratorio completo

Se inició Docker Desktop y se reanudó exclusivamente el perfil existente `pharmago-issue17-validation`, sin cambiar sus límites ni sus datos. Durante el arranque se observaron unos 1,1 GiB libres; la comprobación registrada antes de detenerlo dio **943.869.952 bytes disponibles**, por debajo de los **2.147.483.648 bytes** del precheck existente. Se clasificó **BLOCKED_BEFORE_INJECTION**, no como fallo del nuevo estímulo ni ensayo aprobado.

En un segundo intento se observaron unos 5 GiB libres con el perfil detenido y se reanudó el mismo perfil. Al terminar de cargar el stack, el precheck de capacidad volvió a detectar menos de 2 GiB. El helper se detuvo antes de crear clientes o ejecutar la inyección y confirmó la parada del perfil. Ambos intentos se conservan separados en `checks.json`; no se presentan como fallos de escritura ni como pruebas de efecto aprobadas.

Después de que el usuario indicó que liberaría memoria, se realizó un tercer intento. Antes de iniciar Docker se observaron aproximadamente 10,38 GiB libres y, durante la carga de pods, el helper registró una caída de 6,03 a 2,81 GiB. La siguiente comprobación volvió a quedar por debajo de 2 GiB con solo seis de diecisiete pods Ready. Se detuvo el perfil antes de crear clientes o inyectar. El tercer intento se conserva por separado en `checks.json`; no se afirma que se haya ejecutado la carga.

En esos tres intentos no se crearon clientes ni se ejecutó el controlador con `--execute` sobre PharmaGo. Se detuvo el perfil conservando datos y se retiró la selección global de contexto que el arranque había establecido; al iniciar no había contexto activo. No se redujo el margen ni se desactivó observabilidad para conseguir una ejecución.

Después de los dos primeros intentos se solicitó apagar Docker Desktop, que inicialmente estaba apagado. El servidor dejó de responder y desapareció `vmmemWSL`, pero la CLI/plugin de apagado siguieron esperando más de tres minutos; se terminaron únicamente esos procesos de CLI identificados por comando y hora de inicio. No se forzaron procesos de aplicación o del motor. Ese cierre previo se conserva en `checks.json`; no se cuenta como resultado del escenario.

## Cuarto intento: resultado real

El diagnóstico encontró caché retenida dentro de WSL. Con el perfil detenido y, una segunda vez, durante su arranque, se ejecutó `sync` seguido de `echo 3 > /proc/sys/vm/drop_caches` en la distribución `docker-desktop`. Es una operación de diagnóstico sobre caché limpia, documentada por el [kernel Linux](https://docs.kernel.org/admin-guide/sysctl/vm.html#drop-caches). Ambas operaciones ocurrieron antes del baseline funcional y de la inyección; no se repitieron durante el ensayo. No se cambió `.wslconfig`, el margen de memoria, los límites de Docker/Kubernetes ni la observabilidad. La app de esta conversación permaneció abierta.

Los diecisiete pods quedaron Ready y las cinco reglas sanas/inactivas antes de ejecutar. El run `c70c8cae26144765974aa922c828bc86` comenzó la inyección a las **17:40:35 UTC** y retiró el estímulo a las **17:41:42 UTC**. La duración solicitada fue 60 s; la retirada y muestreo agregan tiempo al intervalo registrado. El preflight registró la memoria disponible exacta en `summary.json`.

- El agente terminó con **29 pasadas y 928 MiB lógicos escritos** sobre el mismo archivo de 32 MiB; primera/última escritura separadas por 58 s. La última muestra activa utilizada para corroborar el efecto registró **26 pasadas, 832 MiB y 52 s**. Son dos puntos de observación distintos, no contadores contradictorios.
- El contador del pod aumentó **838.971.392 bytes**, unos 800,11 MiB. La tasa de un minuto pasó de baseline 0 a un pico de unos **15,54 MiB/s**. La métrica puede incluir escritura de la aplicación y su muestreo no coincide exactamente con el contador lógico del agente.
- **61/61 sondas HTTP 200 y válidas**: tres antes, dieciocho durante y cuarenta en recuperación. Las latencias se conservan en el reporte; no se infiere mejora de rendimiento comparando un baseline corto de arranque con la ventana caliente.
- Se verificaron **125,33 s estables**, desde 17:41:45 hasta 17:43:50 UTC, con alertas sanas/inactivas. El inventario de PVC, PV y deployments permaneció igual. Resultado final: `PASS`, `cleanup=verified`.
- El helper comprobó por separado la ausencia de archivo/control y procesos del run, eliminó únicamente sus dos clientes comprobando UID y detuvo el perfil. El [registro de sesión](session.json.gz) conserva esas comprobaciones. Se restauró el contexto global a no seleccionado.

Después se pidió el cierre normal de Docker Desktop con timeout de 30 s. La CLI informó timeout porque aún había procesos Desktop/backend; no se forzó su terminación. La comprobación posterior encontró la VM WSL ausente y el motor sin respuesta en cinco segundos; no se confirmó la salida de todos los procesos de Desktop. Este límite del cierre de la herramienta se registra en `checks.json` por separado del PASS y de la parada confirmada del laboratorio.

La ejecución fue local y asistida por Codex, sobre la base `baec66bb304fa5d923fb3e604e49a7d5fcacc6bc` con árbol modificado y hashes de fuentes registrados. No es validación independiente de otro integrante ni una ejecución desde commit limpio. No se reemplazó la evidencia histórica del 13/11. El resultado acredita un estímulo sostenido de I/O y continuidad funcional en este entorno; `deviceSaturation` permanece null. La justificación académica de si esta carga acotada satisface “sobrecarga” sigue siendo una revisión explícita del equipo/docente.

## Reproducción

Con suficiente memoria libre para conservar el margen del controlador, preparar el laboratorio y credenciales según [la guía](../../../Implementacion%20K8S/Codigo/chaos-engineering/README.md). Revisar primero el plan, desde la raíz:

```powershell
python 'Implementacion K8S/Codigo/chaos-engineering/chaos.py' storage --context pharmago-issue17-validation --operator '<operador>' --duration 60 --megabytes 32
```

Después del baseline y prechecks, agregar `--execute` para medir un archivo de 32 MiB reescrito repetidamente. Conservar el reporte/journal del nuevo run ID y cualquier intento bloqueado/fallido. La preparación de caché anterior describe este equipo; no forma parte del generador ni se debe ejecutar durante una medición.
