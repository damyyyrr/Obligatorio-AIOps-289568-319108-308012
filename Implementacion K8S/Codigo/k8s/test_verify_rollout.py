"""Evidence must count every failed request, including quota responses."""
import unittest

from verify_rollout import classify, fingerprint, summarize


class EvidenceTests(unittest.TestCase):
    def test_errors_are_never_successes(self):
        self.assertEqual("httpError", classify(429, 0, True))
        self.assertEqual("httpError", classify(502, 0, True))
        self.assertEqual("timeout", classify(0, 28, False))
        self.assertEqual("transportError", classify(0, 7, False))
        self.assertEqual("validationError", classify(200, 0, False))
        self.assertEqual("success", classify(200, 0, True))

    def test_summary_keeps_all_attempts_and_latency(self):
        samples = [{"http": code, "outcome": classify(code, error, valid), "latencyMs": ms}
                   for code, error, valid, ms in [(200, 0, True, 10), (429, 0, False, 20),
                                                  (0, 28, False, 2000), (200, 0, False, 30)]]
        result = summarize(samples)
        self.assertEqual(4, result["sent"])
        self.assertEqual(1, result["success"])
        self.assertEqual(1, result["httpError"])
        self.assertEqual(1, result["timeout"])
        self.assertEqual(1, result["validationError"])
        self.assertEqual(2000, result["latencyMs"]["p95"])

    def test_business_validation_ignores_only_list_order(self):
        self.assertEqual(fingerprint([{"id": 1}, {"id": 2}]), fingerprint([{"id": 2}, {"id": 1}]))
        self.assertNotEqual(fingerprint([{"id": 1, "stock": 4}]), fingerprint([{"id": 1, "stock": 3}]))
