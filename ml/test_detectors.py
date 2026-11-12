"""Contratos del protocolo y evaluación, sin infraestructura ni dataset externo."""
import contextlib
import io
import json
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from dataset import FEATURES, generate_dataset
from detectors import counts_by_kind, evaluate, feature_frame, fit_detectors


class DatasetTests(unittest.TestCase):
    def test_every_value_matches_original_teacher_generation_cell(self):
        notebook = json.loads(Path(__file__).with_name("practico_detectores_aiops.ipynb").read_text(encoding="utf-8"))
        namespace = {"np": np, "pd": pd, "rng": np.random.default_rng(42), "display": lambda *_: None}
        # Solo la celda generadora revisada; no ejecuta el notebook ni sus TODO.
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile("".join(notebook["cells"][4]["source"]), "teacher-dataset-cell", "exec"), namespace)
        pd.testing.assert_frame_equal(generate_dataset(), namespace["data"], check_exact=True)

    def test_expected_protocol_and_legitimate_traps(self):
        data = generate_dataset()
        self.assertEqual(len(data), 300)
        self.assertEqual(int(data.is_anomaly.sum()), 53)
        self.assertEqual(data.timestamp.diff().dropna().unique().tolist(), [pd.Timedelta(minutes=1)])
        self.assertFalse(data.loc[data.kind.isin(["batch", "pico_carga"]), "is_anomaly"].any())
        self.assertEqual(int(data.kind.eq("batch").sum()), 20)

    def test_seed_is_local_and_reproducible(self):
        first = generate_dataset()
        np.random.default_rng(1).normal(size=500)
        pd.testing.assert_frame_equal(first, generate_dataset(), check_exact=True)


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generate_dataset()
        cls.models = fit_detectors(cls.data)
        cls.predictions = cls.models.score(cls.data)

    def test_labels_and_extra_numeric_columns_cannot_change_fit(self):
        poisoned = self.data.copy()
        poisoned["is_anomaly"] = np.arange(len(poisoned)) * 10 ** 9
        poisoned["kind"] = np.arange(len(poisoned)) * -10 ** 9
        poisoned["label_leak"] = np.where(self.data.is_anomaly, 10 ** 12, -10 ** 12)
        other = fit_detectors(poisoned)
        pd.testing.assert_frame_equal(self.predictions, other.score(poisoned), check_exact=True)
        np.testing.assert_array_equal(self.models.scaler.mean_, other.scaler.mean_)

    def test_repeated_fit_produces_identical_scores_and_flags(self):
        pd.testing.assert_frame_equal(self.predictions, fit_detectors(self.data).score(self.data), check_exact=True)

    def test_scaler_uses_all_rows_and_exactly_four_features(self):
        self.assertEqual(int(self.models.scaler.n_samples_seen_), 300)
        self.assertEqual(self.models.forest.n_features_in_, 4)
        self.assertEqual(self.models.ocsvm.n_features_in_, 4)
        np.testing.assert_allclose(self.models.scaler.mean_, self.data[list(FEATURES)].mean(), rtol=1e-14)
        scaled = self.models.scaler.transform(feature_frame(self.data))
        np.testing.assert_allclose(scaled.mean(axis=0), 0, atol=1e-14)
        np.testing.assert_allclose(scaled.var(axis=0), 1, atol=1e-14)

    def test_teacher_hyperparameters_and_convergence(self):
        forest, svm = self.models.forest, self.models.ocsvm
        self.assertEqual((forest.n_estimators, forest.max_samples, forest.contamination, forest.random_state),
                         (300, 256, 0.10, 42))
        self.assertEqual((svm.kernel, svm.nu, svm.gamma, svm.fit_status_), ("rbf", 0.10, "scale", 0))

    def test_score_direction_and_detector_thresholds(self):
        for key, threshold in (("if", -self.models.forest.offset_), ("ocsvm", 0.0)):
            scores, flags = self.predictions[f"score_{key}"], self.predictions[f"flag_{key}"]
            self.assertTrue(np.isfinite(scores).all())
            self.assertTrue((scores[flags] > threshold).all())
            self.assertTrue((scores[~flags] <= threshold).all())

    def test_scoring_subset_preserves_index_and_does_not_refit(self):
        subset = self.data.loc[[8, 41, 200], list(FEATURES)]
        pd.testing.assert_frame_equal(self.models.score(subset), self.predictions.loc[subset.index])
        self.assertEqual(int(self.models.scaler.n_samples_seen_), 300)

    def test_feature_order_is_explicit(self):
        reverse = self.data.loc[:, list(reversed(self.data.columns))]
        pd.testing.assert_frame_equal(self.predictions, self.models.score(reverse), check_exact=True)

    def test_missing_features_rejected(self):
        with self.assertRaises(ValueError): fit_detectors(self.data.drop(columns="cpu_pct"))

    def test_invalid_feature_values_not_silently_imputed_or_removed(self):
        for value in (np.nan, np.inf, -np.inf, "invalid"):
            data = self.data.astype({"cpu_pct": object})
            data.loc[0, "cpu_pct"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): fit_detectors(data)

    def test_duplicate_or_empty_index_rejected(self):
        duplicate = self.data.copy()
        duplicate.index = [0] * len(duplicate)
        for data in (duplicate, self.data.iloc[:0]):
            with self.assertRaises(ValueError): fit_detectors(data)

    def test_fit_does_not_mutate_input(self):
        data = self.data.copy(deep=True)
        fit_detectors(data)
        pd.testing.assert_frame_equal(data, self.data, check_exact=True)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({"is_anomaly": [True, True, False, False]})
        self.predictions = pd.DataFrame({"flag_if": [True, False, True, False],
                                         "flag_ocsvm": [True, True, False, False]})

    def test_known_confusion_matrix_counts_and_metrics(self):
        result = evaluate(self.data, self.predictions)
        row = result.iloc[0]
        self.assertEqual((row.tp, row.fp, row.fn, row.tn), (1, 1, 1, 1))
        self.assertEqual((row.precision, row.recall, row.f1), (0.5, 0.5, 0.5))
        self.assertEqual(result.iloc[1].f1, 1.0)

    def test_no_labels_does_not_fabricate_metrics(self):
        self.assertTrue(evaluate(pd.DataFrame(index=range(4)), self.predictions).empty)

    def test_misaligned_predictions_rejected(self):
        with self.assertRaises(ValueError): evaluate(self.data, self.predictions.iloc[::-1])

    def test_invalid_or_missing_labels_rejected(self):
        for value in (None, "true", -1, 2):
            data = self.data.astype(object)
            data.loc[0, "is_anomaly"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): evaluate(data, self.predictions)

    def test_invalid_flags_rejected(self):
        predictions = self.predictions.astype(object)
        predictions.loc[0, "flag_if"] = None
        with self.assertRaises(ValueError): evaluate(self.data, predictions)

    def test_single_class_without_alerts_is_well_defined(self):
        result = evaluate(pd.DataFrame({"is_anomaly": [False] * 4}),
                          pd.DataFrame({"flag_if": [False] * 4, "flag_ocsvm": [False] * 4}))
        self.assertTrue(result.f1.eq(0).all())
        self.assertTrue(result.tn.eq(4).all())


if __name__ == "__main__":
    unittest.main()
