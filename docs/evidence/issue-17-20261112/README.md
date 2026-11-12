# Issue #17: implementación y verificaciones sin clúster

**Revisión posterior:** la carrera de aborto está corregida y pasaron 41 tests del controlador y cinco del agente real aislado, también en CI Linux. Ver [correcciones y preparación del laboratorio nuevo](fix-after-review/README.md). El resto de este archivo conserva la inspección original, realizada con menos capacidad y sin clúster.

Rama `feature/issue-17-ingenieria-caos`, desde `54d5a17c68cb7ede122b92862ad156163a0b09d9` de `obligatorio` (PR #36 integrado). Fecha de revisión: **12/11/2026**. Los checks se hicieron con el árbol modificado; los hashes en [offline-checks.json](offline-checks.json) identifican los archivos verificados. No se presentan como imágenes desplegadas.

## Estado real

**Implementación preparada; seis ensayos sobre PharmaGo NO ejecutados.** #17/R07 y la validación integral de #16/R06 siguen pendientes. No hay resultados de impacto, Firing/OK, recuperación o limpieza de fallas reales en este incremento.

Se inició Docker Desktop para inspeccionar capacidad. El motor tiene 4.026.466.304 bytes (aprox. 3,75 GiB) y esta PC, 8.286.953.472 bytes físicos (aprox. 7,72 GiB). En la captura final había 1.528.782.848 bytes libres (aprox. 1,42 GiB), cero contenedores activos y cero contextos Kubernetes configurados. Al inicio se habían observado solo unos 300 MiB libres, y luego alrededor de 1,2 GiB. Los valores cambian con el uso del equipo. [Captura sanitizada](environment.json).

El margen observado está por debajo del piso de 2 GiB libres del controlador y no justifica iniciar el stack completo ni saturación. Se difieren las pruebas a un laboratorio local con capacidad. El usuario fue informado del riesgo de lentitud, OOM y bloqueo temporal; no se cambiaron límites globales de Docker/WSL, no se cerraron sus aplicaciones ni se inició Minikube, el baseline o contenedores de caos. Los datos/volúmenes existentes no se operaron.

## Cambios

- [Controlador](../../../Implementacion%20K8S/Codigo/chaos-engineering/chaos.py), [cliente](../../../Implementacion%20K8S/Codigo/chaos-engineering/probe.py) y [agente acotado](../../../Implementacion%20K8S/Codigo/chaos-engineering/fault.sh).
- Los cuatro scripts heredados ahora invocan el controlador; se agregan wrappers de red y desconexión interna. La interfaz anterior deja de aceptarse, para evitar ejecuciones accidentales sin contexto/límites.
- [Guía de laboratorio, hipótesis/efectos y recuperación](../../../Implementacion%20K8S/Codigo/chaos-engineering/README.md), fixtures de clientes con límites y actualización de matriz/runbooks.
- Simulación por defecto sin herramientas externas; ejecución explícita en namespace de laboratorio identificado y API local. No hay destinos HTTP libres, borrado de datos ni escalado de DB.
- Journal previo a mutación, lock, watchdog independiente, deadline de agentes y cancelación del generador; recuperación por UID/propietario y precondiciones de DELETE. Fallas de identidad, incertidumbre de RPC o limpieza se conservan como FAIL/recuperación pendiente.

## Qué se comprobó

1. **35 tests aprobados**, sin clúster/HTTP real. Cubren límites inválidos, simulación sin llamadas externas, memoria/condiciones de nodos, identidad de namespace/pod/Service, rechazo a borrar recursos ajenos, selector propio, UID/resourceVersion del DELETE, parada del cliente original, finalmente de aborto y limpieza fallida, clasificación de efecto ausente y exclusión de credenciales/tokens de respuestas.
2. **Siete scripts shell** pasan `bash -n`. Se ejecutaron los seis wrappers únicamente en simulación y emitieron `DRY_RUN_OFFLINE`, sin kubectl, Docker ni inyección.
3. Los módulos Python compilan/importan. Los **dos pods YAML** se comprueban con la dependencia ya fijada por Kubernetes (`PyYAML==6.0.3`): namespace, recursos, deadline, ausencia de token, permisos y filesystem.
4. Revisión de referencias/documentación y diff. La reconstrucción histórica de #16 y la evidencia de incrementos anteriores no se reutilizan como resultados de estos escenarios.

[Resumen de checks y hashes](offline-checks.json). Los tests usan dobles para Kubernetes/HTTP y no validan el comportamiento del CNI, las imágenes o los agentes en un contenedor Linux real.

## Cómo reproducir las verificaciones

Desde raíz, sin iniciar ningún entorno:

```powershell
$chaos = 'Implementacion K8S/Codigo/chaos-engineering'
python -m unittest discover -s $chaos -p 'test_*.py' -v
python -m py_compile "$chaos/chaos.py" "$chaos/probe.py"
python "$chaos/chaos.py" requests --context pharmago-issue17
python "$chaos/chaos.py" cpu --context pharmago-issue17
python "$chaos/chaos.py" ram --context pharmago-issue17
python "$chaos/chaos.py" storage --context pharmago-issue17
python "$chaos/chaos.py" network --context pharmago-issue17
python "$chaos/chaos.py" disconnect --context pharmago-issue17
git diff --check
```

En Bash: `for f in 'Implementacion K8S/Codigo/chaos-engineering/'*.sh; do bash -n "$f" || exit 1; done`. Las pruebas YAML requieren el venv del flujo Kubernetes; el controlador y sus unit tests solo usan biblioteca estándar.

## Ensayos que faltan antes de aceptar #17

| Caso | Estado | Evidencia real requerida |
|---|---|---|
| Requests | NOT RUN | Conteo por IP de carga y cliente legítimo, 429/Retry-After, cuotas, recuperación sin desactivar protección |
| CPU | NOT RUN | Incremento medido en el pod/nodo, PID, efecto funcional, estados de alerta y retirada de procesos |
| RAM | NOT RUN | Bloque residente/cgroup, margen y consumo observado, respuesta, retirada sin fallback a disco |
| Disco | NOT RUN | Bytes exactos en directorio propio, filesystem/espacio, impacto y ausencia del artefacto tras revertir |
| Red | NOT RUN | NetworkPolicy efectivamente aplicada por CNI, catálogo interrumpido, roles atendidos, retirada y conectividad restaurada |
| Desconexión interna | NOT RUN | Service sin endpoints para Pharmacy, impacto parcial, selector y acceso restaurados sin alterar pods/DB |

En todos: baseline sano y versión identificada, presupuesto y roles/canal, ficha con señal inicial y tiempos registrados, decisiones/comunicaciones reales, 120 s de estabilidad, datos/UIDs/configuración comparados, alertas evaluándose y limpieza verificada; luego postmortem y revisión de los runbooks con un compañero cuando esté disponible.

No rebajar el precheck ni retirar observabilidad para ejecutar en este equipo. Si no puede asegurarse reversión/identidad o el watchdog falla, no iniciar. Un cierre de terminal o un apagado del host no garantizan que una regla quede reparada: conservar journal y seguir la recuperación documentada. Este PR debe permanecer como implementación pendiente de validación integral, sin cerrar #16/#17 por los checks sin clúster.
