# Ensayo storage — PASS

El agente escribe y sincroniza exactamente 32 MiB en /tmp efímero, fuera de PV/PVC, y retira solo sus archivos.

## Ejecución

- Commit: `0a47b7b674c8b49cac9ba84578d8b1a0511ccc6f`; árbol limpio al iniciar: `true`.
- Laboratorio local de un nodo `pharmago-issue17-validation`, con Calico. Operación automatizada asistida por Codex.
- Credenciales suministradas por entorno; no se incluyen valores en el comando ni en los artefactos.

```powershell
python "Implementacion K8S/Codigo/chaos-engineering/chaos.py" storage --context pharmago-issue17-validation --operator "Codex-assisted lab validation" --duration 60 --megabytes 32 --execute
```

El campo operatorDeclared del reporte conserva el texto exacto usado por el helper local. Baseline: pods Ready, datos de demostración, targets y cinco alertas sanas/inactivas antes de inyectar.

## Observaciones

- Duración solicitada: 60 s; intervalo medido entre solicitud de inyección y confirmación de reversión: 61.375 s. Incluye latencia de comprobaciones/RPC, no es un instante físico exacto.
- Bytes inyectados comprobados: 33554432.
- pharmago-api-gateway/api/drug: códigos observados {'200': 8}.
- pharmago-api-gateway/api/roles: códigos observados {'200': 8}.
- Estados de alerta observados: inactive. No se forzaron umbrales para provocar Firing.
- Resultado: PASS con limpieza verificada, 120 s estables, alertas finales sanas/inactivas y PV/PVC/configuración conservados.

## Tiempos y proceso

| Evento | UTC |
|---|---|
| Solicitud de inyección | 2026-11-12T22:06:04.755542+00:00 |
| Reversión confirmada | 2026-11-12T22:07:06.130848+00:00 |
| Inicio observado de ventana estable (`tRestore`) | 2026-11-12T22:07:08.508700+00:00 |
| Fin de verificación (`tVerified`) | 2026-11-12T22:09:13.947918+00:00 |
| Reconocimiento humano (`tAck`) | null / no registrado |

La resolución de las muestras y la cadencia de consultas limitan los tiempos observables. No se inventan detección humana, TTA, comunicaciones ni promedios. El comienzo de la ventana estable no equivale a reparación causal. La validación humana de roles, comunicaciones y aplicación de runbooks de #16 permanece pendiente.

[Vista resumida del reporte](report.json) · [JSON original íntegro comprimido](report.json.gz) · [Journal original](journal.json) · [Limpieza independiente](../../cleanup-verification.json).
