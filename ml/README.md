# Material de detección de anomalías

`practico_detectores_aiops.ipynb` es una copia sin modificaciones del notebook docente adjunto por el equipo. Genera 300 ventanas sintéticas de un servicio checkout; contiene TODO de k-sigma, MAD, Isolation Forest y One-Class SVM RBF. No se presenta como implementación terminada.

Para el obligatorio se requieren IF y SVM RBF. Q03 en [consultas académicas](../docs/aiops-open-questions.md) debe confirmar si este dataset se admite para la entrega o si se proporcionará otro. La aceptación pendiente no impide implementar y probar los modelos sobre el material disponible, identificándolo correctamente.

El notebook especifica escalado de las cuatro features y entrenamiento no supervisado sobre las 300 ventanas. `kind` e `is_anomaly` se usan exclusivamente para evaluación. Mantener ese protocolo al completar el práctico; si el docente define otro dataset/protocolo, documentarlo separadamente. k-sigma, MAD, las preguntas y el exit ticket son ampliación salvo confirmación docente.

Dependencias usadas por el material: Python, Jupyter/IPython, NumPy, pandas, Matplotlib y scikit-learn. La issue de ML debe fijar versiones y agregar la ejecución reproducible; no hay todavía resultados de entrenamiento verificados en este repositorio.
