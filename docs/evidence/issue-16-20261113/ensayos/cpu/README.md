# Ensayo CPU — ejecución del operador

13/11/2026. Run ID `cda2bb158a3c4a038860ea19039589a8`. **PASS / limpieza verified**. Dos procesos de carga CPU, duración solicitada 130 s; retirada automática de procesos.

## Ejecución y alcance

Joaquin Decia ejecutó el helper local `probar.ps1 -Escenario cpu -Operador $yo`, después de revisar el plan con `-SoloPlan`. El helper invocó el controlador versionado, cargó credenciales solo en memoria y conservó el reporte. Comando equivalente, con variables y credenciales preparadas según la [guía principal](../../README.md#reproducir):

```powershell
python "$chaos/chaos.py" cpu --context $ctx --operator "Joaquin Decia" --duration 130 --megabytes 32 --execute
```

Controlador en commit `90ae6745066a107d2bc8dc014ef2b5dda1064008`, árbol limpio al iniciar. Laboratorio Minikube local de un nodo con Calico; no demuestra nodos físicos distintos. Codex guió los pasos y recopiló los archivos; el controlador automatizó la inyección, las sondas y la reversión.

## Resultado observado

CPU máxima muestreada del pod: 0.500596 cores durante la inyección. Las observaciones de reglas incluyen Pending y Firing, con las cinco reglas sanas/inactivas al final. La captura muestra subida y bajada. El reconocimiento explícito de la bitácora es posterior al fin técnico; no se presenta como reconocimiento durante la falla.

Ventana de verificación estable registrada: **127.804 s**, desde `tRestore` hasta `tVerified`; muestreo finito, no garantía continua fuera de esa ventana. PV, PVC y deployments coinciden antes/después. Las cinco reglas terminaron con salud `ok` y estado `inactive`. No se modificaron umbrales para esta prueba.

| Evento del controlador | UTC |
|---|---|
| startedUtc | `2026-11-13T15:04:17.273064+00:00` |
| injectionRequestedUtc | `2026-11-13T15:04:23.179537+00:00` |
| faultRestoredUtc | `2026-11-13T15:06:37.147898+00:00` |
| tRestore | `2026-11-13T15:06:39.651500+00:00` |
| tVerified | `2026-11-13T15:08:47.455518+00:00` |
| finishedUtc | `2026-11-13T15:08:49.745391+00:00` |

`tAck` del reporte permanece `null`. Las [notas del operador](../../bitacora.md) tienen su propia hora; no se reemplazan por el inicio del script ni se calculan TTA o promedios sin observaciones suficientes.

[Resumen y métricas](resumen.json) · [Reporte original completo comprimido](report.json.gz) · [Journal original](journal.json) · [Conectividad manual](../../conectividad.jsonl).

## Capturas proporcionadas por el operador

![antes-cpu-20261113](../../capturas/antes-cpu-20261113.png)

![durante-cpu-20261113-150735](../../capturas/durante-cpu-20261113-150735.png)

![cpu-subida-y-bajada-20261113-150915](../../capturas/cpu-subida-y-bajada-20261113-150915.png)

![despues-alertas-20261113-151058](../../capturas/despues-alertas-20261113-151058.png)

![despues-pods-http-20261113-151257](../../capturas/despues-pods-http-20261113-151257.png)
