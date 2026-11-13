# Ensayo Red — ejecución del operador

13/11/2026. Run ID `04b212284ef74d4fa5e30dccd80e7c78`. **PASS / limpieza verified**. NetworkPolicy ingress durante 60 s, aplicada por Calico; conexiones nuevas directas a Pharmacy.

## Ejecución y alcance

Joaquin Decia ejecutó el helper local `probar.ps1 -Escenario network -Operador $yo`, después de revisar el plan con `-SoloPlan`. El helper invocó el controlador versionado, cargó credenciales solo en memoria y conservó el reporte. Comando equivalente, con variables y credenciales preparadas según la [guía principal](../../README.md#reproducir):

```powershell
python "$chaos/chaos.py" network --context $ctx --operator "Joaquin Decia" --duration 60 --megabytes 32 --execute
```

Controlador en commit `90ae6745066a107d2bc8dc014ef2b5dda1064008`, árbol limpio al iniciar. Laboratorio Minikube local de un nodo con Calico; no demuestra nodos físicos distintos. Codex guió los pasos y recopiló los archivos; el controlador automatizó la inyección, las sondas y la reversión.

## Resultado observado

La consulta manual con conexión nueva pasó de HTTP 200 a TimeoutError durante la política y volvió a HTTP 200. Roles por Gateway siguió en 200. Las conexiones ya abiertas del Gateway pueden sobrevivir; no se afirma una caída total de la aplicación.

Ventana de verificación estable registrada: **127.728 s**, desde `tRestore` hasta `tVerified`; muestreo finito, no garantía continua fuera de esa ventana. PV, PVC y deployments coinciden antes/después. Las cinco reglas terminaron con salud `ok` y estado `inactive`. No se modificaron umbrales para esta prueba.

| Evento del controlador | UTC |
|---|---|
| startedUtc | `2026-11-13T17:49:33.650297+00:00` |
| injectionRequestedUtc | `2026-11-13T17:49:38.650091+00:00` |
| faultRestoredUtc | `2026-11-13T17:50:57.580608+00:00` |
| tRestore | `2026-11-13T17:51:00.885975+00:00` |
| tVerified | `2026-11-13T17:53:08.614325+00:00` |
| finishedUtc | `2026-11-13T17:53:11.206342+00:00` |

`tAck` del reporte permanece `null`. Las [notas del operador](../../bitacora.md) tienen su propia hora; no se reemplazan por el inicio del script ni se calculan TTA o promedios sin observaciones suficientes.

[Resumen y métricas](resumen.json) · [Reporte original completo comprimido](report.json.gz) · [Journal original](journal.json) · [Conectividad manual](../../conectividad.jsonl).

## Capturas proporcionadas por el operador

![network-antes-20261113-174415](../../capturas/network-antes-20261113-174415.png)

![network-durante-20261113-175044](../../capturas/network-durante-20261113-175044.png)

![network-antes-durante-despues-20261113-175209](../../capturas/network-antes-durante-despues-20261113-175209.png)

![network-resultado-20261113-175421](../../capturas/network-resultado-20261113-175421.png)

![network-despues-pods-http-20261113-175509](../../capturas/network-despues-pods-http-20261113-175509.png)
