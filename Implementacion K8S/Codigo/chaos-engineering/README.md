# Ingeniería del caos de PharmaGo

Controlador de los seis escenarios de #17. **Seis ensayos reales PASS en un laboratorio local con Calico**, con restauración estable y limpieza independiente. Ver [resultados, intentos fallidos y alcance](../../../docs/evidence/issue-17-20261112/fix-after-review/README.md), [plan de incidentes](../../../docs/baseline-incidents.md) y [runbooks](../../../docs/runbooks/incidentes.md). Red y desconexión se verifican sobre conexiones nuevas al backend, registrando por separado la ruta Gateway existente; no se afirma caída total de la aplicación.

## Simulación y pruebas sin infraestructura

Desde la raíz del repo, Python 3.10+; sin dependencias Python adicionales:

```powershell
$chaos = 'Implementacion K8S/Codigo/chaos-engineering'
python "$chaos/chaos.py" cpu --context pharmago-issue17
python -m unittest discover -s $chaos -p 'test_*.py' -v
```

`test_chaos.py` contiene 45 pruebas sin infraestructura. Las cinco pruebas de `test_fault_agent.py` se omiten salvo opt-in explícito: ejecutan el shell real en un contenedor efímero con 256 MiB, 0,5 CPU, sin red y sin datos de la aplicación. Requieren una imagen local con las herramientas del contenedor Pharmacy (incluido `flock`):

```powershell
$env:PHARMAGO_AGENT_TEST_IMAGE = 'pharmago-baseline/pharmacy:local'
python -m unittest discover -s $chaos -p 'test_fault_agent.py' -v
Remove-Item Env:PHARMAGO_AGENT_TEST_IMAGE
```

Comprueban cancelación antes del arranque de CPU/RAM/disco, aborto con procesos activos, plazo absoluto incluso después de retirar el tombstone, corte de un agente ya iniciado y preservación de controles ajenos. No son los seis experimentos sobre PharmaGo. El workflow `Chaos safety` repite los tests y wrappers en Linux, con un agente aislado sobre la imagen base .NET 6.

Sin `--execute` solo se imprime el plan: no se llama a kubectl/Docker ni se escribe en el clúster. Un contexto no especificado, límites inválidos o un operador no identificado para ejecución se rechazan. Los cuatro scripts originales ahora son wrappers de este controlador; **ya no aceptan los argumentos posicionales anteriores** ni disparan carga al ejecutarlos sin opciones. Bash usa `PHARMAGO_PYTHON` o `python`.

| Escenario | Wrapper | Efecto y reversión |
|---|---|---|
| `requests` | `load-requests.sh` | GET de catálogo desde un pod de carga separado; máximo 240 solicitudes, 4 workers y 4 req/s, sin reintentos. Deadline y cancelación de su PID propio |
| `cpu` | `cpu-spike.sh` | Dos bucles dentro de un pod Pharmacy con límites CPU/RAM; PID con identidad de ensayo, trap y timeout |
| `ram` | `ram-spike.sh` | Bloque residente retenido por dd/FIFO, sin fallback a disco; verifica cgroup finito y margen antes de asignar |
| `storage` | `volume-spike.sh` | Hasta 64 MiB en directorio exclusivo de /tmp no montado; exige 1 GiB adicional libre y retira solo sus archivos |
| `network` | `network-interruption.sh` | NetworkPolicy bloquea conexiones nuevas de clientes/Gateway a Pharmacy; se mide una conexión nueva directa y, separadamente, el Gateway que puede reutilizar conexiones. Retira solo su política |
| `disconnect` | `component-disconnect.sh` | Añade un selector imposible al Service Pharmacy, sin modificar pods/DB; remueve solo su clave mediante JSON Patch con comprobación de identidad |

CPU, RAM y disco afectan un pod Pharmacy, no todas sus réplicas. Red y desconexión aíslan conexiones nuevas a Pharmacy; el cliente mide el Service directamente y registra por separado catálogo/roles vía Gateway. Una conexión existente puede sobrevivir al cambio de política o endpoints: no se presume que todo tráfico del Gateway se interrumpa. Ningún escenario borra PV/PVC, cambia réplicas, toca SQL, hace seed ni escribe compras. La inyección de disco es ocupación acotada, no llenar el disco del host. No se promete provocar todas las alertas con los valores predeterminados: se registran sus estados reales y no se fuerzan umbrales para mejorar el resultado.

## Entorno necesario antes de ejecutar

Usar un clúster local **dedicado a pruebas**, con aplicación sana, datos de demostración, OTLP, Prometheus, Grafana (cinco reglas sanas/inactivas), Jaeger, Elasticsearch/Kibana y métricas de recursos completos. Seguir [despliegue](../k8s/README-k8s.md). Preparar/verificar la instalación con capacidad suficiente; este controlador no inicia Minikube ni construye imágenes.

