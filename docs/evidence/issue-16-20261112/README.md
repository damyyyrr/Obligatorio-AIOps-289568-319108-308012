# OPS-01: preparación del proceso de incidentes

Revisión documental del **12/11/2026**, rama `feature/issue-16-incidentes-runbooks`, desde `9164d8d5ee2395d86bcf9997f471da390c57e637` de `obligatorio`. Relacionada con #16; su validación integral se completa con #17. No se inyectaron fallas ni se iniciaron/detuvieron servicios para este cambio. No se enviaron comunicaciones a terceros.

## Entregables y trazabilidad

| Tarea de #16 | Resultado preparado | Validación |
|---|---|---|
| Roles, severidades, canal y escalamiento/aborto | [Plan de incidentes](../../baseline-incidents.md) para Kubernetes y Compose | Contraste con topología, guías de operación y condiciones de riesgo; nombres/canal se completan por corrida |
| Seis runbooks | [RB-01 a RB-06](../../runbooks/incidentes.md) | Requests, CPU, RAM, disco, red y desconexión interna; cada uno incluye señal, diagnóstico, contención, restauración, validación, aborto y evidencia |
| Eventos y tiempos del curso | TTD/TTA/TTRestore desde t_start; ack_delay separado; desconocidos explícitos | Lectura de Clase 1, pp. 33–35 y 42–45; reconstrucción histórica reproducible sin inventar tiempos |
| Bitácora y comunicaciones | [Ficha y mensajes](../../templates/incidente.md), [postmortem](../../templates/postmortem.md) | Checklist y borradores para envío manual; no se atribuye reconocimiento humano a un script |
| Revisión previa y mejora posterior | [Análisis retrospectivo](retrospectiva.md), más contrato de validación con #17 | Revisión previa realizada; ejecución de los seis casos y revisión por compañero aún pendientes |

También se consultó Clase 5, ciclo Prepare/Detect/Respond/Recover/Learn, roles y postmortem. Los materiales del curso permanecen fuera del repositorio; las decisiones operativas nuevas (cadencias de comunicación y ventana estable de 120 s) se identifican como políticas del equipo, no como resultados medidos ni obligaciones textuales del docente.

## Reconstrucción de observaciones reales

Fuente inalterada: [proof.json de #7](../issue-7-20261110/proof.json), tres ensayos del 10/11/2026 y su [informe](../issue-7-20261110/README.md). [reconstruct.py](reconstruct.py) produce [reconstruction.json](reconstruction.json) sin dependencias externas ni llamadas a Docker, kubectl o red.

Se toma `faultUtc` como referencia de inyección, **sin afirmar que sea el inicio medido del impacto al usuario**. La primera respuesta de negocio inválida completada es una señal capturada por el generador, no una alerta Firing ni reconocimiento humano. Los intervalos son segundos desde la inyección:

| Servicio | Primera respuesta inválida | Primer NotReady observado | Primera respuesta válida posterior | Pod Ready nuevamente |
|---|---:|---:|---:|---:|
| Gateway | 2,210 | 7,732 | 42,832 | 40,567 |
| Users | 2,223 | 8,319 | 8,059 | 37,768 |
| Pharmacy | 2,219 | 6,666 | 2,944 | 34,939 |

La diferencia entre respuesta válida y pod recuperado es coherente con las réplicas restantes, pero los datos no identifican qué réplica atendió cada request. Los valores Ready calculados se contrastan con `readyAgainSeconds` original con tolerancia de 0,02 s (redondeo/muestreo). Se conservan seis decimales en JSON para reproducibilidad aritmética, no como afirmación de exactitud del detector. El hash es SHA-256 de JSON canónico, estable ante LF/CRLF, no hash de los bytes originales.

**No registrados:** inicio de impacto independiente de la inyección, reconocimiento humano, corrección causal, alertas y ventana estable de 120 s. Se mantienen `null` los tiempos/intervalos correspondientes; no se calculan TTA, TTRestore ni promedios. Ningún dato se presenta como una nueva ejecución de #17 ni como validación integral del proceso.

## Reproducción y comprobaciones

Desde la raíz, Python 3.10+:

```powershell
# Regenerar solo el análisis documental local:
python docs/evidence/issue-16-20261112/reconstruct.py
# Verificar sin escribir:
python docs/evidence/issue-16-20261112/reconstruct.py --check
git diff --check
```

Comprobaciones realizadas en este incremento:

- El análisis se regeneró y `--check` coincidió en los tres casos; los datos de #7 quedaron sin cambios.
- Las rutas Markdown locales de los documentos cambiados existen y los bloques PowerShell pasan el parser, sin ejecutar sus comandos de operación.
- Los cinco UID/umbrales/tiempos de alerta se contrastaron con el ConfigMap versionado; servicios, réplicas, endpoints y capacidades con manifests y guías.
- Revisión de diff y contenido nuevo para excluir credenciales y afirmaciones de ensayos no ejecutados.
- `git diff --check` aprobado. No se recompiló la aplicación ni se ejecutó una suite de backend: el cambio es documentación y análisis de evidencia existente.

## Validación que debe registrar #17

Por cada RB-01 a RB-06: ficha con contexto/objetivo, roles reales y canal, baseline, presupuesto, mecanismo revisado e inversa; timestamps observables con fuente; acciones y comunicaciones efectivamente realizadas; resultados funcionales completos, alertas y estabilidad; limpieza y comparación de datos/recursos; postmortem y actualización del runbook. Mantener desconocidos cuando falten datos, con su motivo.

La revisión por otro integrante debe registrar quién leyó el procedimiento, qué pudo ejecutar y las correcciones necesarias. Si se trabaja en solitario, explicitarlo; este cambio no finge esa revisión. No esperar cierre de #16 para preparar #17: los documentos habilitan sus ensayos y el cierre integral se evalúa al aplicar el proceso. **Estado R06: preparación terminada; validación integral pendiente.**
