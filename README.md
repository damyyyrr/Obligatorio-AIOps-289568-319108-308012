# PharmaGo — Obligatorio AIOps

Fork de [jirabedra/AIOps](https://github.com/jirabedra/AIOps). La rama de integración del equipo es **`obligatorio`**, basada en `feature/k8s`. `main` conserva la referencia original mínima del curso.

El baseline local de Compose fue verificado el 06/11/2026: ocho servicios activos y catorce comprobaciones funcionales/de telemetría aprobadas antes y después de una parada/reinicio. Kubernetes ya cuenta con validaciones locales de despliegue, datos, métricas, recuperación y [rollout/rollback de aplicación](docs/evidence/issue-8-20261111/README.md). La separación física, el alcance completo de disponibilidad, observabilidad, caos y ML conservan sus pendientes en la matriz.

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
- [Plan maestro](docs/aiops-master-plan.md), [estado de implementación](docs/AIops-implementation-plan.md) y [matriz de requisitos](docs/aiops-requirements-matrix.md).
- [Consultas académicas pendientes](docs/aiops-open-questions.md), [procedimiento inicial de incidentes](docs/baseline-incidents.md) y [práctico de ML](ml/README.md).

Cada integrante toma una issue pendiente y se asigna como responsable. Crear una rama desde `obligatorio`, referenciar la issue en commits y abrir el PR contra `obligatorio`. Revisar dependencias antes de empezar; coordinar cambios compartidos en Compose/manifests y no cerrar una issue por tener archivos escritos sin probarlos. Las prioridades y los hitos permiten filtrar el trabajo sin asignar personas por suposición.

Antes de subir cambios, excluir `.env`, tokens, credenciales y datos ajenos al proyecto. Actualizar la matriz y adjuntar las pruebas que permitan reproducir el resultado. El enunciado original y las capturas docentes se consultan en los materiales del curso; la matriz del repositorio es una síntesis de trabajo.

Entrega: **16/11/2026, 21:00 de Uruguay**. Defensa obligatoria: **23/11/2026**. Las consultas Q01–Q04 siguen abiertas; no se supone resuelta la aceptación de Minikube o del dataset adjunto.
