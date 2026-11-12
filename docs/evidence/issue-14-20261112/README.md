# Issue #14: ejecución de Isolation Forest y One-Class SVM RBF

Implementación en `feature/issue-14-algoritmos`, creada desde `54d5a17c68cb7ede122b92862ad156163a0b09d9` de `obligatorio`. Ejecución del **12/11/2026**, Python 3.11.0 en Windows. Los resultados se capturaron con el árbol modificado durante el incremento; `results/run.json` conserva ese estado, hashes de fuentes/artefactos y versiones exactas. Las fuentes y salidas de texto nuevas usan LF explícito para conservar sus hashes al versionarlas y clonarlas en Windows.

**Resultado técnico reproducido; aceptación académica pendiente de Q03.** El criterio de cierre de #14 admite identificar explícitamente esa aceptación pendiente. No se declara R05 aceptado por el docente ni se cierra la consulta #1.

## Procedencia y protocolo

Único material de entrada en `ml/`: el [notebook docente](../../../ml/practico_detectores_aiops.ipynb), conservado sin cambios, con 24 celdas. Su celda de índice 4 genera 300 minutos sintéticos de checkout con `np.random.default_rng(42)`. [dataset.py](../../../ml/dataset.py) reproduce esa generación y se prueba igualdad exacta de todos los valores frente a la celda original. El hash canónico del notebook y los hashes de scripts están en [run.json](results/run.json).

Cuatro features: requests/min, fracción de errores, latencia media en ms y CPU %. El tiempo es sintético, sin zona horaria; no son datos de PharmaGo ni una captura de caos. `kind` e `is_anomaly` se usan solo después del ajuste para evaluar las 53 ventanas etiquetadas anómalas. Batch (20 minutos) y pico de carga (8) son legítimos.

Scaler y ambos modelos se ajustan sobre **todas las 300 ventanas**, incluidas las contaminadas, por instrucción del práctico. No se sustituyó por entrenamiento solo en normales ni por train/test split. IF: 300 árboles, muestras min(256,n), contaminación 0,10 y semilla 42. OCSVM: RBF, nu 0,10 y gamma scale. No se tunearon parámetros ni umbrales usando las etiquetas.

## Artefactos reales

| Salida | Contenido |
|---|---|
| [RESULTS.md](results/RESULTS.md) | Tablas, interpretación, límites y las tres figuras |
| [dataset.csv](results/dataset.csv) | Las 300 ventanas generadas, incluidas etiquetas solo de evaluación |
| [predictions.csv](results/predictions.csv) | Cuatro features originales, timestamps, etiquetas, scores y flags de ambos modelos |
| [metrics.csv](results/metrics.csv) | Precisión, recall, F1, TP/FP/FN/TN y conteos por ventana |
| [by_kind.csv](results/by_kind.csv) | Alertas y mediana de scores por cada tipo de ventana |
| [errors.json](results/errors.json) | Todos los FP/FN de cada modelo, con vector de cuatro features, tipo, tiempo y score |
| [run.json](results/run.json) | Procedencia, protocolo, parámetros completos, estado del scaler, convergencia, versiones y hashes |
| [Notebook ejecutado](../../../ml/algoritmos.ipynb) | Siete celdas de código ejecutadas desde cero, sin errores, y tres figuras embebidas |

## Resultados y lectura operativa

| Modelo | Alertas | TP | FP | FN | TN | Precisión | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Isolation Forest | 30 | 24 | 6 | 29 | 241 | 0,800000 | 0,452830 | 0,578313 |
| One-Class SVM RBF | 29 | 18 | 11 | 35 | 236 | 0,620690 | 0,339623 | 0,439024 |

IF logra mayor F1 en esta muestra. La tabla por tipo muestra por qué ese agregado no alcanza: detecta los ocho minutos `incidente_5xx` frente a cuatro de OCSVM, pero omite los 18 de `degradacion` mientras OCSVM detecta uno. Ambos alertan actividad batch legítima: cuatro y cinco minutos de veinte, respectivamente. OCSVM también alerta dos de los ocho minutos `pico_carga`; IF, ninguno.

Las métricas son **descriptivas sobre la misma muestra usada al entrenar**, no validación fuera de muestra, probabilidad de incidente o MTTD. El presupuesto de IF y la restricción nu de OCSVM no equivalen a la verdad de referencia del 17,7%. Una ventana estadísticamente rara puede ser legítima y una tendencia puede pasar desapercibida sin features temporales. No se afirma qué modelo conviene en producción a partir de esta comparación.

## Verificaciones

- **20 pruebas aprobadas**: procedencia exacta y semilla local; labels/columnas adversariales sin efecto en fit; ajuste sobre las 300 ventanas; parámetros, convergencia y dirección de scores; repetición exacta; input sin mutaciones; índices; faltantes/NaN/inf; evaluación con matriz de confusión conocida; ausencia/errores de etiquetas y caso de una sola clase.
- **Dos ejecuciones CLI** en el venv: dataset, predicciones/scores/flags, métricas, conteos y errores idénticos byte a byte; mismo estado de modelos y scaler. La hora de ejecución y metadatos de Git no se usan para comparar determinismo. [Resumen de verificación](verification.json).
- **Notebook completo ejecutado** con kernel del mismo venv, sin kernels globales; siete celdas de código terminadas y salidas revisadas. Reutiliza módulos comunes de la CLI, sin duplicar algoritmos.
- `pip check` sin dependencias rotas, figuras inspeccionadas visualmente y revisión de formato/referencias. No se inició Docker/Kubernetes ni servicios de aplicación.

Dependencias directas y restricciones transitivas están en [requirements](../../../ml/requirements.txt), [opcionales de notebook](../../../ml/requirements-notebook.txt) y [constraints](../../../ml/constraints.txt). La [guía ML](../../../ml/README.md) contiene los comandos para reproducir CLI, tests y notebook, incluyendo alternativas de ruta en Linux/macOS. La repetición exacta se verificó en este entorno; no se presume igualdad binaria de PNG/solvers entre plataformas diferentes.

## Alcance y pendientes

Q03 sigue sin respuesta docente registrada sobre dataset/protocolo aceptado. Si se proporciona otro insumo, identificarlo y acordar su protocolo antes de adaptar la carga/evaluación; no imponerle automáticamente este diseño. La ampliación k-sigma/MAD y el cierre completo del práctico siguen en #20. Los modelos no se integran al monitoreo de producción ni sustituyen los umbrales de Grafana en esta issue.

Implementación asistida por Codex usando la issue #14, el notebook adjunto y el plan del repositorio como contexto. El código, las decisiones de protocolo, los datos sintéticos exportados y los resultados quedan disponibles para revisión del equipo; no se atribuye aprobación académica ni conclusiones a un docente sin evidencia.
