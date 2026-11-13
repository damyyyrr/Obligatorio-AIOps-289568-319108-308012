# Ensayo Desconexión interna — ejecución del operador

13/11/2026. Run ID `213770c063314506a986c05861373319`. **PASS / limpieza verified**. Selector temporal del Service durante 60 s; selector original restaurado, pods y SQL conservados.

## Ejecución y alcance

Joaquin Decia ejecutó el helper local `probar.ps1 -Escenario disconnect -Operador $yo`, después de revisar el plan con `-SoloPlan`. El helper invocó el controlador versionado, cargó credenciales solo en memoria y conservó el reporte. Comando equivalente, con variables y credenciales preparadas según la [guía principal](../../README.md#reproducir):

```powershell
python "$chaos/chaos.py" disconnect --context $ctx --operator "Joaquin Decia" --duration 60 --megabytes 32 --execute
```

Controlador en commit `90ae6745066a107d2bc8dc014ef2b5dda1064008`, árbol limpio al iniciar. Laboratorio Minikube local de un nodo con Calico; no demuestra nodos físicos distintos. Codex guió los pasos y recopiló los archivos; el controlador automatizó la inyección, las sondas y la reversión.

## Resultado observado

La consulta manual con conexión nueva pasó de HTTP 200 a ConnectionRefusedError con el selector temporal y volvió a HTTP 200. Roles por Gateway siguió en 200. Una consulta adicional posterior a la reversión fue etiquetada por error como durante; se conserva sin editar y se usa la consulta corregida despues para la recuperación.

Ventana de verificación estable registrada: **122.434 s**, desde `tRestore` hasta `tVerified`; muestreo finito, no garantía continua fuera de esa ventana. PV, PVC y deployments coinciden antes/después. Las cinco reglas terminaron con salud `ok` y estado `inactive`. No se modificaron umbrales para esta prueba.

| Evento del controlador | UTC |
|---|---|
| startedUtc | `2026-11-13T18:11:35.660423+00:00` |
| injectionRequestedUtc | `2026-11-13T18:11:40.517043+00:00` |
| faultRestoredUtc | `2026-11-13T18:12:42.301865+00:00` |
| tRestore | `2026-11-13T18:12:45.024118+00:00` |
| tVerified | `2026-11-13T18:14:47.458326+00:00` |
| finishedUtc | `2026-11-13T18:14:48.573215+00:00` |

`tAck` del reporte permanece `null`. Las [notas del operador](../../bitacora.md) tienen su propia hora; no se reemplazan por el inicio del script ni se calculan TTA o promedios sin observaciones suficientes.

[Resumen y métricas](resumen.json) · [Reporte original completo comprimido](report.json.gz) · [Journal original](journal.json) · [Conectividad manual](../../conectividad.jsonl).

## Capturas proporcionadas por el operador

![disconnect-antes-20261113-181109](../../capturas/disconnect-antes-20261113-181109.png)

![disconnect-durante-20261113-181246](../../capturas/disconnect-durante-20261113-181246.png)

![disconnect-antes-durante-despues-20261113-181417](../../capturas/disconnect-antes-durante-despues-20261113-181417.png)

![disconnect-resultado-20261113-181637](../../capturas/disconnect-resultado-20261113-181637.png)

![disconnect-despues-pods-http-20261113-181854](../../capturas/disconnect-despues-pods-http-20261113-181854.png)
