"""Ejecución reproducible del práctico IF/OCSVM; sin Docker, datos externos o etiquetas al fit."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess

from dataset import FEATURES, SEED, generate_dataset
from detectors import counts_by_kind, evaluate, fit_detectors
from plots import make_plots

HERE = Path(__file__).resolve().parent


def table(frame):
    rows = [[str(v) if not isinstance(v, float) else f"{v:.6f}" for v in row]
            for row in frame.itertuples(index=False, name=None)]
    return "\n".join(["| " + " | ".join(frame.columns) + " |",
                      "| " + " | ".join("---" for _ in frame.columns) + " |",
                      *("| " + " | ".join(row) + " |" for row in rows)])


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def experiment():
    data = generate_dataset()
    models = fit_detectors(data)
    predictions = models.score(data)
    return data, models, predictions, evaluate(data, predictions), counts_by_kind(data, predictions)


def export(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data, models, predictions, metrics, counts = experiment()
    notebook = json.loads((HERE / "practico_detectores_aiops.ipynb").read_text(encoding="utf-8"))
    source = {"origin": "notebook docente adjunto; dataset sintético checkout, celda 4",
              "notebook": "ml/practico_detectores_aiops.ipynb", "notebookCanonicalJsonSha256": json_hash(notebook),
              "seed": SEED, "rows": len(data), "features": list(FEATURES),
              "true_anomalies_for_evaluation_only": int(data.is_anomaly.sum()),
              "timestamp": "synthetic, timezone-naive; not production events"}
    csv_options = {"index": False, "float_format": "%.17g", "lineterminator": "\n"}
    data.to_csv(output / "dataset.csv", **csv_options)
    data.join(predictions).to_csv(output / "predictions.csv", **csv_options)
    metrics.to_csv(output / "metrics.csv", **csv_options)
    counts.to_csv(output / "by_kind.csv", **csv_options)
    cases = []
    for key in ("if", "ocsvm"):
        for label, mask in (("FP", ~data.is_anomaly & predictions[f"flag_{key}"]),
                            ("FN", data.is_anomaly & ~predictions[f"flag_{key}"])):
            for index in data.index[mask]:
                cases.append({"model": key, "case": label, "timestamp": str(data.loc[index, "timestamp"]),
                              "kind": data.loc[index, "kind"],
                              **{feature: float(data.loc[index, feature]) for feature in FEATURES},
                              "score": float(predictions.loc[index, f"score_{key}"]),
                              "flag": bool(predictions.loc[index, f"flag_{key}"])})
    (output / "errors.json").write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    commit = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True,
                            text=True, check=True, timeout=10).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain"], capture_output=True,
                           text=True, check=True, timeout=10).stdout.strip()
    run = {"executedUtc": datetime.now(timezone.utc).isoformat(), "sourceCommit": commit,
           "dirtyTreeAtRun": bool(dirty), "dataset": source, "protocol": {
               "fit": "StandardScaler and both models fitted on all 300 windows, including contaminated windows",
               "evaluation": "same 300 windows; descriptive in-sample comparison, no held-out test",
               "training_labels": False, "features_only": list(FEATURES), "tuning_with_labels": False,
               "academic_acceptance": "pending Q03; no teacher confirmation recorded"},
           "models": models.metadata(), "metrics": metrics.to_dict(orient="records"),
           "environment": {"python": platform.python_version(), "system": platform.system(),
                           "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}},
           "sourceHashes": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                            for name in ("dataset.py", "detectors.py", "plots.py", "run.py")}}
    make_plots(data, predictions, metrics, models, output)
    run["artifactHashes"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())
                             if p.name in ("dataset.csv", "predictions.csv", "metrics.csv", "by_kind.csv", "errors.json",
                                           "scores_timeline.png", "projection.png", "comparison.png")}
    (output / "run.json").write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    summary = """# Comparación de Isolation Forest y One-Class SVM RBF

Datos: 300 ventanas sintéticas del notebook docente, semilla 42; 53 ventanas etiquetadas como anómalas solo para evaluación. Fechas sintéticas, sin zona horaria. El dataset no proviene de PharmaGo ni de los ensayos Kubernetes.

El scaler y los dos modelos se ajustaron sobre las mismas 300 ventanas, incluidas las contaminadas, según el protocolo del práctico. Las cuatro features son requests, error_rate, latency_ms y cpu_pct. Las etiquetas kind/is_anomaly no entran al fit ni al escalado. No hubo selección de hiperparámetros con etiquetas ni cambio de umbral para mejorar F1.

## Resultados descriptivos sobre la muestra de entrenamiento

""" + table(metrics) + "\n\n## Alertas por tipo de ventana\n\n" + table(counts) + """

## Interpretación y límites

- Mayor score significa mayor anomalía en ambos modelos, pero sus escalas no son comparables entre sí y no son probabilidades. IF usa -score_samples y predict == -1; OCSVM usa -decision_function y predict == -1.
- IF fija contamination=0.10; OCSVM usa kernel RBF, nu=0.10 y gamma=scale. Nu no fuerza exactamente el mismo número de alertas que el cuantil de IF. Ninguno de esos parámetros equivale a la tasa verdadera de incidentes.
- Las filas batch y pico_carga son legítimas: sus alertas son falsos positivos. Las filas de degradación ilustran que un detector por ventana puede omitir una tendencia temporal. Una anomalía estadística no implica por sí sola un incidente operativo.
- Precision/recall/F1 y TP/FP/FN/TN son por minuto, no por incidente, y usan etiquetas sintéticas conocidas. Entrenar y evaluar sobre la misma muestra no mide generalización ni rendimiento futuro. En datos operativos se necesita un protocolo temporal acordado, calibración y validación fuera de muestra; eso no se simuló aquí.
- Q03 sigue pendiente: no se presume aceptación docente del dataset para el obligatorio. No se cambió el protocolo adjunto ni se inventó un dataset alternativo. K-sigma/MAD y el cierre completo del práctico siguen en #20.

## Artefactos

[Dataset](dataset.csv), [scores y flags por ventana](predictions.csv), [métricas](metrics.csv), [conteos por kind](by_kind.csv), [todos los FP/FN con sus vectores](errors.json), [parámetros, scaler, versiones y hashes](run.json).

![Scores en el tiempo](scores_timeline.png)

![Proyección de las decisiones](projection.png)

![Métricas y matrices de confusión](comparison.png)
"""
    (output / "RESULTS.md").write_text(summary, encoding="utf-8", newline="\n")
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".runtime/ml-results"))
    args = parser.parse_args()
    run = export(args.output)
    for row in run["metrics"]:
        print(f"{row['model']}: alertas={row['alerts']}, TP={row['tp']}, FP={row['fp']}, FN={row['fn']}, F1={row['f1']:.6f}")
    print(f"Artefactos en {args.output}; aceptación académica pendiente de Q03")


if __name__ == "__main__":
    main()
