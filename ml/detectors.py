"""IF y OCSVM del práctico: cuatro features, escalado único, sin etiquetas al fit."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM
from threadpoolctl import threadpool_limits

from dataset import FEATURES, SEED

MODEL_COLUMNS = {"Isolation Forest": "if", "One-Class SVM RBF": "ocsvm"}


def feature_frame(data):
    missing = set(FEATURES) - set(data.columns)
    if missing:
        raise ValueError("Faltan features: " + ", ".join(sorted(missing)))
    if not data.index.is_unique or data.empty:
        raise ValueError("Se requiere una muestra no vacía con índice único")
    values = data.loc[:, list(FEATURES)].apply(pd.to_numeric, errors="raise").astype(float)
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError("Features con NaN/inf: corregir el insumo sin descartar filas silenciosamente")
    return values


@dataclass
class FittedDetectors:
    scaler: StandardScaler
    forest: IsolationForest
    ocsvm: OneClassSVM

    def score(self, data):
        values = self.scaler.transform(feature_frame(data))
        with threadpool_limits(limits=1):
            return pd.DataFrame({
                "score_if": -self.forest.score_samples(values),
                "flag_if": self.forest.predict(values) == -1,
                "score_ocsvm": -self.ocsvm.decision_function(values),
                "flag_ocsvm": self.ocsvm.predict(values) == -1,
            }, index=data.index)

    def metadata(self):
        return {
            "features": list(FEATURES),
            "scaler": {"class": "StandardScaler", "fit_rows": int(self.scaler.n_samples_seen_),
                       "mean": self.scaler.mean_.tolist(), "scale": self.scaler.scale_.tolist(),
                       "variance": self.scaler.var_.tolist()},
            "isolation_forest": {"parameters": self.forest.get_params(deep=False),
                                 "offset": float(self.forest.offset_),
                                 "anomaly_score_threshold": float(-self.forest.offset_),
                                 "score": "-score_samples; larger means more anomalous",
                                 "flag": "predict(X) == -1"},
            "one_class_svm": {"parameters": self.ocsvm.get_params(deep=False),
                              "support_vectors": int(len(self.ocsvm.support_)),
                              "fit_status": int(self.ocsvm.fit_status_),
                              "anomaly_score_threshold": 0.0,
                              "score": "-decision_function; larger means more anomalous",
                              "flag": "predict(X) == -1"},
        }


def fit_detectors(data):
    features = feature_frame(data)
    if len(features) < 2:
        raise ValueError("Se requieren al menos dos ventanas")
    scaler = StandardScaler()
    values = scaler.fit_transform(features)
    forest = IsolationForest(n_estimators=300, max_samples=min(256, len(features)),
                             contamination=0.10, random_state=SEED, n_jobs=1)
    ocsvm = OneClassSVM(kernel="rbf", nu=0.10, gamma="scale")
    with threadpool_limits(limits=1):
        forest.fit(values)
        ocsvm.fit(values)
    if ocsvm.fit_status_ != 0:
        raise RuntimeError("One-Class SVM no convergió")
    return FittedDetectors(scaler, forest, ocsvm)


def evaluate(data, predictions):
    if not data.index.equals(predictions.index):
        raise ValueError("Predicciones desalineadas respecto de las ventanas")
    if "is_anomaly" not in data:
        return pd.DataFrame()  # No inventar métricas sin verdad de referencia.
    if data["is_anomaly"].isna().any() or not data["is_anomaly"].isin([True, False, 0, 1]).all():
        raise ValueError("Etiquetas de evaluación inválidas")
    truth = data["is_anomaly"].to_numpy(dtype=bool)
    rows = []
    for name, key in MODEL_COLUMNS.items():
        if predictions[f"flag_{key}"].isna().any() or not predictions[f"flag_{key}"].isin([True, False, 0, 1]).all():
            raise ValueError("Flags inválidas")
        predicted = predictions[f"flag_{key}"].to_numpy(dtype=bool)
        precision, recall, f1, _ = precision_recall_fscore_support(truth, predicted, average="binary", zero_division=0)
        tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[False, True]).ravel()
        rows.append({"model": name, "windows": len(data), "true_anomalies": int(truth.sum()),
                     "alerts": int(predicted.sum()), "tp": int(tp), "fp": int(fp),
                     "fn": int(fn), "tn": int(tn), "precision": float(precision),
                     "recall": float(recall), "f1": float(f1)})
    return pd.DataFrame(rows)


def counts_by_kind(data, predictions):
    if not data.index.equals(predictions.index):
        raise ValueError("Predicciones desalineadas")
    if "kind" not in data:
        return pd.DataFrame()
    combined = data.loc[:, ["kind"]].join(predictions)
    group = combined.groupby("kind", sort=True)
    counts = group.agg(windows=("kind", "size"), if_alerts=("flag_if", "sum"),
                       ocsvm_alerts=("flag_ocsvm", "sum"),
                       median_score_if=("score_if", "median"),
                       median_score_ocsvm=("score_ocsvm", "median"))
    if "is_anomaly" in data:
        counts["true_anomalies"] = data.groupby("kind")["is_anomaly"].sum().astype(int)
    return counts.reset_index()
