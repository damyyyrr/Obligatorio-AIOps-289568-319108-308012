# Consultas académicas pendientes

Preparadas el 06/11/2026. No enviadas a terceros y sin respuestas registradas. La implementación local puede continuar sin presentar estos puntos como resueltos.

| ID | Consulta para el docente | Criterio afectado |
|---|---|---|
| Q01 | La letra exige nodos físicos diferentes: ¿se admite Minikube multinodo en un host para la evaluación? ¿Qué separación se exige para gateway y réplicas del mismo servicio? | R01 y diseño de infraestructura; sin aclaración se mantiene la exigencia literal |
| Q02 | ¿El reemplazo sin interrupción se evalúa en frontend/gateway/microservicios o incluye DB y componentes de observabilidad? | R03 incompleto: SQL sigue sin continuidad durante su reemplazo. La consulta pendiente no excluye DB ni observabilidad del trabajo requerido |
| Q03 | ¿El dataset sintético del práctico adjunto es válido para el obligatorio o se proporcionará otro dataset/protocolo? ¿Se exige también entregar k-sigma/MAD y las respuestas del práctico? | R05 y alcance de E05 |
| Q04 | La letra menciona hasta tres integrantes y el recordatorio hasta dos: ¿cuál es el límite vigente? | Integración del equipo y entrega |

Al recibir una respuesta, registrar fecha, origen, contenido y evidencia; ajustar matriz/plan y conservar la distinción entre interpretación y requisito confirmado.

Seguimiento del 09/11/2026. El equipo indicó que Q02 sigue sin confirmación del docente. La prueba de la #5 cubre las migraciones y el rollback funcional de Users. La aceptación de disponibilidad durante el reemplazo de SQL y observabilidad sigue pendiente.

Seguimiento del 11/11/2026. Se verificó el apartado «Despliegues seguros» del enunciado original: exige reemplazar componentes con 100% de disponibilidad y explicar la técnica, sin enumerarlos ni excluir SQL. Q02 es una consulta del equipo y no una excepción docente. Se conserva SQL en el alcance de trabajo: #5 resolvió migraciones y rollback de aplicación; #8 midió el recambio de Gateway, Users y Pharmacy con SQL estable. La continuidad durante reemplazo de SQL sigue sin implementar ni probar. El [pendiente y la evidencia necesaria](aiops-sql-migrations.md#disponibilidad-de-sql-y-q02) se mantienen aunque esas issues se cierren.
