# Decisiones de alcance del equipo

Los puntos antes identificados como Q01–Q04 se registraron como decisiones D01–D04. D01 incorpora el despliegue físico documentado; los laboratorios anteriores conservan sus resultados y límites. El estado por requisito se consulta en la [matriz](aiops-requirements-matrix.md).

| ID | Decisión del equipo | Alcance y límites |
|---|---|---|
| D01 — Plataforma | Desplegar Gateway, Users y Pharmacy en tres PCs físicas con k3s en WSL2 y Tailscale. Conservar Minikube multinodo y el perfil local con Calico para los ensayos anteriores. | La [evidencia física](evidence/chaos-3pc-20261116/README.md) acredita la distribución documentada, caos y recuperación de procesos. PC A concentra Gateway, SQL, servidor k3s y observabilidad. Rollout/rollback, restauración SQL y validación detallada de telemetría conservan su alcance local; no se acredita tolerancia a la pérdida de una PC. |
| D02 — Reemplazo | Evaluar el recambio sin interrupciones de Gateway, Users y Pharmacy mediante RollingUpdate y rollback compatibles. Mantener frontend, SQL y observabilidad estables durante ese ensayo. | SQL Express conserva una réplica y Recreate. El 100 % observado corresponde a 226 solicitudes del ensayo; no demuestra recambio sin interrupciones de SQL, frontend u observabilidad ni disponibilidad global. |
| D03 — Dataset | Adoptar el dataset sintético del notebook docente adjunto: 300 ventanas, semilla 42 y su protocolo de ajuste/evaluación. Entregar Isolation Forest y One-Class SVM RBF; mantener k-sigma/MAD y el resto del práctico como ampliación opcional. | Las métricas son descriptivas sobre entrenamiento. Los datos no provienen de PharmaGo y no acreditan generalización ni detección operativa. |
| D04 — Integrantes | Mantener el equipo de tres integrantes: Joaquín Decia, Vicente Lavega y Damián Rodríguez, siguiendo la condición de hasta tres de la sección principal de la letra. | Se conserva identificada la discrepancia con el recordatorio de hasta dos. La decisión no acredita por sí sola la inscripción o la entrega en Gestión. |

Para caos, el equipo adopta los seis escenarios actuales y sus estímulos acotados, incluido el refuerzo de escritura sostenida de storage. Se documentan los efectos medidos y la limpieza; no se afirma saturación del dispositivo, disco lleno u OOM cuando no se observaron.

Estas son decisiones del equipo sobre su entrega, sin atribuir aprobación al docente ni cambiar los requisitos literales o las mediciones. Las evidencias originales conservan fechas, commits, hashes y estados de sus capturas; las referencias históricas a Q01–Q04 se interpretan con esta actualización de alcance.