La preparación original observó 8 GiB físicos y 1,2 GiB libre con Docker ocioso. La revisión posterior preparó el laboratorio completo con Calico en un equipo de aproximadamente 16 GiB: el primer intento se rechazó con 1,67 GiB libres; después de liberar memoria, hubo aproximadamente 3,5–4 GiB disponibles y se ejecutaron los seis ensayos. El precheck exige 2 GiB libres en el host, nodos Ready sin presión, al menos 256 MiB libres por nodo y 1 GiB libre en los filesystems de datos observados. Son pisos de aborto, no una garantía de dimensionamiento ni permiso para llenar memoria hasta ese límite. Ver [capacidad y resultados](../../../docs/evidence/issue-17-20261112/fix-after-review/README.md).

El escenario de red requiere un CNI que **aplique** NetworkPolicy, por ejemplo Calico. Crear un objeto NetworkPolicy sin enforcement no corta tráfico. Un perfil nuevo puede prepararse con el CNI apropiado según [la guía oficial de Minikube](https://minikube.sigs.k8s.io/docs/handbook/network_policy/); no cambiar a ciegas el CNI de un clúster con datos. El runner rechaza políticas existentes en el namespace para no asumir cómo se combinan. Si la política no causa efecto observado, el resultado es FAIL. La aplicación sobre conexiones ya establecidas depende del CNI y debe comprobarse, no inferirse del objeto creado. [Semántica de NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

La API debe estar en HTTPS y en localhost/loopback o `kubernetes.docker.internal`; no se aceptan endpoints remotos. Ejecutar los ensayos desde la computadora que aloja ese laboratorio. No se opera una nube ni se cambia el contexto global.

## Preparación explícita del laboratorio

No ejecutar estos pasos sobre un clúster compartido o una instalación que otro integrante esté usando. Verificar contexto, propietario y capacidad antes de identificar el namespace como laboratorio:

```powershell
$ctx = '<contexto-local-verificado>'
$chaos = 'Implementacion K8S/Codigo/chaos-engineering'
kubectl --context $ctx get nodes -o wide
kubectl --context $ctx -n pharmago get pods,pvc -o wide
kubectl --context $ctx label namespace pharmago pharmago.io/chaos-lab=true
# Comprobar que estos nombres no estén ocupados; no adoptar un pod ajeno.
kubectl --context $ctx -n pharmago get pod pharmago-chaos-client pharmago-chaos-load --ignore-not-found
kubectl --context $ctx create -f "$chaos/clients.yaml"
kubectl --context $ctx -n pharmago wait pod/pharmago-chaos-client pod/pharmago-chaos-load --for=condition=Ready --timeout=120s
kubectl --context $ctx -n pharmago get pod pharmago-chaos-client pharmago-chaos-load -o json
```

Guardar UIDs de los clientes recién creados en la ficha. Si `create` falla, comprobar qué creó; no sobrescribir el otro pod ni continuar. Los clientes tienen CPU/RAM limitadas, sin token de ServiceAccount ni privilegios, raíz de solo lectura, /tmp efímero para control y deadline de cuatro horas. Su imagen tiene tag explícito; registrar también el imageID/digest realmente ejecutado. Mantenerlos como fixture del laboratorio durante los seis ensayos, retirar solo esos dos pods propios al terminar y verificar su desaparición; no borrar namespace ni volúmenes. Si ya existían, confirmar con el propietario su identidad/uso antes de reutilizarlos o retirarlos.

Cargar `PHARMAGO_TEST_PASSWORD` y `PHARMAGO_GRAFANA_PASSWORD` en variables locales de entorno, sin valores en argumentos, archivos versionados, captura de terminal ni evidencia. `--username` identifica el usuario existente (por defecto admin). El runner envía credenciales al cliente por stdin, sin almacenarlas en reportes. No obtiene ni publica Secrets del clúster.

Antes de inyectar completar roles, canal, hipótesis, baseline y presupuestos en [la ficha](../../../docs/templates/incidente.md). `--operator` solo registra el nombre declarado; **no inventa un reconocimiento humano ni una comunicación**. El campo `tAck` automatizado queda null; la persona registra su reconocimiento real en la bitácora. Si trabaja una persona sola, debe poder abortar y después diagnosticar, según el plan.

## Ejecutar uno a la vez

```powershell
# Primero revisar el plan sin --execute.
python "$chaos/chaos.py" requests --context $ctx --operator '<persona>' --duration 60
# Solo con el precheck y el laboratorio verificados:
python "$chaos/chaos.py" requests --context $ctx --operator '<persona>' --duration 60 --execute
python "$chaos/chaos.py" cpu --context $ctx --operator '<persona>' --duration 130 --execute
python "$chaos/chaos.py" ram --context $ctx --operator '<persona>' --megabytes 32 --duration 60 --execute
python "$chaos/chaos.py" storage --context $ctx --operator '<persona>' --megabytes 32 --duration 60 --execute
python "$chaos/chaos.py" network --context $ctx --operator '<persona>' --duration 60 --execute
python "$chaos/chaos.py" disconnect --context $ctx --operator '<persona>' --duration 60 --execute
```

No pegar el bloque entero para continuar tras un fallo: ejecutar una línea, comprobar código de salida y evidencia, completar ficha/postmortem y recién entonces pasar al siguiente. Detener si un comando falla. No reducir los pisos de capacidad ni omitir observabilidad para conseguir PASS.

Límites no ampliables por flags: duración 1..180 s, RAM hasta 128 MiB y hasta un tercio del límite del contenedor con margen adicional, disco hasta 64 MiB, 240 solicitudes y cuatro workers. El pod elegido requiere CPU >0 y hasta un core, y memoria entre 64 y 512 MiB. El directorio de inyección es `/tmp/pharmago-chaos-<id-aleatorio>`; no se toca un mount bajo /tmp ni un volumen de negocio.

## Reversión y aborto

Antes de mutar se escribe `.runtime/chaos/<runId>/journal.json` y se adquiere un lock de laboratorio. Un watchdog local independiente debe confirmar preparación. Revierte si vence el plazo de inyección; al presupuesto total de 600 s intenta también retirar el lock propio. Los procesos remotos tienen timeout/deadline independientes. El generador de requests usa cancelación persistente para impedir arranques tardíos después de un aborto.

Ctrl+C/SIGTERM solicita aborto y ejecuta finally: detener generador, limpiar agente, quitar política o selector propios y verificar identidad. CPU/RAM/disco también conservan cancelación persistente; `flock` serializa comprobación, arranque, registro de PIDs y limpieza. Todos los RPC de carga reciben un deadline absoluto: un arranque remoto tardío no puede reiniciar el estímulo después del aborto o del vencimiento. El envío de scripts por stdin conserva bytes LF desde Windows; no se usa traducción de texto CRLF.

Con un RPC incierto de requests, CPU, RAM o disco se mantienen cancelación, lock y journal sin declarar `cleanup=verified`, hasta confirmar su fin o alcanzar deadline + 15 s. Antes de retirar los controles, el controlador confirma que el watchdog terminó; si no lo confirma, requiere recuperación manual. Puede haber hasta 12 s de solicitudes HTTP ya en vuelo; no se considera que el aborto revoque operaciones ya enviadas. El watchdog no puede reparar durante apagado del host o API server inaccesible: queda journal y puede requerirse recuperación manual. No se garantiza limpieza por solo cerrar una terminal.

```powershell
python "$chaos/chaos.py" --recover '.runtime/chaos/<runId>/journal.json' --execute
```

La recuperación es idempotente, comprueba namespace/UID/propietario y no adopta recursos ajenos. Un Service reemplazado o un selector concurrente detienen la reparación sin sobrescribirlos. El borrado de política/lock usa DeleteOptions con precondiciones UID y resourceVersion. Para cualquier RPC de carga incierto se conserva la cancelación hasta deadline + 15 s; repetir recuperación luego de ese plazo, sin borrar el control a mano ni correr recuperaciones simultáneas. Con `MANUAL_RECOVERY_REQUIRED` no iniciar otro ensayo. Escalar por [los runbooks](../../../docs/runbooks/incidentes.md); no borrar datos ni vaciar reglas generales de red.

## Resultados y aceptación

`report.json` guarda muestras de catálogo/roles/login, códigos/latencias sin cuerpos, fingerprints, imágenes/UIDs, métricas/alertas, eventos, limpieza y hashes de los scripts. Credenciales y tokens quedan fuera. El journal no contiene credenciales. Revisar y sanitizar los archivos antes de copiarlos a `docs/evidence/`; el log local del watchdog tampoco se publica sin revisión.

PASS exige efecto observado (429 en carga; incremento real de CPU/RAM; bytes de disco; conexiones nuevas al Service Pharmacy interrumpidas y roles vía Gateway funcionales en red/desconexión), reversión, 120 s de comprobaciones funcionales sin fallos ni nuevos reinicios, alertas sanas/inactivas, catálogo/roles sin cambios y PV/PVC/configuración conservados. El resultado de catálogo vía Gateway se registra separadamente, aunque conserve conexiones previas. Si el CNI ignora la política para conexiones nuevas, un agente no produce incremento medido, falta telemetría, se rompe una comparación o falla limpieza, el resultado es FAIL. Las duraciones solicitadas y los intervalos reales de reversión se registran por separado: las consultas/RPC pueden añadir latencia; el watchdog mantiene su deadline independiente.

Las [seis fichas reales](../../../docs/evidence/issue-17-20261112/fix-after-review/README.md) conservan hipótesis, comandos, efectos, tiempos, alertas, recuperación y limpieza. Para otra ejecución, copiar la [ficha](../../../docs/templates/incidente.md) y completar comunicaciones/postmortem reales. Separar inyección solicitada, efecto observado, pod Ready, primera respuesta válida y ventana estable. No inferir TTA, corrección causal o promedios de las acciones automáticas. La evidencia técnica local de #17 está disponible para revisión e integración; la validación humana de roles/comunicaciones de #16 sigue pendiente, con tAck null y sin mensajes externos inventados.
