# Decisiones de alcance del equipo

El 14/11/2026 el equipo decidió mantener el alcance de la implementación actual. Los puntos antes identificados como Q01–Q04 se registran desde esta revisión como decisiones D01–D04, sin consultas pendientes de envío o respuesta.

| ID | Decisión del equipo | Alcance y límites |
|---|---|---|
| D01 — Plataforma | Usar Minikube en una única PC, con el perfil multinodo para colocación y el perfil de un nodo con Calico para caos. | Los servicios corren en pods independientes. Los nodos virtuales comparten host; no se acredita la separación en máquinas físicas distintas indicada en la letra. |
| D02 — Reemplazo | Evaluar el recambio sin interrupciones de Gateway, Users y Pharmacy mediante RollingUpdate y rollback compatibles. Mantener frontend, SQL y observabilidad estables durante ese ensayo. | SQL Express conserva una réplica y Recreate. El 100 % observado corresponde a 226 solicitudes del ensayo; no demuestra recambio sin interrupciones de SQL, frontend u observabilidad ni disponibilidad global. |
| D03 — Dataset | Adoptar el dataset sintético del notebook docente adjunto: 300 ventanas, semilla 42 y su protocolo de ajuste/evaluación. Entregar Isolation Forest y One-Class SVM RBF; mantener k-sigma/MAD y el resto del práctico como ampliación opcional. | Las métricas son descriptivas sobre entrenamiento. Los datos no provienen de PharmaGo y no acreditan generalización ni detección operativa. |
| D04 — Integrantes | Mantener el equipo de tres integrantes: Joaquín Decia, Vicente Lavega y Damián Rodríguez, siguiendo la condición de hasta tres de la sección principal de la letra. | Se conserva identificada la discrepancia con el recordatorio de hasta dos. La decisión no acredita por sí sola la inscripción o la entrega en Gestión. |

Para caos, el equipo adopta los seis escenarios actuales y sus estímulos acotados, incluido el refuerzo de escritura sostenida de storage. Se documentan los efectos medidos y la limpieza; no se afirma saturación del dispositivo, disco lleno u OOM cuando no se observaron.

Estas son decisiones del equipo sobre su entrega, sin atribuir aprobación al docente ni cambiar los requisitos literales o las mediciones. Las evidencias originales conservan fechas, commits, hashes y estados de sus capturas; las referencias históricas a Q01–Q04 se interpretan con esta actualización de alcance.
