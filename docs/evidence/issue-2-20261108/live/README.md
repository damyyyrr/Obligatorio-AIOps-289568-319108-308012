# Validación real de la issue #2 — PASS local

Fecha: 08/11/2026 (Uruguay). Rama: `feature/issue-2-k8s-reproducible`, basada en `486bdce`, con cambios locales sin commit. La validación corresponde a esos archivos locales; no se modificaron las issues remotas.

## Resultado

| Etapa | Pods preparados | Frontend HTTP | Login por gateway | Medicamentos | Datos y PV/PVC |
|---|---:|---:|---:|---:|---|
| Instalación inicial | 12/12 | 200 | 200 y token presente | 4 | Referencia inicial |
| Segundo apply, mismo tag | 12/12 | 200 | 200 y token presente | 4 | Conservados |
| Parada y nuevo apply | 12/12 | 200 | 200 y token presente | 4 | Conservados |

Las tres consultas SQL produjeron el mismo SHA-256 y los ocho UIDs de cuatro PVs y cuatro PVCs permanecieron iguales. El seed se ejecutó solo una vez, después de la instalación inicial. Se creó un marcador de prueba en `PharmaDb.dbo.Issue2Validation` y se comprobó su conservación sin recrearlo. La consulta comparó medicamentos (Id, Code, Stock, Price, Deleted), cantidad de usuarios y marcador. Los registros sanitizados están en `first-sql.txt`, `second-sql.txt` y `after-stop-sql.txt`; no incluyen contraseñas ni tokens.

`summary.json` contiene los tres resultados, UIDs, digest SQL, pods, imágenes observadas, readiness y reinicios. `build.json` registra las cuatro imágenes construidas, sus IDs Docker y los digests de configuración comprobados en containerd. Los archivos `*-metadata.json` identifican cada operación y su versión. Las 17 pruebas de regresión también pasaron; ver `../checks.json`.

## Entorno y reproducción

Minikube 1.39.0; driver Docker; Kubernetes 1.34.1; containerd 2.3.4; nodo propio `pharmago-issue2`, 6144 MiB, cuatro CPUs y etiqueta `node-type=all`. Docker engine Linux 29.0.1 sobre Docker Desktop 4.52.0. Esta es una sola máquina física.

Se ejecutaron los subcomandos `build`, `apply`, `apply`, `stop`, `apply` de `k8s/manage.py`, con contexto explícito y el mismo tag de aplicación durante los tres despliegues. Se esperó la eliminación del pod SQL tras la parada antes de reaplicar. El procedimiento para repetir estas operaciones está en `Implementacion K8S/Codigo/k8s/README-k8s.md`.

Se usó `Backend/seed-data.sql` para el clúster aislado. Las comprobaciones HTTP usaron port-forward temporal a UI y gateway. SQL se consultó dentro de su pod con sqlcmd, tomando la contraseña del entorno del contenedor; no se guardaron credenciales. Elasticsearch 8.11.0 se precargó desde la imagen Docker local mediante `docker image save` y `ctr -n k8s.io images import` para ahorrar una descarga; el resto de imágenes operativas se descargó normalmente.

Se observaron avisos transitorios de readiness durante el arranque en frío. Los tres snapshots finales registran todos los contenedores preparados. No se presenta esta prueba como una medición de continuidad de servicio.

## Problema detectado y corregido

La primera construcción real cargó Users correctamente, pero la comparación de imágenes falló: Docker reportó un descriptor OCI y CRI un digest de configuración distinto. `manage.py` ahora obtiene el digest de configuración de una exportación Docker en streaming, sin escribir otro archivo de imagen en el host. La nueva prueba de regresión reproduce esa diferencia. `image-verification.json` documenta la comprobación real inicial de la corrección; la construcción final verificó las cuatro imágenes.

`initial-attempt.json` conserva el intento previo incompleto, que quedó detenido por falta de disco. Su bloqueo se resolvió con la limpieza posterior descrita abajo; no representa el resultado final.

## Limpieza autorizada y estado final

Con autorización del usuario se eliminaron primero 14 imágenes/tags antiguos de prueba de PharmaGo sin referencias desde contenedores. Después se borraron nueve volúmenes huérfanos de las pruebas antiguas `aiops-obligatorio*` y la caché de compilación antigua. Se conservaron los 26 contenedores del inventario, el volumen `pharmago-issue2` y todos los volúmenes de los demás proyectos; ver `cleanup.json`. La reconstrucción posterior genera una nueva caché útil para continuar este proyecto.

El espacio libre de C: pasó de unos 1,5 GB al inicio de esa limpieza a unos 17 GB tras ella; una observación posterior mostró unos 58 GB libres. `cleanup.json` registra las mediciones y la disponibilidad posterior a la validación. No se atribuye toda variación del espacio del host exclusivamente a una operación concreta.

La compactación del VHDX mediante la API de Windows no llegó a ejecutarse: OpenVirtualDisk devolvió acceso denegado (5), sin cambiar el archivo. Su longitud aparente se mantuvo cercana a 63,6 GiB. Se recuperó capacidad sin hacer factory reset ni borrar ese disco completo.

Docker necesitó renovar sus directorios de sockets temporales para arrancar; las copias `.issue2-backup*` se conservaron fuera del repositorio. Tras limpiar capas se reinició Docker. Para evitar una recarga de imagen base que quedaba esperando, se creó el alias local `pharmago-kicbase:issue2` de la misma imagen base y se arrancó el perfil con `--base-image=pharmago-kicbase:issue2`. Ese alias debe conservarse para reutilizar el perfil actual.

Después de registrar el resultado se detuvo el perfil para liberar memoria, conservando sus datos. Para retomarlo en este equipo: `minikube start -p pharmago-issue2 --base-image=pharmago-kicbase:issue2`.

## Alcance

Este PASS cubre instalación local funcional, repetición sin pérdida de datos y parada/arranque de la issue #2. La aceptación se basa en HTTP y SQL reales; no se automatizó interacción Angular en navegador ni BDD (issue #15). No demuestra separación física, autorrecuperación ante excepciones, disponibilidad durante rollout, trazas/alertas completas, caos, ML o restauración de backups. Los estados globales R01–R08 permanecen abiertos.
