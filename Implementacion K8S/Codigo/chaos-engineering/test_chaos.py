"""Regresiones de límites, identidad, reversión y clasificación. Sin clúster/carga."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import chaos
import probe


RUN = "a" * 32


def journal(scenario):
    return {"runId": RUN, "context": "test-local", "namespaceUid": "ns-1", "scenario": scenario,
            "pod": "pharmago-pharmacy-service-abc", "podUid": "pod-1", "serviceUid": "svc-1",
            "selectorBefore": {"app": chaos.TARGET}, "lockUid": "lock-1", "loadPodUid": "load-1"}


def local_cluster():
    cluster = Mock()
    cluster.kub.return_value = json.dumps({"clusters": [{"cluster": {"server": "https://127.0.0.1:6443"}}]})
    def get(kind, name=None):
        if kind == "namespace":
            return {"metadata": {"uid": "ns-1", "labels": {"pharmago.io/chaos-lab": "true"}}}
        if kind == "service":
            return {"metadata": {"uid": "svc-1"}, "spec": {"selector": {"app": chaos.TARGET}}}
        raise AssertionError((kind, name))
    cluster.get.side_effect = get
    cluster.optional.return_value = None
    return cluster


class LimitsTests(unittest.TestCase):
    def test_offline_dry_run_never_calls_subprocess_or_cluster(self):
        for scenario in chaos.SCENARIOS:
            with self.subTest(scenario=scenario), patch.object(sys, "argv", ["chaos.py", scenario, "--context", "test"]), \
                    patch("chaos.subprocess.run", side_effect=AssertionError("Unexpected tool call")), \
                    patch("chaos.Cluster", side_effect=AssertionError("Unexpected cluster")), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(chaos.main(), 0)
                self.assertFalse(json.loads(output.getvalue())["mutations"])

    def test_reject_unbounded_or_negative_settings(self):
        for flags in (("--duration", "0"), ("--duration", "181"), ("--megabytes", "129"),
                      ("--megabytes", "0"), ("--requests", "241"), ("--requests", "0"),
                      ("--concurrency", "5"), ("--concurrency", "0")):
            with self.subTest(flags=flags):
                args = chaos.parser().parse_args(["cpu", "--context", "test", *flags])
                with self.assertRaises(ValueError): chaos.validate_settings(args)

    def test_storage_has_lower_limit(self):
        args = chaos.parser().parse_args(["storage", "--context", "test", "--megabytes", "65"])
        with self.assertRaises(ValueError): chaos.validate_settings(args)

    def test_execute_needs_operator(self):
        args = chaos.parser().parse_args(["cpu", "--context", "test", "--execute"])
        with self.assertRaises(ValueError): chaos.validate_settings(args)

    def test_missing_context_rejected(self):
        with self.assertRaises(ValueError): chaos.validate_settings(chaos.parser().parse_args(["cpu"]))

    def test_remote_api_servers_rejected(self):
        for server in ("https://example.com:6443", "http://127.0.0.1:8001", "https://10.0.0.5", "https://127.0.0.1.evil"):
            with self.subTest(server=server), self.assertRaises(ValueError): chaos.validate_local_server(server)

    def test_finite_container_limits_required(self):
        self.assertTrue(chaos.limits_safe({"resources": {"limits": {"memory": "384Mi", "cpu": "500m"}}}))
        for limits in ({}, {"memory": "2Gi", "cpu": "500m"}, {"memory": "384Mi", "cpu": "0"},
                       {"memory": "384Mi", "cpu": "2000m"}):
            self.assertFalse(chaos.limits_safe({"resources": {"limits": limits}}))

    def test_low_host_memory_prevents_node_calls(self):
        cluster = Mock()
        with patch("chaos.host_available_bytes", return_value=1024 ** 3), self.assertRaises(RuntimeError):
            chaos.assert_capacity(cluster)
        cluster.get.assert_not_called()

    def test_node_pressure_aborts(self):
        cluster = Mock()
        cluster.get.return_value = {"items": [{"status": {"conditions": [
            {"type": "Ready", "status": "True"}, {"type": "DiskPressure", "status": "True"}]}}]}
        with patch("chaos.host_available_bytes", return_value=4 * 1024 ** 3), self.assertRaises(RuntimeError):
            chaos.assert_capacity(cluster)

    def test_unknown_namespace_not_adopted(self):
        cluster = local_cluster()
        cluster.get.side_effect = None
        cluster.get.return_value = {"metadata": {"uid": "ns-1", "labels": {}}}
        with self.assertRaises(RuntimeError): chaos.namespace_lab(cluster)


class RecoveryTests(unittest.TestCase):
    def test_no_mutation_if_namespace_replaced(self):
        cluster = local_cluster()
        with patch("chaos.namespace_lab", return_value="another-ns"), self.assertRaises(RuntimeError):
            chaos.restore_fault(cluster, journal("disconnect"))
        cluster.patch.assert_not_called()

    def test_disconnect_restores_only_own_selector(self):
        cluster = local_cluster()
        service = {"metadata": {"uid": "svc-1"}, "spec": {"selector": {
            "app": chaos.TARGET, chaos.SELECTOR_KEY: RUN}}}
        original = copy.deepcopy(service)
        def get(kind, name=None):
            if kind == "service": return service
            return {"metadata": {"uid": "ns-1", "labels": {"pharmago.io/chaos-lab": "true"}}}
        def apply(kind, name, ops):
            self.assertEqual(ops[0], {"op": "test", "path": "/metadata/uid", "value": "svc-1"})
            self.assertEqual(ops[1]["value"], RUN)
            self.assertEqual(ops[2]["op"], "remove")
            del service["spec"]["selector"][chaos.SELECTOR_KEY]
        cluster.get.side_effect, cluster.patch.side_effect = get, apply
        chaos.restore_fault(cluster, journal("disconnect"))
        self.assertEqual(service["spec"]["selector"], {"app": chaos.TARGET})
        self.assertEqual(original["spec"]["selector"][chaos.SELECTOR_KEY], RUN)

    def test_foreign_selector_not_removed(self):
        cluster = local_cluster()
        with patch("chaos.namespace_lab", return_value="ns-1"):
            cluster.get.side_effect = None
            cluster.get.return_value = {"metadata": {"uid": "svc-1"}, "spec": {"selector": {chaos.SELECTOR_KEY: "foreign"}}}
            with self.assertRaises(RuntimeError): chaos.restore_fault(cluster, journal("disconnect"))
        cluster.patch.assert_not_called()

    def test_service_replacement_never_patched(self):
        cluster = local_cluster()
        with patch("chaos.namespace_lab", return_value="ns-1"):
            cluster.get.side_effect = None
            cluster.get.return_value = {"metadata": {"uid": "new-service"}}
            with self.assertRaises(RuntimeError): chaos.restore_fault(cluster, journal("disconnect"))
        cluster.patch.assert_not_called()

    def test_cleanup_never_executes_in_replacement_pod(self):
        cluster = local_cluster()
        cluster.optional.return_value = {"metadata": {"uid": "new-pod"}}
        chaos.restore_fault(cluster, journal("cpu"))
        cluster.exec_script.assert_not_called()

    def test_agent_cleanup_is_verified(self):
        cluster = local_cluster()
        cluster.optional.return_value = {"metadata": {"uid": "pod-1"}}
        cluster.exec_script.side_effect = ['{"cleaned":true}', '{"active":false}']
        chaos.restore_fault(cluster, journal("ram"))
        self.assertEqual(cluster.exec_script.call_count, 2)

    def test_active_agent_after_cleanup_is_failure(self):
        cluster = local_cluster()
        cluster.optional.return_value = {"metadata": {"uid": "pod-1"}}
        cluster.exec_script.side_effect = ['{"cleaned":true}', '{"active":true}']
        with self.assertRaises(RuntimeError): chaos.restore_fault(cluster, journal("storage"))

    def test_foreign_resource_not_deleted(self):
        cluster = local_cluster()
        cluster.optional.return_value = {"metadata": {"uid": "policy-1", "labels": {chaos.OWNER: "foreign"}}}
        with self.assertRaises(RuntimeError): chaos.owned_delete(cluster, "networkpolicy", "test-policy", RUN)
        self.assertEqual(cluster.kub.call_count, 0)

    def test_delete_uses_uid_and_resource_version_preconditions(self):
        cluster = local_cluster()
        cluster.optional.side_effect = [{"metadata": {"uid": "policy-1", "resourceVersion": "42", "labels": {chaos.OWNER: RUN}}}, None]
        chaos.owned_delete(cluster, "networkpolicy", "test-policy", RUN)
        args, kwargs = cluster.kub.call_args
        self.assertIn("--raw", args)
        self.assertEqual(json.loads(kwargs["stdin"])["preconditions"], {"uid": "policy-1", "resourceVersion": "42"})

    def test_request_recovery_does_not_change_application(self):
        cluster = local_cluster()
        chaos.restore_fault(cluster, journal("requests"))
        cluster.patch.assert_not_called()
        cluster.create.assert_not_called()
        cluster.exec_script.assert_not_called()

    def test_request_recovery_stops_only_original_load_pod(self):
        cluster = local_cluster()
        cluster.optional.return_value = {"metadata": {"uid": "load-1"}}
        cluster.rpc.return_value = {"stopped": True}
        chaos.restore_fault(cluster, journal("requests"))
        cluster.rpc.assert_called_once_with("pharmago-chaos-load", {"action": "stop", "runId": RUN})

    def test_request_recovery_does_not_touch_replacement_client(self):
        cluster = local_cluster()
        cluster.optional.return_value = {"metadata": {"uid": "another-load-pod"}}
        chaos.restore_fault(cluster, journal("requests"))
        cluster.rpc.assert_not_called()


class EvidenceTests(unittest.TestCase):
    def trial(self, directory, scenario):
        args = chaos.parser().parse_args([scenario, "--context", "test", "--output", directory])
        trial = chaos.Trial(args)
        trial.journal = journal(scenario)
        trial.report.update(events=[{"event": "inject-requested", "timeUtc": "2026-11-12T10:00:00Z"}],
                            faultRestoredUtc="2026-11-12T10:01:00Z")
        return trial

    def test_non_enforced_network_policy_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.trial(directory, "network")
            trial.report["samples"] = [{"path": "/api/drug", "http": 200, "valid": True,
                                        "receivedUtc": "2026-11-12T10:00:20Z"}]
            with self.assertRaises(RuntimeError): trial.check_effect()

    def test_burst_without_rate_limit_effect_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.trial(directory, "requests")
            trial.report["injectionResult"] = [{"http": 200}]
            with self.assertRaises(RuntimeError): trial.check_effect()

    def test_storage_must_reach_budgeted_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.trial(directory, "storage")
            trial.report["injectionStates"] = [{"active": True, "bytes": 100}]
            with self.assertRaises(RuntimeError): trial.check_effect()

    def test_process_running_without_cpu_metric_effect_is_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.trial(directory, "cpu")
            trial.report.update(injectionStates=[{"active": True}], observations=[{
                "timeUtc": "2026-11-12T09:59:59Z", "telemetry": {"cpu": {"series": []}}}])
            with self.assertRaises(RuntimeError): trial.check_effect()

    def test_cli_error_does_not_leak_exec_output_or_stdin(self):
        cluster = chaos.Cluster("test")
        result = subprocess.CompletedProcess([], 1, "private-response", "private-token")
        with patch("chaos.subprocess.run", return_value=result), self.assertRaises(RuntimeError) as error:
            cluster.kub("exec", "client", stdin="private-password")
        self.assertNotIn("private", str(error.exception))

    def test_windows_stdin_preserves_linux_lf_bytes_and_decodes_utf8_output(self):
        cluster = chaos.Cluster("test")
        result = subprocess.CompletedProcess([], 0, 'respuestá\n'.encode("utf-8"), b"")
        with patch("chaos.subprocess.run", return_value=result) as run:
            self.assertEqual(cluster.kub("exec", "client", stdin="set -eu\nprintf ok\n"), "respuestá\n")
        self.assertEqual(run.call_args.kwargs["input"], b"set -eu\nprintf ok\n")
        self.assertNotIn("text", run.call_args.kwargs)

    def test_burst_limits_checked_before_http(self):
        with patch("probe.request", side_effect=AssertionError("Unexpected HTTP")), self.assertRaises(ValueError):
            probe.burst({"count": 241, "concurrency": 4, "duration": 60})

    def test_fingerprint_ignores_list_order(self):
        self.assertEqual(probe.fingerprint([{"id": 2}, {"id": 1}]), probe.fingerprint([{"id": 1}, {"id": 2}]))

    def test_failure_after_journal_creation_still_restores_and_releases_own_lock(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            trial = self.trial(directory, "disconnect")
            trial.preflight = Mock(side_effect=RuntimeError("Fallo de precheck posterior al journal"))
            with patch("chaos.restore_fault") as restore, patch("chaos.owned_delete") as release:
                self.assertFalse(trial.run())
            restore.assert_called_once_with(trial.cluster, trial.journal)
            release.assert_called_once_with(trial.cluster, "configmap", chaos.LOCK, trial.run_id, "lock-1")
            self.assertTrue(trial.journal["finished"])
            self.assertEqual(trial.report["status"], "FAIL")

    def test_cleanup_failure_cannot_be_reported_as_verified(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            trial = self.trial(directory, "cpu")
            trial.preflight = Mock(side_effect=RuntimeError("Interrumpido"))
            with patch("chaos.restore_fault", side_effect=RuntimeError("Sin acceso al cluster")):
                self.assertFalse(trial.run())
            self.assertEqual(trial.report["cleanup"], "MANUAL_RECOVERY_REQUIRED")
            self.assertNotIn("finished", trial.journal)

    def test_probe_never_emits_login_token_or_password(self):
        with patch("probe.request", return_value=({"http": 200}, {"token": "private-token", "userName": "admin"})):
            result = probe.sample({"login": True, "username": "admin", "password": "private-password"})
        self.assertTrue(result[-1]["valid"])
        self.assertNotIn("private", json.dumps(result))

    def test_cancel_before_remote_start_prevents_late_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            with patch("probe.Path", side_effect=lambda p: tmp if p == "/tmp" else Path(p)), \
                    patch.dict(os.environ, {"PHARMAGO_CHAOS_RUNID": RUN}), \
                    patch("probe.request", side_effect=AssertionError("No HTTP after cancel")):
                self.assertTrue(probe.stop_burst({"runId": RUN})["stopped"])
                self.assertEqual(probe.burst({"runId": RUN, "count": 240, "concurrency": 4,
                                              "duration": 60, "untilEpoch": time.time() + 60}), [])
                self.assertTrue(probe.stop_burst({"runId": RUN, "clear": True})["cleared"])
            self.assertEqual(list(tmp.iterdir()), [])

    def test_expired_absolute_deadline_prevents_remote_start(self):
        with patch.dict(os.environ, {"PHARMAGO_CHAOS_RUNID": RUN}), \
                patch("probe.request", side_effect=AssertionError("No HTTP after deadline")):
            self.assertEqual(probe.burst({"runId": RUN, "count": 100, "concurrency": 4,
                                          "duration": 60, "untilEpoch": time.time() - 1}), [])

    def test_foreign_cancel_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            marker = tmp / ("pharmago-chaos-" + RUN + ".cancel")
            marker.write_text("foreign")
            with patch("probe.Path", side_effect=lambda p: tmp if p == "/tmp" else Path(p)), self.assertRaises(ValueError):
                probe.stop_burst({"runId": RUN})
            self.assertEqual(marker.read_text(), "foreign")

    def aborted_remote_trial(self, directory, scenario, remote_error, expired=False, watchdog_error=None):
        trial = self.trial(directory, scenario)
        trial.journal["faultDeadlineEpoch"] = time.time() + (-60 if expired else 60)
        (trial.directory / "watchdog-ready.json").write_text("{}")
        trial.preflight = Mock()
        trial.inject = Mock(return_value=lambda: None)
        future = Mock()
        future.result.side_effect = remote_error
        pool, watch = Mock(), Mock()
        pool.submit.return_value = future
        watch.poll.return_value = None
        watch.wait.side_effect = watchdog_error
        with patch("chaos.subprocess.Popen", return_value=watch), \
                patch("chaos.ThreadPoolExecutor", return_value=pool), \
                patch("chaos.assert_capacity", side_effect=RuntimeError("Abort after dispatch")), \
                patch("chaos.restore_fault") as restore, patch("chaos.clear_remote_control") as clear, \
                patch("chaos.owned_delete") as release, contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(trial.run())
        return trial, future, restore, clear, release

    def test_abort_keeps_cancel_lock_and_watchdog_for_every_uncertain_remote_rpc(self):
        for scenario in ("requests", "cpu", "ram", "storage"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                trial, future, restore, clear, release = self.aborted_remote_trial(directory, scenario, TimeoutError())
                future.result.assert_called_once_with(timeout=30)
                restore.assert_called_once()
                clear.assert_not_called()
                release.assert_not_called()
                self.assertFalse(trial.journal.get("finished", False))
                self.assertEqual(trial.report["cleanup"], "MANUAL_RECOVERY_REQUIRED")

    def test_expired_absolute_deadline_allows_cleanup_of_uncertain_resource_rpc(self):
        for scenario in ("requests", "cpu", "ram", "storage"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                trial, future, restore, clear, release = self.aborted_remote_trial(directory, scenario, TimeoutError(), expired=True)
                self.assertEqual(restore.call_count, 2)
                clear.assert_called_once_with(trial.cluster, trial.journal)
                release.assert_called_once()
                self.assertTrue(trial.journal["finished"])
                self.assertEqual(trial.report["cleanup"], "verified")

    def test_settled_resource_rpc_is_restored_again_before_control_is_removed(self):
        for scenario in ("cpu", "ram", "storage"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                trial, future, restore, clear, release = self.aborted_remote_trial(directory, scenario, None)
                self.assertEqual(restore.call_count, 2)
                clear.assert_called_once()
                release.assert_called_once()
                self.assertTrue(trial.journal["finished"])

    def test_resource_rpc_receives_absolute_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            trial = self.trial(directory, "cpu")
            trial.journal["faultDeadlineEpoch"] = 1794513723.8
            trial.cluster.get = Mock(return_value={"metadata": {"uid": "pod-1"}})
            trial.cluster.exec_script = Mock()
            trial.inject()()
            arguments = trial.cluster.exec_script.call_args.args[2]
            self.assertEqual(arguments[-1], "1794513723")

    def test_watchdog_must_stop_before_controls_and_lab_lock_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            trial, _, _, clear, release = self.aborted_remote_trial(directory, "cpu", None,
                watchdog_error=subprocess.TimeoutExpired("watchdog", 10))
            clear.assert_not_called()
            release.assert_not_called()
            self.assertFalse(trial.journal.get("finished", False))
            self.assertEqual(trial.report["cleanup"], "MANUAL_RECOVERY_REQUIRED")


if __name__ == "__main__":
    unittest.main()
