# PharmaGo — Obligatorio AIOps

Este repositorio contiene el obligatorio de AIOps desarrollado sobre **PharmaGo**, una aplicación basada en microservicios. El objetivo es desplegarla, observar su funcionamiento y evaluar cómo responde ante fallas y cambios de versión.

El trabajo integra Kubernetes, monitoreo de logs, métricas y trazas, detección de anomalías con Isolation Forest y One-Class SVM, pruebas automatizadas y procedimientos de respuesta a incidentes. Incluye el código, las guías de ejecución y las evidencias de las pruebas realizadas, tanto en el laboratorio local como en un despliegue distribuido en tres PCs físicas.

## Entrega y evidencias

- [Informe académico en PDF — 10 páginas](docs/entrega/Informe_Final_AIOps.pdf) y [fuentes del informe](docs/entrega/README.md).
- [Matriz de requisitos y evidencias](docs/aiops-requirements-matrix.md).
- [Despliegue y caos en tres PCs](docs/evidence/chaos-3pc-20261116/README.md), con [diagrama de la topología](docs/evidence/chaos-3pc-20261116/topologia-3pc.png), nodos, pods y reportes.
- [Estado contrastado del proyecto](docs/estado-actual.md), con las validaciones y sus límites.

El informe y la matriz distinguen las pruebas del laboratorio local de las realizadas en tres PCs. Los resultados de caos no acreditan por sí solos un rollout sin interrupciones entre las tres PCs.

## Empezar

Clonar el repositorio y entrar en su raíz:

```powershell
git clone --branch obligatorio https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012.git
cd 'Obligatorio-AIOps-289568-319108-308012'
```

### Kubernetes

- **Tres PCs físicas:** consultar la [topología, preparación y resultados con k3s/Tailscale](docs/evidence/chaos-3pc-20261116/README.md). La carpeta `setup/` conserva los scripts usados, incluido el intento inicial con Hamachi y la migración a Tailscale; no constituye un instalador completo desde cero.
- **Laboratorio local con Minikube:** seguir la [guía de despliegue Kubernetes](<Implementacion K8S/Codigo/k8s/README-k8s.md>) y la [guía de topología y capacidad](docs/aiops-k8s-topology.md). Requiere Python 3.10+, las dependencias indicadas en la guía, kubectl, Docker y Minikube. Un clúster de tres nodos sobre una PC acredita separación lógica entre nodos.

Seleccionar y comprobar el contexto y la capacidad disponible antes de desplegar. Las pruebas de [recuperación de datos](docs/aiops-k8s-recovery.md), [rollout/rollback](docs/aiops-k8s-rollout.md) y [caos](<Implementacion K8S/Codigo/chaos-engineering/README.md>) tienen guías y evidencias propias.

### Baseline local con Docker Compose

Para el arranque funcional local y las pruebas BDD: Git, PowerShell y Docker Desktop en modo Linux. El baseline requiere al menos 3,5 GiB asignados al motor; revisar la capacidad del host antes de cambiar sus recursos.

Desde la raíz del repositorio:

```powershell
cd 'Implementacion K8S/Codigo'
.\scripts\start-baseline.ps1 -SeedDemoData
.\scripts\smoke-baseline.ps1
```

Aplicación: http://127.0.0.1:4200. Prometheus: http://127.0.0.1:9090. Grafana: http://127.0.0.1:3000. El arranque genera contraseñas locales en `.env`, ignorado por Git; el seed docente contiene los usuarios de laboratorio. Para parar conservando los datos: `.\scripts\stop-baseline.ps1`.

Ver la [guía de arranque y diagnóstico](<Implementacion K8S/Codigo/BASELINE.md>) y el [reporte con evidencias](docs/BASELINE_RESULT.md): el 06/11/2026 se verificaron ocho servicios activos y catorce comprobaciones funcionales/de telemetría antes y después de una parada/reinicio.

## Trabajo del equipo

El proyecto parte del repositorio docente [jirabedra/AIOps](https://github.com/jirabedra/AIOps). Los cambios del equipo se integran en la rama **`obligatorio`**.

- [Issues del obligatorio](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues) y [mapa de trabajo](docs/GITHUB_ISSUES.md).
- [BDD Cypress + Cucumber: ejecución de #15](Implementacion%20K8S/Codigo/Frontend/e2e/README.md), cuatro escenarios aprobados en navegador contra el baseline real; [evidencia](docs/evidence/issue-15-20261112/live-after-fix/README.md).
- [Plan maestro](docs/aiops-master-plan.md), [estado de implementación](docs/AIops-implementation-plan.md) y [matriz de requisitos](docs/aiops-requirements-matrix.md).
- [Decisiones de alcance del equipo](docs/aiops-open-questions.md), registradas antes de la ejecución en tres PCs; [plan de incidentes](docs/baseline-incidents.md), [seis runbooks](docs/runbooks/incidentes.md) y [algoritmos ML con resultados reproducibles](ml/README.md).
- [Guía de seis escenarios de caos y recuperación](<Implementacion K8S/Codigo/chaos-engineering/README.md>), [ejecución en tres PCs](docs/evidence/chaos-3pc-20261116/README.md) y [repetición local guiada por el operador del 13/11](docs/evidence/issue-16-20261113/README.md). Red/Service se evalúan sobre conexiones nuevas; RAM y almacenamiento conservan los límites de sus ensayos. [#16](https://github.com/damyyyrr/Obligatorio-AIOps-289568-319108-308012/issues/16) está cerrada para plan y aplicación guiada local; la revisión independiente quedó como mejora opcional no realizada.
- [Suite .NET, 14/11](docs/evidence/test-isolation-20261114/README.md): **319/319 pruebas aprobadas** después de corregir únicamente el aislamiento de una prueba en el PR #42.

Cada integrante toma una issue pendiente y se asigna como responsable. Crear una rama desde `obligatorio`, referenciar la issue en commits y abrir el PR contra `obligatorio`. Revisar dependencias antes de empezar; coordinar cambios compartidos en Compose/manifests y no cerrar una issue por tener archivos escritos sin probarlos. Las prioridades y los hitos permiten filtrar el trabajo sin asignar personas por suposición.

Antes de subir cambios, excluir `.env`, tokens, credenciales y datos ajenos al proyecto. Actualizar la matriz y adjuntar las pruebas que permitan reproducir el resultado. El enunciado original y las capturas docentes se consultan en los materiales del curso; la matriz del repositorio es una síntesis de trabajo.

Entrega: **16/11/2026, 21:00 de Uruguay**. Defensa obligatoria: **23/11/2026**. Equipo de tres integrantes, dataset docente adjunto y recambio validado de Gateway/Users/Pharmacy en el laboratorio local; consultar las evidencias de cada entorno para conocer el alcance comprobado.
