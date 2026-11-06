# Baseline local de PharmaGo

Ejecutar desde esta carpeta en PowerShell con Docker Desktop en modo Linux. Este arranque usa `compose.baseline.yaml` y el proyecto aislado `pharmago-baseline`. Mantiene el Compose original del curso como referencia. No levanta Kubernetes ni ELK.

```powershell
.\scripts\start-baseline.ps1 -SeedDemoData
.\scripts\smoke-baseline.ps1
```

El primer comando genera contraseñas aleatorias en `.env`, ignorado por Git; no reemplaza un `.env` existente. Compila las cuatro imágenes de aplicación secuencialmente, espera a SQL, inicia Users para aplicar las migraciones existentes y agrega el resto. `-SeedDemoData` incorpora solo datos de laboratorio ausentes en la DB aislada; omitirlo si se desea conservar una DB sin demos. El smoke espera roles/medicamentos persistidos, por lo que una DB vacía no pasa la prueba funcional con datos.

Para comprobar además el login y guardar su log JSON correlacionado, usar un usuario de demostración del seed o un usuario válido de esta DB:

```powershell
$demoCredential = Get-Credential -UserName admin -Message 'Credencial de la DB local de demostración'
.\scripts\smoke-baseline.ps1 -DemoCredential $demoCredential
```

El seed docente describe sus credenciales de laboratorio en `Backend/seed-data.sql`. El smoke no guarda el token ni la contraseña. Los resultados sanitizados quedan en `../../docs/evidence/baseline-<fecha-hora>/` y un fallo devuelve error; no confundir archivos presentes con una prueba exitosa.

| Servicio | Dirección |
|---|---|
| Angular | http://127.0.0.1:4200 |
| API Gateway | http://127.0.0.1:5000 |
| Users | http://127.0.0.1:5001 |
| Pharmacy | http://127.0.0.1:5002 |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |
| SQL Express | 127.0.0.1,11433 |

Grafana usa el usuario `admin` y la contraseña `PHARMAGO_GRAFANA_PASSWORD` del `.env` local. Su datasource ya apunta a `http://prometheus:9090` dentro de Compose. Los puertos del baseline se publican solo en loopback. No imprimir ni adjuntar `.env` o la salida expandida de `docker compose config`; validar con `config --quiet`.

## Inspección y parada

```powershell
docker compose -p pharmago-baseline -f compose.baseline.yaml ps
docker compose -p pharmago-baseline -f compose.baseline.yaml logs --tail 100 pharmago-users-service
docker compose -p pharmago-baseline -f compose.baseline.yaml stats --no-stream
.\scripts\stop-baseline.ps1
# Volver a iniciar imágenes ya construidas y conservar DB:
.\scripts\start-baseline.ps1 -SkipBuild
```

La parada conserva contenedores y volúmenes. No usar `down -v`, cleanup del curso ni prune como procedimiento de arranque o reparación. Si hay puertos ocupados, diagnosticar quién los usa; no detener procesos ajenos. Si falta el motor Linux, iniciar Docker Desktop antes de reintentar.

## Alcance de la comprobación

Se verifican respuestas HTTP de Angular, datos SQL a través de los dos microservicios y gateway, correlación, Prometheus y Grafana. Con credencial se comprueba login y un evento JSON de negocio. La configuración JSON de .NET no convierte automáticamente escrituras directas por `Console.WriteLine`; el resto de logs se audita en el incremento de telemetría.

No se demuestra todavía interacción Angular en navegador, Kubernetes, separación física, trazas completas, cinco alertas, alta disponibilidad, caos ni modelos ML. Los límites de memoria suman 3,25 GiB más sobrecarga del motor. Obsérvese el consumo antes de añadir ELK o ejecutar compilaciones con los servicios activos.

Referencias: [orden de arranque de Compose](https://docs.docker.com/compose/how-tos/startup-order/), [formato JSON de logs .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/logging/console-log-formatter), [variables de SQL Server](https://learn.microsoft.com/en-us/sql/linux/configure/environment-variables?view=sql-server-ver15).
