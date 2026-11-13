# Ensayo disconnect — PASS

Un selector imposible retira endpoints del Service Pharmacy e impide conexiones nuevas; se observa por separado la ruta Gateway existente y se restaura el selector original.

## Ejecución

- Commit: `b808ed45bbe406a9257e2f28e57c10dd2fc54a04`; árbol limpio al iniciar: `true`.
- Laboratorio local de un nodo `pharmago-issue17-validation`, con Calico. Operación automatizada asistida por Codex.
- Credenciales suministradas por entorno; no se incluyen valores en el comando ni en los artefactos.

```powershell
python "Implementacion K8S/Codigo/chaos-engineering/chaos.py" disconnect --context pharmago-issue17-validation --operator "Codex-assisted lab validation" --duration 60 --megabytes 32 --execute
```

El campo operatorDeclared del reporte conserva el texto exacto usado por el helper local. Baseline: pods Ready, datos de demostración, targets y cinco alertas sanas/inactivas antes de inyectar.

## Observaciones

- Duración solicitada: 60 s; intervalo medido entre solicitud de inyección y confirmación de reversión: 66.312 s. Incluye latencia de comprobaciones/RPC, no es un instante físico exacto.
- pharmago-api-gateway/api/drug: códigos observados {'200': 9}.
- pharmago-api-gateway/api/roles: códigos observados {'200': 9}.
- pharmago-pharmacy-service/api/drug: códigos observados {'0': 9}.
- Estados de alerta observados: inactive. No se forzaron umbrales para provocar Firing.
- Resultado: PASS con limpieza verificada, 120 s estables, alertas finales sanas/inactivas y PV/PVC/configuración conservados.

## Tiempos y proceso

| Evento | UTC |
|---|---|
| Solicitud de inyección | 2026-11-12T22:22:56.250736+00:00 |
| Reversión confirmada | 2026-11-12T22:24:02.563062+00:00 |
| Inicio observado de ventana estable (`tRestore`) | 2026-11-12T22:24:05.004781+00:00 |
| Fin de verificación (`tVerified`) | 2026-11-12T22:26:10.111242+00:00 |
| Reconocimiento humano (`tAck`) | null / no registrado |

La resolución de las muestras y la cadencia de consultas limitan los tiempos observables. No se inventan detección humana, TTA, comunicaciones ni promedios. El comienzo de la ventana estable no equivale a reparación causal. La validación humana de roles, comunicaciones y aplicación de runbooks de #16 permanece pendiente.

[Vista resumida del reporte](report.json) · [JSON original íntegro comprimido](report.json.gz) · [Journal original](journal.json) · [Limpieza independiente](../../cleanup-verification.json).
