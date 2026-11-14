# PharmaGo — Obligatorio AIOps

Fork de [jirabedra/AIOps](https://github.com/jirabedra/AIOps). La rama de integración del equipo es **`obligatorio`**, basada en `feature/k8s`. `main` conserva la referencia original mínima del curso.

El baseline local de Compose fue verificado el 06/11/2026: ocho servicios activos y catorce comprobaciones funcionales/de telemetría aprobadas antes y después de una parada/reinicio. Después se registraron validaciones locales de Kubernetes/datos, recuperación, rollout/rollback, observabilidad, ML, BDD y seis escenarios de caos. Ver [estado contrastado al 14/11](docs/estado-actual.md), con enlaces a cada evidencia y sus límites. La separación física, el alcance de disponibilidad y la aceptación del dataset conservan consultas académicas abiertas; el cierre técnico de las issues no las resuelve.

## Empezar

Requisitos: Git, PowerShell y Docker Desktop en modo Linux. El baseline requiere al menos 3,5 GiB asignados al motor; revisar la capacidad del host antes de cambiar sus recursos.

```powershell
git clone --branch obligatorio https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012.git
cd 'Obligatorio-AIOps-289568-319108-308012/Implementacion K8S/Codigo'
.\scripts\start-baseline.ps1 -SeedDemoData
.\scripts\smoke-baseline.ps1
```

Aplicación: http://127.0.0.1:4200. Prometheus: http://127.0.0.1:9090. Grafana: http://127.0.0.1:3000. El arranque genera contraseñas locales en `.env`, ignorado por Git; el seed docente contiene los usuarios de laboratorio. Para parar conservando los datos: `.\scripts\stop-baseline.ps1`.

Ver la [guía de arranque y diagnóstico](<Implementacion K8S/Codigo/BASELINE.md>) y el [reporte con evidencias](docs/BASELINE_RESULT.md).

## Trabajo del equipo

- [Issues del obligatorio](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues) y [mapa de trabajo](docs/GITHUB_ISSUES.md).
- [BDD Cypress + Cucumber: ejecución de #15](Implementacion%20K8S/Codigo/Frontend/e2e/README.md), cuatro escenarios aprobados en navegador contra el baseline real; [evidencia](docs/evidence/issue-15-20261112/live-after-fix/README.md).
- [Plan maestro](docs/aiops-master-plan.md), [estado de implementación](docs/AIops-implementation-plan.md) y [matriz de requisitos](docs/aiops-requirements-matrix.md).
- [Consultas académicas pendientes](docs/aiops-open-questions.md), [plan de incidentes](docs/baseline-incidents.md), [seis runbooks](docs/runbooks/incidentes.md) y [algoritmos ML con resultados reproducibles](ml/README.md).
- [Seis escenarios de caos y recuperación](<Implementacion K8S/Codigo/chaos-engineering/README.md>): seis ensayos reales PASS locales y [repetición guiada por el operador](docs/evidence/issue-16-20261113/README.md), con efectos, restauración y limpieza verificados. Red/Service se evalúan sobre conexiones nuevas. [#16](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/16) está cerrada para plan y aplicación guiada local; la revisión independiente quedó como mejora opcional no realizada.
- [Suite .NET, 14/11](docs/evidence/test-isolation-20261114/README.md): **319/319 pruebas aprobadas** después de corregir únicamente el aislamiento de una prueba en el PR #42.

Cada integrante toma una issue pendiente y se asigna como responsable. Crear una rama desde `obligatorio`, referenciar la issue en commits y abrir el PR contra `obligatorio`. Revisar dependencias antes de empezar; coordinar cambios compartidos en Compose/manifests y no cerrar una issue por tener archivos escritos sin probarlos. Las prioridades y los hitos permiten filtrar el trabajo sin asignar personas por suposición.

Antes de subir cambios, excluir `.env`, tokens, credenciales y datos ajenos al proyecto. Actualizar la matriz y adjuntar las pruebas que permitan reproducir el resultado. El enunciado original y las capturas docentes se consultan en los materiales del curso; la matriz del repositorio es una síntesis de trabajo.

Entrega: **16/11/2026, 21:00 de Uruguay**. Defensa obligatoria: **23/11/2026**. Las consultas Q01–Q04 siguen abiertas; no se supone resuelta la aceptación de Minikube o del dataset adjunto.
