"""Regression tests: command failures, volume identity and deployment ordering."""
import argparse
import json
import contextlib
import io
import hashlib
import tarfile
import unittest
from unittest.mock import patch

import manage


CREDENTIALS = {"sqlPassword": "test-sql-password", "grafanaAdminPassword": "test-grafana-password"}


def node(role="all", uid="node-uid"):
    return {"metadata": {"name": "custom-node", "uid": uid, "labels": {"node-type": role, manage.HOSTNAME_LABEL: uid}},
            "spec": {}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}}


class FakeCluster(manage.Cluster):
    def __init__(self, fail=None, changed=False):
        super().__init__("test-cluster")
        self.calls = []
        self.fail = fail
        self.changed = changed
        self.snapshots = 0

    def preflight(self, workloads=True):
        return node()

    def volumes(self):
        self.snapshots += 1
        return [{"name": "sql-pv", "uid": "changed" if self.changed and self.snapshots == 2 else "pv-1",
                 "claimUid": "pvc-1", "storageNodeUid": "node-uid",
                 "hostPath": "/mnt/data/sql", "nodeAffinity": {"required": {"nodeSelectorTerms": []}}}]

    def plan_secrets(self, desired, sql_volume_exists):
        return []

    def call(self, *args, stdin=None):
        doc = json.loads(stdin) if stdin else None
        self.calls.append((args, doc))
        if self.fail and ((doc and doc["metadata"]["name"] == self.fail) or self.fail in args):
            raise RuntimeError("injected failure")
        return '{"items": []}'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_manifest_inventory_and_references(self):
        docs = manage.resources("test-123")
        services = {d["metadata"]["name"] for d in docs if d["kind"] == "Service"}
        self.assertTrue({"pharmago-db", "pharmago-users-service", "pharmago-pharmacy-service", "otlp-collector"} <= services)
        cms = {d["metadata"]["name"] for d in docs if d["kind"] == "ConfigMap"}
        claims = {d["metadata"]["name"] for d in docs if d["kind"] == "PersistentVolumeClaim"}
        accounts = {d["metadata"]["name"] for d in docs if d["kind"] == "ServiceAccount"} | {"default"}
        count = 0
        for d in docs:
            if d["kind"] == "PersistentVolume":
                self.assertEqual("Retain", d["spec"]["persistentVolumeReclaimPolicy"])
            if d["kind"] not in ("Deployment", "DaemonSet"):
                continue
            spec = d["spec"]["template"]["spec"]
            self.assertIn(spec.get("serviceAccountName", "default"), accounts)
            for v in spec.get("volumes", []):
                if "configMap" in v:
                    self.assertIn(v["configMap"]["name"], cms)
                if "persistentVolumeClaim" in v:
                    self.assertIn(v["persistentVolumeClaim"]["claimName"], claims)
            for c in spec.get("containers", []) + spec.get("initContainers", []):
                self.assertNotIn("latest", c["image"])
                if c["image"].split(":")[0] in manage.APP_IMAGES:
                    count += 1
                    self.assertTrue(c["image"].endswith(":test-123"))
        self.assertEqual(4, count)
        self.assertIn("fluent-bit", accounts)

    def test_repeat_apply_preserves_pv_and_never_deletes(self):
        cluster = FakeCluster()
        for _ in range(2):
            result = manage.deploy(cluster, manage.resources("test"), 42, CREDENTIALS)
            self.assertEqual(result["volumesBefore"], result["volumesAfter"])
        self.assertFalse(any("delete" in args or "label" in args for args, _ in cluster.calls))
        applied = [doc["metadata"]["name"] for _, doc in cluster.calls if doc and doc["kind"] == "DaemonSet"]
        self.assertEqual(2, applied.count("fluent-bit"))

    def test_stops_on_early_apply_error(self):
        cluster = FakeCluster(fail="prometheus-config")
        with self.assertRaises(RuntimeError):
            manage.deploy(cluster, manage.resources("test"), 42, CREDENTIALS)
        self.assertFalse(any(d and d["kind"] == "Deployment" for _, d in cluster.calls))

    def test_sql_timeout_prevents_downstream_workloads(self):
        cluster = FakeCluster(fail="deployment/pharmago-db")
        with self.assertRaises(RuntimeError):
            manage.deploy(cluster, manage.resources("test"), 42, CREDENTIALS)
        self.assertFalse(any(d and d["kind"] == "Deployment" and d["metadata"]["name"] != "pharmago-db" for _, d in cluster.calls))

    def test_changed_volume_identity_fails(self):
        with self.assertRaisesRegex(RuntimeError, "identity changed"):
            manage.deploy(FakeCluster(changed=True), manage.resources("test"), 42, CREDENTIALS)

    def test_context_mismatch_blocks_reads_and_writes(self):
        with patch.object(manage, "run", return_value="other-cluster") as runner:
            with self.assertRaisesRegex(RuntimeError, "differs"):
                manage.Cluster("test-cluster").preflight()
            self.assertEqual(1, runner.call_count)

    def test_missing_node_roles_blocks_apply(self):
        cluster = manage.Cluster("test-cluster")
        with patch.object(manage, "run", return_value="test-cluster"), patch.object(cluster, "call", return_value=json.dumps({"items": [node("ops")]})):
            with self.assertRaisesRegex(RuntimeError, "Label schedulable Ready nodes"):
                cluster.preflight()

    def test_all_role_cannot_bypass_separated_topology(self):
        local = node()
        with self.assertRaisesRegex(RuntimeError, "only supported with"):
            manage.validate_topology([local], [local], "separated")
        self.assertIs(local, manage.validate_topology([local], [local], "single-node"))
        with self.assertRaisesRegex(RuntimeError, "one-node cluster"):
            manage.validate_topology([local, node("unused", "second")], [local], "single-node")

    def test_different_storage_node_blocks_before_mutation(self):
        cluster = FakeCluster()
        with patch.object(cluster, "volumes", return_value=[
            {"name": "sql-pv", "uid": "pv-1", "claimUid": "pvc-1", "storageNodeUid": "other-node"}
        ]):
            with self.assertRaisesRegex(RuntimeError, "belongs to another storage node"):
                manage.deploy(cluster, manage.resources("test"), 42, CREDENTIALS)
        self.assertEqual([], cluster.calls)

    def test_legacy_secret_keeps_password_and_removes_last_applied_data(self):
        cluster = manage.Cluster("test-cluster")
        desired = manage.secret_resources(CREDENTIALS)[0]
        old = {**desired, "metadata": {**desired["metadata"], "resourceVersion": "7",
               "annotations": {"kubectl.kubernetes.io/last-applied-configuration": "old-secret",
                               "other": "keep"}},
               "data": {"SA_PASSWORD": desired["data"]["SA_PASSWORD"]}}
        with patch.object(cluster, "call", return_value=json.dumps(old)):
            (action, updated), = cluster.plan_secrets([desired], sql_volume_exists=True)
        self.assertEqual("replace", action)
        self.assertEqual(desired["data"], updated["data"])
        self.assertEqual("7", updated["metadata"]["resourceVersion"])
        self.assertEqual({"other": "keep"}, updated["metadata"]["annotations"])

    def test_different_sql_password_is_rejected_before_apply(self):
        cluster = manage.Cluster("test-cluster")
        (desired, _) = manage.secret_resources(CREDENTIALS)
        with patch.object(cluster, "call", return_value='{"data": {"SA_PASSWORD": "other"}}'):
            with self.assertRaisesRegex(RuntimeError, "Local password differs"):
                cluster.plan_secrets([desired], sql_volume_exists=True)

    def test_released_volume_not_automatically_recreated(self):
        cluster = manage.Cluster("test-cluster")
        with patch.object(cluster, "call", return_value=json.dumps({"metadata": {}, "status": {"phase": "Released"}})) as call:
            with self.assertRaisesRegex(RuntimeError, "manual recovery"):
                cluster.volumes()
            self.assertEqual(1, call.call_count)

    def test_wrong_volume_owner_blocks_apply(self):
        cluster = manage.Cluster("test-cluster")
        pv = {"metadata": {"uid": "x"}, "spec": {"claimRef": {"namespace": "other", "name": "sql-pvc"}}}
        with patch.object(cluster, "call", return_value=json.dumps(pv)):
            with self.assertRaisesRegex(RuntimeError, "another claim"):
                cluster.volumes()

    def test_external_command_failure_propagates_without_stdin(self):
        with patch.object(manage.subprocess, "run", return_value=argparse.Namespace(returncode=1, stderr="unavailable", stdout="")):
            with self.assertRaisesRegex(RuntimeError, "unavailable") as error:
                manage.run("kubectl", "apply", stdin="secret-data")
            self.assertNotIn("secret-data", str(error.exception))

    def test_build_profile_mismatch_blocks_docker(self):
        cluster = FakeCluster()
        replies = ["Configured", json.dumps({"items": [node(uid="wrong-cluster") ]})]
        with patch.object(manage, "run", side_effect=replies) as runner:
            with self.assertRaisesRegex(RuntimeError, "profile nodes differ"):
                manage.build(cluster, "test", "profile")
            self.assertFalse(any(c.args[0] == "docker" for c in runner.call_args_list))

    def test_invalid_tags(self):
        for tag in ("latest", "../../bad", "", "tag with spaces"):
            with self.assertRaises(argparse.ArgumentTypeError):
                manage.tag_value(tag)

    def test_build_checks_loaded_image_on_each_node(self):
        cluster = FakeCluster()
        nodes = [node()]
        cluster.call = lambda *a, **k: json.dumps({"items": nodes})
        commands = []
        def command(*args, **kwargs):
            commands.append(args)
            if args[0] == "minikube":
                if "status" in args:
                    return "Configured"
                if "kubectl" in args:
                    return json.dumps({"items": nodes})
                if "ssh" in args:
                    return json.dumps({"images": [{"id": "sha256:test", "repoTags": ["docker.io/library/pharmago-ui:test"]}]})
            if args[:3] == ("docker", "image", "ls"):
                return ""
            if args[:3] == ("docker", "image", "inspect"):
                return "sha256:test"
            return ""
        with patch.object(manage, "run", side_effect=command), patch.object(manage, "image_config_digest", return_value="sha256:test"):
            report = manage.build(cluster, "test", "profile", ui_only=True)
        self.assertEqual("sha256:test", report["images"][0]["id"])
        self.assertTrue(any("--node" in c for c in commands))
        self.assertTrue(any(c[0:2] == ("docker", "build") and str(c[-1]).endswith("Frontend") for c in commands))

    def test_cri_digest_uses_config_instead_of_oci_index(self):
        config = b'{"architecture":"amd64","rootfs":{"type":"layers","diff_ids":[]}}'
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            for name, data in (("blobs/sha256/config", config), ("manifest.json", b'[{"Config":"blobs/sha256/config","RepoTags":["app:test"],"Layers":[]}]')):
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        stream.seek(0)
        self.assertEqual("sha256:" + hashlib.sha256(config).hexdigest(), manage.archive_config_digest(stream))

    def test_cli_missing_context_exits_before_commands(self):
        with patch.object(manage, "run") as command, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                manage.main(["apply", "--image-tag", "test"])
            command.assert_not_called()

    def test_multiple_hostpath_nodes_block_deployment(self):
        cluster = manage.Cluster("test-cluster")
        with patch.object(manage, "run", return_value="test-cluster"), patch.object(cluster, "call", return_value=json.dumps({"items": [node(), node(uid="second")]})):
            with self.assertRaisesRegex(RuntimeError, "exactly one"):
                cluster.preflight()

    def test_elasticsearch_timeout_prevents_application_deployment(self):
        cluster = FakeCluster(fail="deployment/elasticsearch")
        with self.assertRaises(RuntimeError):
            manage.deploy(cluster, manage.resources("test"), 42, CREDENTIALS)
        self.assertFalse(any(d and d["metadata"]["name"] == "pharmago-users-service" and d["kind"] == "Deployment" for _, d in cluster.calls))


if __name__ == "__main__":
    unittest.main()
