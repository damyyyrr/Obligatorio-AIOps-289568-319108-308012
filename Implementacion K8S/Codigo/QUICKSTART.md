# Inicio rápido de PharmaGo

## Elegir el entorno

- [Baseline Compose local](BASELINE.md): aplicación, SQL, Collector, Prometheus y Grafana, con scripts PowerShell y credenciales locales. No incluye el pipeline central de logs ni Kubernetes.
- [Despliegue Kubernetes](k8s/README-k8s.md): perfil/contexto explícitos, imágenes verificadas, Secrets externos, almacenamiento y observabilidad. [Resumen Kubernetes](tutoriales/quickstart.md).

El `docker-compose.yml` heredado y sus puertos/configuración no equivalen al baseline aislado. Para reproducir la validación Compose del equipo, usar `compose.baseline.yaml` mediante los scripts siguientes.

## Baseline local

Con Docker Desktop Linux disponible y capacidad suficiente, desde `Implementacion K8S/Codigo` en PowerShell:

```powershell
.\scripts\start-baseline.ps1 -SeedDemoData
```

Cuando el arranque termine correctamente:

```powershell
.\scripts\smoke-baseline.ps1
```

La primera ejecución construye cuatro imágenes y genera contraseñas aleatorias en `.env`, ignorado por Git; un archivo existente se conserva. `-SeedDemoData` agrega únicamente datos de laboratorio ausentes. Omitirlo si no corresponde cargar demos. El Job/servicio `pharmago-db-migrate` ejecuta las migraciones antes de Users y Pharmacy; ver [migraciones](../../docs/aiops-sql-migrations.md).

| Servicio | Acceso local |
|---|---|
| Angular | http://127.0.0.1:4200 |
| Gateway | http://127.0.0.1:5000 |
| Users | http://127.0.0.1:5001 |
| Pharmacy | http://127.0.0.1:5002 |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |

Usar las credenciales locales vigentes. Las contraseñas de SQL/Grafana no son constantes indicadas por esta guía; los usuarios de demo se describen en el seed docente. El baseline configura retención de Prometheus de dos días, no los treinta del Compose heredado.

Para detener este baseline conservando datos:

```powershell
.\scripts\stop-baseline.ps1
```

No se requiere eliminar volúmenes para reiniciar. La [guía del baseline](BASELINE.md) explica login con credencial de prueba, diagnóstico y `-SkipBuild` para reiniciar sin recompilar cuando corresponda.

## Pruebas y evidencias

Desde la raíz del repositorio:

```powershell
dotnet test 'Implementacion K8S/Codigo/Backend/PharmaGo.sln'
```

La [suite del 14/11](../../docs/evidence/test-isolation-20261114/README.md) pasó 319/319; ese resultado no sustituye las pruebas de despliegue o navegador. Para Cypress + Cucumber seguir la [guía BDD](Frontend/e2e/README.md), que usa Node 22.16 de forma separada del build Angular con Node 16 del Dockerfile.

Para el estado de Kubernetes, trazas, logs, alertas, ML y caos, consultar el [resumen contrastado](../../docs/estado-actual.md) y la [matriz](../../docs/aiops-requirements-matrix.md). El Collector/Prometheus del baseline no acreditan por sí solos la observabilidad central validada en Kubernetes.

