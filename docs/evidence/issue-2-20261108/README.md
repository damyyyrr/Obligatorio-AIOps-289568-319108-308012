# Issue #2 — implementación local y límites de validación

Fecha: 08/11/2026 (Uruguay). Base: commit `486bdce` de `obligatorio`. Implementación en `feature/issue-2-k8s-reproducible`, con cambios locales sin commit, push ni modificación de issues remotas.

## Causas corregidas

- PowerShell borraba PVs incondicionalmente; Bash eliminaba los Released/Failed. Ahora ninguno borra namespace, PV ni PVC. Un volumen que requiere recuperación detiene el apply antes de mutar recursos.
- Los errores de comandos intermedios podían quedar ocultos por `$LASTEXITCODE` posterior. Ahora cada comando externo se comprueba individualmente.
- Los timeouts de SQL/Elasticsearch continuaban hacia consumidores. Ahora producen error y detienen el flujo.
- PowerShell omitía Fluent Bit; ambos sistemas usan un inventario común que incluye RBAC, Deployments y DaemonSets.
- Se dependía del directorio actual y de nombres de nodos `minikube*`. Ahora las rutas son absolutas y las etiquetas son una decisión explícita previa, sin sobrescritura automática.
- Se usaban imágenes latest y se reiniciaba UI implícitamente. Ahora se exige tag de aplicación, versiones operativas fijas, carga por perfil comprobado y verificación de tag/ID en cada nodo. SQL reutiliza el digest ya registrado en el baseline; no se ha comprobado su disponibilidad remota en esta sesión.
- Cleanup eliminaba namespace y volúmenes por defecto. Ahora reduce réplicas de Deployments a cero y conserva el resto, incluidos los DaemonSets. Reaplicar restaura las réplicas declaradas.

## Verificaciones ejecutadas

1. Entorno Python aislado en `.runtime/k8s-venv`; instalación correcta de PyYAML 6.0.3.
2. `python -m unittest discover -s 'Implementacion K8S/Codigo/k8s' -p 'test_*.py' -v`: pruebas con dobles de comandos/cluster y validación del inventario YAML. Ver `checks.json` para conteo y resultado de la ejecución final.
3. Parser de PowerShell sobre scripts `.ps1` y `bash -n` individual sobre scripts `.sh`.
4. Render local de todos los recursos con tag de prueba y salida a `.runtime/issue2-render.json`. No se publica porque contiene el Secret docente existente.
5. Comprobación de errores de entrada y del bloqueo previo a cualquier apply cuando falta contexto Kubernetes, usando los entrypoints PowerShell y Bash.
6. `git diff --check`.

Las pruebas cubren contexto incorrecto, falta de roles, hostPath con varios nodos elegibles, PV Released o de otro propietario, fallos tempranos, timeouts de SQL/Elasticsearch, repetición sin deletes, conservación de identidades, perfil Minikube incorrecto, carga de imágenes y referencias entre recursos. Son verificaciones de lógica y configuración: no demuestran persistencia real.

## Validación integral pendiente

Docker CLI está instalado pero el engine Linux no responde (`dockerDesktopLinuxEngine` ausente). `kubectl config current-context` falla porque no hay contexto configurado. Minikube no está en PATH. No se ha arrancado, creado ni eliminado infraestructura.

Falta construir/cargar las cuatro imágenes reales, aplicar todos los recursos en un clúster, esperar rollouts, cargar datos de prueba y comparar login, catálogo y registros SQL antes/después de un segundo apply y de parada/arranque. El procedimiento está en el README Kubernetes. La identidad de PV/PVC es necesaria pero no reemplaza la comparación de datos. La issue #2 debe permanecer abierta hasta reunir esa evidencia; los criterios de #3/#4 y los otros requisitos académicos siguen abiertos.

## Actualización posterior: validación real aprobada

El bloqueo inicial de entorno se resolvió: se instaló Minikube, se recuperó Docker y se liberó espacio mediante limpieza autorizada. La ejecución real permitió corregir el digest de verificación de imágenes; pasan 17 pruebas de regresión y los tres escenarios reales de instalación/reapply/parada-arranque. El resultado vigente y sus límites están en [live/README.md](live/README.md). Las limitaciones de entorno anteriores describen la primera revisión, no el estado final.
