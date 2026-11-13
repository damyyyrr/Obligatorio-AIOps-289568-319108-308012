# Ensayo Almacenamiento — ejecución del operador

13/11/2026. Run ID `61159cbb42bc4491bcc92a93b9299b56`. **PASS / limpieza verified**. Archivo temporal propio de 32 MiB durante 60 s, fuera de los PVC de datos; retirada automática.

## Ejecución y alcance

Joaquin Decia ejecutó el helper local `probar.ps1 -Escenario storage -Operador $yo`, después de revisar el plan con `-SoloPlan`. El helper invocó el controlador versionado, cargó credenciales solo en memoria y conservó el reporte. Comando equivalente, con variables y credenciales preparadas según la [guía principal](../../README.md#reproducir):

```powershell
python "$chaos/chaos.py" storage --context $ctx --operator "Joaquin Decia" --duration 60 --megabytes 32 --execute
```

Controlador en commit `90ae6745066a107d2bc8dc014ef2b5dda1064008`, árbol limpio al iniciar. Laboratorio Minikube local de un nodo con Calico; no demuestra nodos físicos distintos. Codex guió los pasos y recopiló los archivos; el controlador automatizó la inyección, las sondas y la reversión.

## Resultado observado

Filesystem máximo muestreado durante la inyección: 32.11 MiB. La captura muestra ocupación temporal cercana a 32 MiB y retirada. El journal terminado y la comparación de PV/PVC sustentan limpieza y conservación de recursos.

Ventana de verificación estable registrada: **121.094 s**, desde `tRestore` hasta `tVerified`; muestreo finito, no garantía continua fuera de esa ventana. PV, PVC y deployments coinciden antes/después. Las cinco reglas terminaron con salud `ok` y estado `inactive`. No se modificaron umbrales para esta prueba.

| Evento del controlador | UTC |
|---|---|
| startedUtc | `2026-11-13T17:33:09.218645+00:00` |
| injectionRequestedUtc | `2026-11-13T17:33:14.046412+00:00` |
| faultRestoredUtc | `2026-11-13T17:34:15.769242+00:00` |
| tRestore | `2026-11-13T17:34:18.168651+00:00` |
| tVerified | `2026-11-13T17:36:19.263003+00:00` |
| finishedUtc | `2026-11-13T17:36:22.334872+00:00` |

`tAck` del reporte permanece `null`. Las [notas del operador](../../bitacora.md) tienen su propia hora; no se reemplazan por el inicio del script ni se calculan TTA o promedios sin observaciones suficientes.

[Resumen y métricas](resumen.json) · [Reporte original completo comprimido](report.json.gz) · [Journal original](journal.json) · [Conectividad manual](../../conectividad.jsonl).

## Capturas proporcionadas por el operador

![storage-antes-pod-5zzkh-20261113-173207](../../capturas/storage-antes-pod-5zzkh-20261113-173207.png)

![storage-durante-20261113-173433](../../capturas/storage-durante-20261113-173433.png)

![storage-subida-y-bajada-20261113-173752](../../capturas/storage-subida-y-bajada-20261113-173752.png)

![storage-resultado-20261113-173752](../../capturas/storage-resultado-20261113-173752.png)

![storage-despues-pods-http-20261113-173854](../../capturas/storage-despues-pods-http-20261113-173854.png)
