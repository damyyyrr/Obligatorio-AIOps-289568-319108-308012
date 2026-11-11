# Issue #8 — rollout y rollback con tráfico funcional

Ensayo del **11/11/2026**, rama `codex/issue-8-rollout-rollback`, desde `2e6ef27cfede8297b19a9f7147d8a3120d164a2c` de `obligatorio`, con cambios locales. Se reutilizó `pharmago-issue3`: tres nodos Minikube en una PC, Kubernetes 1.34.1, Minikube 1.39.0 y containerd 2.3.4. El motor Docker disponía de unos 7,7 GiB y los nodos conservaron sus límites existentes. No se modificaron recursos de otros proyectos.

**100% observado en 226 solicitudes durante 282,139 s**, desde `16:07:06.283524 UTC` hasta `16:11:48.422961 UTC` (13:07:06–13:11:48 de Uruguay). No hubo errores HTTP, 429, timeouts, errores de transporte ni fallos de validación. No se descartaron muestras.

| Operación por Gateway | Intentos | HTTP 200 válidos | Latencia p95 | Máxima |
|---|---:|---:|---:|---:|
| Catálogo — `GET /api/drug` | 95 | 95 | 95,973 ms | 884,228 ms |
| Roles — `GET /api/roles` | 95 | 95 | 94,430 ms | 458,259 ms |
| Login — `POST /api/login` | 36 | 36 | 722,931 ms | 739,058 ms |
| Total | 226 | 226 | 96,071 ms | 884,228 ms |

Las latencias son `time_total` de curl dentro del clúster; las marcas de envío/recepción incluyen la sobrecarga de `kubectl exec`. Catálogo y roles conservaron su contenido completo independientemente del orden de la lista. Cada login devolvió un token y el usuario esperado. Las tres rutas acceden a SQL. El generador no reintentó solicitudes y usó una única IP, sin alterar el rate limiting.

## Ventanas y revisiones

| Fase | Solicitudes válidas / enviadas |
|---|---:|
| Antes de migrar | 17 / 17 |
| Job de migración | 5 / 5 |
| Rollout Users | 33 / 33 |
| Rollout Pharmacy | 33 / 33 |
| Rollout Gateway | 19 / 19 |
| Después del rollout | 17 / 17 |
| Rollback Gateway | 21 / 21 |
| Rollback Pharmacy | 31 / 31 |
| Rollback Users | 33 / 33 |
| Después del rollback | 17 / 17 |

La versión A usa `issue7-recovery-20261110`. Antes de medir se instaló en A la política nueva de drenaje y permanencia en Ready. Esa preparación **queda fuera** de la ventana anterior. B usa `issue8-drain-20261111`, con binarios recompilados que agregan el timeout de apagado de 20 s. Los digests de configuración de las tres imágenes nuevas se verificaron contra CRI en sus nodos elegibles y están en [validation.json](validation.json). Las imágenes y digests realmente ejecutados aparecen también en las observaciones de pods.

Se reemplazaron secuencialmente Users, Pharmacy y Gateway. Para cada servicio se observaron pods A y B Ready al mismo tiempo. El muestreo nominal cada 2 s registró 15 pods distintos a lo largo de las seis transiciones, con su nodo, UID, imagen, estado y EndpointSlices. El rollback usó las revisiones originales 14 de Users, 7 de Pharmacy y 6 de Gateway. Las revisiones finales fueron 16, 9 y 8; Kubernetes incrementa el número al restaurar una plantilla anterior. Las tres plantillas restauradas coincidieron íntegramente con las guardadas y quedaron 2/2 Users, 2/2 Pharmacy y 1/1 Gateway listos.

El Job `pharmago-db-migrate-f9a6acc937ae` tomó el bloqueo SQL y terminó con **cero migraciones pendientes**. A y B comparten las diez migraciones históricas y no cambian el esquema. Antes, después de B y después del rollback coincidieron el historial, la huella de medicamentos/usuarios, el UID del pod SQL y los ocho UIDs de cuatro PV/PVC. Se excluyen las sesiones creadas por los logins de la huella de negocio. Los contadores OTLP incluyen las rutas observadas por servicio y pod; no se usan como sustituto del conteo HTTP del cliente.

## Validaciones y reproducción

- **26/26 pruebas Python**: regresiones del despliegue y clasificación/conteo de errores, incluidos 429 y timeouts.
- **Tres builds Docker aprobados**: Gateway, Users y Pharmacy. Users y Pharmacy mantienen advertencias previas de nulabilidad/tipos duplicados.
- **API server dry-run aprobado** para los tres manifests candidatos.
- **.NET: 290/291** en el árbol modificado y **290/291** en una extracción limpia de `obligatorio` (`2e6ef27`). La misma prueba `PurchasesDetailRepositoryTest.Test_GetOneByExpression` falla con `Assert.IsNotNull`; pasa al ejecutarse aislada. Comparte la base InMemory `PharmaGoDb` y busca `Id == 1` aunque el ID se genera al insertar. No se modificaron esa prueba ni su repositorio para ocultar el fallo. Los resultados comparados están en [validation.json](validation.json).
- `git diff --check` aprobado; evidencia revisada para excluir credenciales, tokens y cuerpos HTTP.

Se construyeron las imágenes secuencialmente desde `Implementacion K8S/Codigo/Backend`:

```powershell
docker build -f PharmaGo.ApiGateway/Dockerfile -t pharmago-api-gateway:issue8-drain-20261111 .
docker build -f PharmaGo.UsersService/Dockerfile -t pharmago-users-service:issue8-drain-20261111 .
docker build -f PharmaGo.PharmacyService/Dockerfile -t pharmago-pharmacy-service:issue8-drain-20261111 .
```

Se cargó cada imagen mediante streaming de `docker save` a `ctr -n k8s.io images import -` en el nodo correspondiente y se comparó su digest con `crictl images -o json`. Para otra instalación se puede usar la construcción/carga completa de la [guía Kubernetes](../../../Implementacion%20K8S/Codigo/k8s/README-k8s.md) con un tag nuevo.

Desde la raíz, con `PHARMAGO_TEST_PASSWORD` configurada localmente para el usuario de demo existente:

```powershell
$py = (Resolve-Path '.runtime/k8s-venv/Scripts/python.exe').Path
$k8s = 'Implementacion K8S/Codigo/k8s'
& $py -m unittest discover -s $k8s
& $py "$k8s/verify_rollout.py" --context pharmago-issue3 --image-tag issue8-drain-20261111 --output .runtime/issue8-proof.json
dotnet test 'Implementacion K8S/Codigo/Backend/PharnaGo.Test/PharmaGo.Test.csproj'
```

La [guía de rollout](../../aiops-k8s-rollout.md) detalla preparación, compatibilidad, cuotas, límites y recuperación. [proof.json](proof.json) conserva las 226 muestras, todas las fases, observaciones, métricas y comparaciones. [validation.json](validation.json) conserva los digests, validación de manifests y resultados de suites.

## Límites del resultado

La prueba cubre carga baja y operaciones cortas durante recambios planificados de esos tres procesos, con nodos disponibles. No mide tráfico de navegador, UI, caída de nodo ni operaciones largas de escritura. SQL y observabilidad permanecieron estables; SQL Express conserva una réplica y `Recreate`. Q01/Q02 siguen abiertas y R03 completo no se declara cumplido. El perfil terminó con la versión A restaurada y sus datos conservados. Tras las validaciones se detuvieron únicamente sus tres nodos con `minikube stop -p pharmago-issue3`, como estaban al comenzar.
