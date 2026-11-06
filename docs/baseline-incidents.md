# Operación e incidentes del baseline local

Versión inicial del 06/11/2026; pendiente de validación en escenarios de caos. Alcance: proyecto Compose `pharmago-baseline` en esta computadora. No se opera infraestructura externa.

Antes de una prueba, una persona debe asumir coordinación y registro; otra, si está disponible, observa métricas y ejecuta la recuperación acordada. No se asignan nombres por defecto. Usar una única bitácora local con timestamps ISO 8601, run ID, hipótesis, cambios y resultado. No enviar notificaciones ni mensajes externos automáticamente.

## Clasificación inicial

- S1: el ensayo afecta la estabilidad del host, hay OOM/reinicios reiterados o riesgo para otros trabajos. Abortar inmediatamente el ensayo y detener solo este baseline; preservar volúmenes.
- S2: el host permanece estable, pero login o consultas por gateway fallan. Detener tráfico de prueba, capturar diagnóstico y restaurar el servicio afectado.
- S3: aplicación funcional con métricas/logs incompletos. Registrar el fallo de observabilidad; no declarar exitoso el criterio afectado.

## Procedimiento

1. Preparar: confirmar proyecto, puertos, recursos, volumen de prueba y límites. No hay carga masiva ni inyección de fallas autorizada por este incremento.
2. Detectar: revisar `docker compose ... ps`, memoria con `stats --no-stream`, readiness y peticiones funcionales; guardar hora de primer síntoma y detección.
3. Responder: detener el generador de prueba, capturar solo logs/configuración sin secretos. Registrar reconocimiento y acciones. No reiniciar servicios de otros proyectos.
4. Recuperar: ante presión del host, usar `scripts/stop-baseline.ps1`. Para recuperar un servicio, diagnosticar su dependencia antes de reiniciarlo. Ante errores de schema/seed, conservar DB y logs; no borrar volúmenes ni repetir migraciones destructivas. Corregir la causa y reintentar el arranque existente con `-SkipBuild` si no cambió código.
5. Validar: repetir smoke funcional y verificar targets, métrica y log correlacionado. Confirmar estabilidad antes de cualquier nuevo ensayo.
6. Aprender: redactar impacto, línea temporal, causa sustentada, acciones, limitaciones y próxima mejora; evitar atribuir causalidad sin evidencia.

Para cada medición definir `t_inicio`, `t_deteccion`, `t_reconocimiento` y `t_restauracion`. Registrar TTD, TTA y TTRestore con sus intervalos explícitos y la convención del curso; un ensayo produce tiempos individuales, no un promedio representativo. Nunca registrar contraseñas, tokens o respuestas de login completas en evidencia.
