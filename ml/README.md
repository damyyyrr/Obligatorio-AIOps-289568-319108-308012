# Detección de anomalías: Isolation Forest y One-Class SVM RBF

La implementación de #14 está ejecutada y verificada sobre el material docente disponible. Ver [resultados completos](../docs/evidence/issue-14-20261112/results/RESULTS.md), [evidencia y reproducción](../docs/evidence/issue-14-20261112/README.md) y [notebook ejecutado](algoritmos.ipynb). No requiere Docker ni Kubernetes.

**Q03 sigue pendiente:** falta confirmación docente de que este dataset/protocolo sea admitido para el obligatorio. El resultado técnico no equivale a aceptación académica ni a validación en producción. El notebook original `practico_detectores_aiops.ipynb` se conserva sin modificar, incluidos sus TODO de la ampliación #20.

## Material y protocolo

| Elemento | Procedencia o decisión |
|---|---|
| Entrada disponible | Notebook docente adjunto `practico_detectores_aiops.ipynb`, 24 celdas; generación en celda 4, índice cero |
| Dataset | 300 ventanas de un minuto de checkout sintético, semilla 42; 53 ventanas anómalas para evaluación |
| Variables | `requests` (requests/min), `error_rate` (fracción), `latency_ms` (media de ventana, ms), `cpu_pct` (%) |
| Tiempo | Fechas sintéticas del 03/06/2026, sin zona horaria; no son incidentes medidos en PharmaGo |
| Etiquetas | `kind` e `is_anomaly` solo para tablas/métricas posteriores; no se usan en scaler, fit ni selección de parámetros |
| Ajuste | StandardScaler y ambos modelos sobre las mismas 300 ventanas, incluidas las contaminadas, conforme al práctico |
| Evaluación | Descriptiva sobre esas mismas ventanas; sin partición hold-out ni inferencia de generalización |

`dataset.py` conserva el orden de las operaciones y sorteos de la celda docente. Un test compara **cada valor y etiqueta** con la celda original. Si el docente cambia el insumo, adaptar explícitamente carga y protocolo; no asumir que las mismas 300 ventanas o parámetros son apropiados para cualquier otro archivo. No se inventó ni descargó otro dataset.

## Ejecutar por CLI

Python **3.11**, desde raíz del repo. Entorno aislado y dependencias directas/transitivas fijadas mediante requirements/constraints:

```powershell
python -m venv .runtime/ml-venv
$py = (Resolve-Path '.runtime/ml-venv/Scripts/python.exe').Path
& $py -m pip install -r ml/requirements.txt
& $py -m pip check
& $py -m unittest discover -s ml -p 'test_*.py' -v
$env:MPLCONFIGDIR = (Join-Path (Get-Location) '.runtime/ml-matplotlib')
& $py ml/run.py --output .runtime/ml-results
```

Linux/macOS: usar `.runtime/ml-venv/bin/python` y `export MPLCONFIGDIR="$PWD/.runtime/ml-matplotlib"`. El controlador de ejecución usa un worker de IF y limita bibliotecas numéricas a un hilo durante ajuste/scoring. La muestra es pequeña; no inicia servicios ni cargas de infraestructura.

La CLI genera `dataset.csv`, `predictions.csv` con scores/flags para cada ventana, `metrics.csv`, `by_kind.csv`, `errors.json` con todos los FP/FN y sus vectores, `run.json` con parámetros/scaler/versiones/hashes, tres PNG y `RESULTS.md`. `--output` elige dónde escribir esos artefactos, sin borrar directorios. No se guardan objetos pickle/joblib; los modelos se reconstruyen a partir del insumo y parámetros.

## Ejecutar el notebook

El [notebook versionado](algoritmos.ipynb) ya incluye la ejecución y sus figuras. Para repetirlo con el mismo código de la CLI, instalar las dependencias opcionales:

```powershell
& $py -m pip install -r ml/requirements-notebook.txt
& $py ml/execute_notebook.py --output .runtime/algoritmos-ejecutado.ipynb
```

El helper utiliza **ese mismo Python** como kernel temporal y lo elimina al terminar, sin registrar kernels globales. Ejecuta todas las celdas desde cero y falla ante errores. También puede abrirse interactivamente seleccionando el entorno ML como kernel. Las celdas importan los módulos comunes: no hay otra implementación divergente de los modelos. `constraints.txt` restringe versiones de paquetes opcionales sin instalarlos si no se piden.

## Modelos y significado de scores

- **Isolation Forest:** `n_estimators=300`, `max_samples=min(256, n)`, `contamination=0.10`, `random_state=42`; un worker. Score `-forest.score_samples(X)` y flag `forest.predict(X) == -1`. El cuantil de contaminación fija el corte de alertas de la muestra; el umbral aprendido se guarda en `run.json`. [API 1.7](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.IsolationForest.html).
- **One-Class SVM:** `kernel="rbf"`, `nu=0.10`, `gamma="scale"`, sobre el mismo X escalado. Score `-ocsvm.decision_function(X)` y flag `predict(X) == -1`; umbral del score 0. Nu limita la fracción de errores de entrenamiento y acota inferiormente la fracción de support vectors en el modelo teórico; no es un cuantil que obligue a 30 flags exactas. Se comprueba convergencia. [API 1.7](https://scikit-learn.org/1.7/modules/generated/sklearn.svm.OneClassSVM.html).
- **Escalado:** único StandardScaler ajustado a las cuatro columnas; orden explícito, validación de faltantes/NaN/inf y de alineación de índices. Los parámetros del scaler quedan guardados. Scores más altos significan mayor anomalía, pero las escalas de ambos modelos no son comparables y no son probabilidades. [StandardScaler 1.7](https://scikit-learn.org/1.7/modules/generated/sklearn.preprocessing.StandardScaler.html).

## Resultado observado

| Modelo | Alertas | TP | FP | FN | TN | Precisión | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Isolation Forest | 30 | 24 | 6 | 29 | 241 | 0,800000 | 0,452830 | 0,578313 |
| One-Class SVM RBF | 29 | 18 | 11 | 35 | 236 | 0,620690 | 0,339623 | 0,439024 |

Son métricas **por ventana sobre la muestra de entrenamiento**, no por incidente. IF tiene mayor F1 en este ejercicio, sin que eso pruebe superioridad general. El presupuesto cercano al 10% es menor que el 17,7% de ventanas etiquetadas anómalas; no se alteró para mejorar el resultado.

El conteo por `kind` muestra los compromisos operativos: IF/OCSVM alertan 4/5 minutos batch legítimos de un total de 20; detectan 8/4 de los ocho minutos `incidente_5xx`; en `degradacion` detectan 0/1 de 18. Los dos modelos no incorporan una secuencia temporal como feature. La alerta estadística debe interpretarse con contexto, logs/trazas y política de incidentes; estos resultados no miden MTTD ni automatizan mitigación.

K-sigma/MAD, comparación de seis flags, siete preguntas y exit ticket del cuaderno completo quedan en #20 salvo confirmación docente. #14 no rellena esas secciones para simular que el práctico completo ya está terminado. Ver [consultas académicas](../docs/aiops-open-questions.md).
