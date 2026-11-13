# Ensayo Solicitudes — ejecución del operador

13/11/2026. Run ID `6a3b5bc65d4043c689ba37646f811628`. **PASS / limpieza verified**. 240 solicitudes en 60 s, máximo 4 req/s y concurrencia 4; cuota conservada.

## Ejecución y alcance

Joaquin Decia ejecutó el helper local `probar.ps1 -Escenario requests -Operador $yo`, después de revisar el plan con `-SoloPlan`. El helper invocó el controlador versionado, cargó credenciales solo en memoria y conservó el reporte. Comando equivalente, con variables y credenciales preparadas según la [guía principal](../../README.md#reproducir):

```powershell
python "$chaos/chaos.py" requests --context $ctx --operator "Joaquin Decia" --duration 60 --megabytes 32 --execute
```

Controlador en commit `90ae6745066a107d2bc8dc014ef2b5dda1064008`, árbol limpio al iniciar. Laboratorio Minikube local de un nodo con Calico; no demuestra nodos físicos distintos. Codex guió los pasos y recopiló los archivos; el controlador automatizó la inyección, las sondas y la reversión.

## Resultado observado

El generador registró 100 respuestas HTTP 200 y 140 HTTP 429, 240 en total. Las capturas muestran aumento de tráfico, rechazos 429 y regreso a cero, sin 5xx en el panel. La latencia mostrada en la captura es media, no p95. Las sondas funcionales legítimas se conservan separadas de la carga.

Ventana de verificación estable registrada: **127.084 s**, desde `tRestore` hasta `tVerified`; muestreo finito, no garantía continua fuera de esa ventana. PV, PVC y deployments coinciden antes/después. Las cinco reglas terminaron con salud `ok` y estado `inactive`. No se modificaron umbrales para esta prueba.

| Evento del controlador | UTC |
|---|---|
| startedUtc | `2026-11-13T16:18:01.594997+00:00` |
| injectionRequestedUtc | `2026-11-13T16:18:06.055014+00:00` |
| faultRestoredUtc | `2026-11-13T16:19:13.469760+00:00` |
| tRestore | `2026-11-13T16:19:15.730471+00:00` |
| tVerified | `2026-11-13T16:21:22.814228+00:00` |
| finishedUtc | `2026-11-13T16:21:27.251052+00:00` |

`tAck` del reporte permanece `null`. Las [notas del operador](../../bitacora.md) tienen su propia hora; no se reemplazan por el inicio del script ni se calculan TTA o promedios sin observaciones suficientes.

[Resumen y métricas](resumen.json) · [Reporte original completo comprimido](report.json.gz) · [Journal original](journal.json) · [Conectividad manual](../../conectividad.jsonl).

## Capturas proporcionadas por el operador

![requests-antes-20261113-161604](../../capturas/requests-antes-20261113-161604.png)

![requests-durante-20261113-162004](../../capturas/requests-durante-20261113-162004.png)

![requests-overview-recuperacion-20261113-162211](../../capturas/requests-overview-recuperacion-20261113-162211.png)

![requests-resultado-20261113-162308](../../capturas/requests-resultado-20261113-162308.png)

![requests-despues-pods-http-20261113-162508](../../capturas/requests-despues-pods-http-20261113-162508.png)
