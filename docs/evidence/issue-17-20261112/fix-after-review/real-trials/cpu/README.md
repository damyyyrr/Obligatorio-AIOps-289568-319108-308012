# Ensayo cpu — PASS

Dos bucles acotados elevan CPU del pod elegido; al retirarlos se normaliza y se completa la ventana estable.

## Ejecución

- Commit: `a807b0498d5fcd06eee81e0eb2cf5794873028e1`; árbol limpio al iniciar: `true`.
- Laboratorio local de un nodo `pharmago-issue17-validation`, con Calico. Operación automatizada asistida por Codex.
- Credenciales suministradas por entorno; no se incluyen valores en el comando ni en los artefactos.

```powershell
python "Implementacion K8S/Codigo/chaos-engineering/chaos.py" cpu --context pharmago-issue17-validation --operator "Codex-assisted lab validation" --duration 130 --megabytes 32 --execute
```

El campo operatorDeclared del reporte conserva el texto exacto usado por el helper local. Baseline: pods Ready, datos de demostración, targets y cinco alertas sanas/inactivas antes de inyectar.

## Observaciones

- Duración solicitada: 130 s; intervalo medido entre solicitud de inyección y confirmación de reversión: 132.212 s. Incluye latencia de comprobaciones/RPC, no es un instante físico exacto.
- Métrica cpu: baseline máximo 0.0019567361394905343; máximo durante inyección 0.5001935899941372 cores.
- pharmago-api-gateway/api/drug: códigos observados {'200': 17}.
- pharmago-api-gateway/api/roles: códigos observados {'200': 17}.
- Estados de alerta observados: firing, inactive, pending. No se forzaron umbrales para provocar Firing.
- Resultado: PASS con limpieza verificada, 120 s estables, alertas finales sanas/inactivas y PV/PVC/configuración conservados.

## Tiempos y proceso

| Evento | UTC |
|---|---|
| Solicitud de inyección | 2026-11-12T21:51:45.342010+00:00 |
| Reversión confirmada | 2026-11-12T21:53:57.553627+00:00 |
| Inicio observado de ventana estable (`tRestore`) | 2026-11-12T21:54:00.262903+00:00 |
| Fin de verificación (`tVerified`) | 2026-11-12T21:56:07.040654+00:00 |
| Reconocimiento humano (`tAck`) | null / no registrado |

La resolución de las muestras y la cadencia de consultas limitan los tiempos observables. No se inventan detección humana, TTA, comunicaciones ni promedios. El comienzo de la ventana estable no equivale a reparación causal. La validación humana de roles, comunicaciones y aplicación de runbooks de #16 permanece pendiente.

[Vista resumida del reporte](report.json) · [JSON original íntegro comprimido](report.json.gz) · [Journal original](journal.json) · [Limpieza independiente](../../cleanup-verification.json).
