# Ficha y bitácora de incidente

Copiar a `.runtime/incidents/<id>/incidente.md`. Antes de versionar en `docs/evidence/`, sanitizar y completar o marcar desconocidos. `PENDIENTE` no es un resultado. Guías: [plan](../baseline-incidents.md) y [runbooks](../runbooks/incidentes.md).

## Identificación y preparación

- ID / tipo (real, ensayo, retrospectiva) / issue / runbook: PENDIENTE
- Hipótesis / commit-diff / imágenes-digests: PENDIENTE
- Contexto-namespace o proyecto Compose / perfil / nodos: PENDIENTE
- Servicio / pod-UID / contenedor-runtime / nodo / endpoint: PENDIENTE
- Coordinación / respuesta / observación-bitácora / enlace / suplencias: PENDIENTE
- Canal único / ubicación de bitácora / destinatarios: PENDIENTE
- Ventana autorizada / duración máxima / decisión y responsable de iniciar: PENDIENTE
- Baseline funcional y recursos / cuotas / réplicas-revisiones / UIDs PV-PVC: PENDIENTE
- Mecanismo / PID-job-regla-ruta propios / inversa exacta y limpieza: PENDIENTE
- Límites CPU-RAM-disco-carga / criterios de aborto: PENDIENTE
- Criterio funcional y ventana de estabilidad: PENDIENTE
- Precheck y acceso al terminal de recuperación: PENDIENTE

## Impacto y decisiones

- Severidad y fundamento / servicios-usuarios afectados / alcance no observado: PENDIENTE
- Síntomas y señal inicial (fuente, consulta, regla o trace ID): PENDIENTE
- Hechos / hipótesis sin probar: PENDIENTE
- Acción / responsable / reversión / riesgo aceptado: PENDIENTE
- Escalamiento-aborto / destinatario / motivo / próxima revisión: PENDIENTE

## Línea temporal UTC

Una fila por observación, acción o comunicación; timestamps reales ISO 8601 con zona. Guardar inicio y resultado de comandos, sin secretos. Si es retrospectiva, citar archivo y ruta JSON sin atribuir la acción a un operador actual.

| UTC | Actor o detector | Tipo | Hecho/acción/resultado | Evidencia |
|---|---|---|---|---|
| PENDIENTE | PENDIENTE | precheck/inject/detect/ack/mitigate/repair/restore/verify/alert/comunicación | PENDIENTE | PENDIENTE |

## Tiempos

| Evento o intervalo | UTC o segundos | Fuente / precisión / motivo si no registrado |
|---|---|---|
| t_inject y t_start (no asumir equivalencia) | PENDIENTE | PENDIENTE |
| t_detect / detector | PENDIENTE | PENDIENTE |
| t_ack / persona que reconoce | PENDIENTE | PENDIENTE |
| t_mitigate y t_repair (mitigación frente a causa corregida) | PENDIENTE | PENDIENTE |
| Primer HTTP válido / pod Ready | PENDIENTE | PENDIENTE |
| t_restore / t_verified / ventana estable | PENDIENTE | PENDIENTE |
| t_alert_firing / t_alert_ok | PENDIENTE | PENDIENTE |
| TTD = t_detect − t_start | PENDIENTE | PENDIENTE |
| TTA = t_ack − t_start (curso) | PENDIENTE | PENDIENTE |
| ack_delay = t_ack − t_detect (opcional; no es TTA) | PENDIENTE | PENDIENTE |
| TTRestore = t_restore − t_start | PENDIENTE | PENDIENTE |

Dato ausente = no registrado, no cero. Sin t_start no calcular intervalos desde el inicio. Identificar muestreo/diferencias de reloj. No promediar incidentes incomparables.

## Recuperación y cierre

- [ ] Estímulo retirado: PID/job/regla/archivo propio sin efecto.
- [ ] Catálogo, roles y login válidos por el camino del usuario; UI si corresponde.
- [ ] Conteo completo de intentos, errores, 429 y timeouts.
- [ ] Ventana estable verificada; réplicas, Ready y endpoints esperados.
- [ ] Recursos recuperados, sin presión ni nuevos reinicios; datos y PV/PVC conservados.
- [ ] Alertas OK con datos frescos; cualquier S3 pendiente identificado.
- [ ] Temporales limpiados y configuración comparada con inventario.
- [ ] Comunicación final o handoff, postmortem y acciones enlazados.
- Decisión (abierto/mitigado/restaurado en observación/cerrado), responsable y hora: PENDIENTE
- Evidencias / limitaciones / próxima acción y responsable: PENDIENTE

## Mensajes para envío manual

**Apertura:** `[UTC] [ID] [severidad] Impacto confirmado <hechos/alcance>. Coordina <persona>; responde <persona>. Acción inicial <acción>. Próxima actualización <UTC>.`

**Actualización:** `[UTC] [ID] Nuevos hechos <evidencia>. Mitigación <acción/resultado>. Hipótesis pendiente <detalle>. Impacto actual <hechos>. Próxima decisión/actualización <UTC>.`

**Aborto:** `[UTC] [ID] Se aborta por <condición>. Se detuvo <estímulo>. Reversión/datos <comprobado o desconocido>. Necesitamos <responsable/ayuda>. No se inicia otro ensayo.`

**Recuperación:** `[UTC] [ID] Restaurado desde <t_restore>, verificado hasta <t_verified> con <N/T/operaciones>. Limpieza <resultado>. Alertas <estado>. Pendientes/responsable <detalle>. Postmortem <ruta>.`

**Handoff:** `[UTC] [ID] Recibe <persona>. Estado y alcance <detalle>. Último cambio/reversión <detalle>. Evidencia <ruta>. Riesgo, siguiente acción y control <detalle/UTC>.`

Son plantillas sin envío automático. No rellenar horas/personas/resultados por suposición.
