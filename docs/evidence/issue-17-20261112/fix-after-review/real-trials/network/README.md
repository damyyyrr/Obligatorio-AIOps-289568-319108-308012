# Ensayo network — PASS

NetworkPolicy bloquea conexiones nuevas del cliente a Pharmacy; se observa por separado la ruta Gateway, que puede conservar conexiones previas.

## Ejecución

- Commit: `1280e451d3e5b4dfee042022836f8ac5a54a8387`; árbol limpio al iniciar: `true`.
- Laboratorio local de un nodo `pharmago-issue17-validation`, con Calico. Operación automatizada asistida por Codex.
- Credenciales suministradas por entorno; no se incluyen valores en el comando ni en los artefactos.

```powershell
python "Implementacion K8S/Codigo/chaos-engineering/chaos.py" network --context pharmago-issue17-validation --operator "Codex-assisted lab validation" --duration 60 --megabytes 32 --execute
```

El campo operatorDeclared del reporte conserva el texto exacto usado por el helper local. Baseline: pods Ready, datos de demostración, targets y cinco alertas sanas/inactivas antes de inyectar.

## Observaciones

- Duración solicitada: 60 s; intervalo medido entre solicitud de inyección y confirmación de reversión: 77.444 s. Incluye latencia de comprobaciones/RPC, no es un instante físico exacto.
- pharmago-api-gateway/api/drug: códigos observados {'200': 4}.
- pharmago-api-gateway/api/roles: códigos observados {'200': 4}.
- pharmago-pharmacy-service/api/drug: códigos observados {'0': 4}.
- Estados de alerta observados: inactive. No se forzaron umbrales para provocar Firing.
- Resultado: PASS con limpieza verificada, 120 s estables, alertas finales sanas/inactivas y PV/PVC/configuración conservados.

## Tiempos y proceso

| Evento | UTC |
|---|---|
| Solicitud de inyección | 2026-11-12T22:15:33.192199+00:00 |
| Reversión confirmada | 2026-11-12T22:16:50.636687+00:00 |
| Inicio observado de ventana estable (`tRestore`) | 2026-11-12T22:16:52.926665+00:00 |
| Fin de verificación (`tVerified`) | 2026-11-12T22:18:58.043845+00:00 |
| Reconocimiento humano (`tAck`) | null / no registrado |

La resolución de las muestras y la cadencia de consultas limitan los tiempos observables. No se inventan detección humana, TTA, comunicaciones ni promedios. El comienzo de la ventana estable no equivale a reparación causal. La validación humana de roles, comunicaciones y aplicación de runbooks de #16 permanece pendiente.

[Vista resumida del reporte](report.json) · [JSON original íntegro comprimido](report.json.gz) · [Journal original](journal.json) · [Limpieza independiente](../../cleanup-verification.json).
