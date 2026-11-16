# Evidencias de implementación y pruebas

Este índice permite localizar los resultados que respaldan la [matriz de requisitos](../aiops-requirements-matrix.md). Las carpetas con números de issues identifican el incremento que produjo cada prueba; se conservan aunque la issue esté cerrada. Cada evidencia mantiene su entorno, versión y resultado, incluidos intentos bloqueados o fallidos.

## Evidencias por requisito

| Requisito | Evidencia principal | Alcance |
|---|---|---|
| R01 — Plataforma | [Tres PCs: topología, nodos, pods y diagrama](chaos-3pc-20261116/README.md) | k3s/WSL2/Tailscale; Gateway, Users y Pharmacy en PCs distintas |
| R01 — Instalación y datos | [Instalación/reaplicación](issue-2-20261108/live/README.md), [colocación](issue-3-20261109/README.md), [restauración SQL](issue-4-20261109/README.md), [migraciones](issue-5-20261109/README.md) | Ensayos locales Minikube |
| R02 — Recuperación y protección | [SIGSTOP en tres PCs](chaos-3pc-20261116/README.md#recuperación-de-procesos-sigstop-en-3-pcs), [probes locales](issue-7-20261110/README.md), [rate limiting](issue-9-20261111/README.md), [timeouts](issue-10-20261111/README.md) | Recuperación muestreada; interrupciones y 429 registrados |
| R03 — Rollout/rollback | [226/226 solicitudes válidas](issue-8-20261111/README.md) | Recambio local de tres servicios, con SQL, frontend y observabilidad estables |
| R04 — Observabilidad | [Métricas](issue-6-20261110/README.md), [trazas](issue-11-20261112/README.md), [logs](issue-12-20261112/README.md), [cinco alertas](issue-13-20261112/README.md) | Validación detallada local; no equivale a HA del stack |
| R05 — Anomalías | [Isolation Forest y One-Class SVM](issue-14-20261112/README.md) | Dataset docente, resultados descriptivos sobre entrenamiento |
| R06 — Incidentes | [Paquete del operador](issue-16-20261113/README.md) y [antecedente reconstruido](issue-16-20261112/README.md) | Aplicación guiada local; sin medición de reconocimiento humano |
| R07 — Caos | [Seis categorías en tres PCs](chaos-3pc-20261116/README.md), [RAM de 128 MiB](chaos-3pc-20261116/README.md#ensayo-adicional-de-memoria-con-128-mib), [I/O sostenida local](storage-io-20261114/README.md), [ensayos técnicos anteriores](issue-17-20261112/fix-after-review/README.md) | Efecto, restauración y limpieza; no se infiere saturación general u OOM |
| BDD | [Cuatro escenarios reales en navegador](issue-15-20261112/live-after-fix/README.md) | Baseline Compose, Electron headless |
| Suite .NET | [319/319 pruebas](test-isolation-20261114/README.md) | Corrección del aislamiento de una prueba |
| Baseline | [Compose, arranque y persistencia](../BASELINE_RESULT.md) | Pruebas locales iniciales |

La defensa se prepara con estas evidencias; no se registra como realizada por tener los ensayos técnicos aprobados.

## Cómo leer los archivos

- `README.md`, fichas y bitácoras explican procedimiento, resultado y límites.
- `summary.json`, `proof.json` y resúmenes específicos permiten consultar medidas y estados.
- Reportes, journals y capturas respaldan esas conclusiones. Los archivos `.gz` se pueden abrir con Python `gzip` sin iniciar el laboratorio.
- En los ensayos de #17, `report.json` es una vista compacta y `report.json.gz` conserva el original completo; `artifactView` documenta omisiones y hash. No son copias intercambiables.
- Hay archivos idénticos compartidos por evidencias de trazas/logs/alertas y alias de intentos fallidos. Se conservan porque sus paquetes o manifiestos los referencian y su ahorro sería pequeño frente a la pérdida de trazabilidad.

Las fechas de carpetas, timestamps, commits y hashes identifican el origen. Una prueba anterior no se convierte en una ejecución sobre el último código por integrarla en la rama final. Para repetir un ensayo se usan las guías actuales; los comandos históricos se leen en su contexto.
