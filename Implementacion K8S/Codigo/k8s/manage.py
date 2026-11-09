"""Shared Kubernetes workflow for PowerShell and Bash. Python 3.10+."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

import yaml

ROOT = Path(__file__).resolve().parent
CODE = ROOT.parent
APP_IMAGES = {
    "pharmago-users-service": "PharmaGo.UsersService/Dockerfile",
    "pharmago-pharmacy-service": "PharmaGo.PharmacyService/Dockerfile",
    "pharmago-api-gateway": "PharmaGo.ApiGateway/Dockerfile",
    "pharmago-ui": "Dockerfile",
}
PVS = ("sql-pv", "elasticsearch-pv", "prometheus-pv", "grafana-pv")
SERVICE_ROLE = "pharmago.io/service"
STORAGE_OWNER = "pharmago.io/storage-node-uid"
HOSTNAME_LABEL = "kubernetes.io/hostname"
SERVICE_ROLES = {"gateway", "users", "pharmacy"}


def run(*args, stdin=None):
    result = subprocess.run(list(map(str, args)), input=stdin, text=True,
                            encoding="utf-8", capture_output=True, check=False)
    if result.returncode:
        # Never echo stdin: rendered resources may include Secrets.
        raise RuntimeError(f"{args[0]} {args[1]} failed ({result.returncode}): {result.stderr.strip()}")
    return result.stdout.strip()


def tag_value(value):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", value) or value == "latest":
        raise argparse.ArgumentTypeError("Use an explicit image tag, not latest")
    return value


def archive_config_digest(stream):
    """CRI IDs hash the image config, not Docker's OCI index/manifest descriptor."""
    configs = {}
    manifests = []
    with tarfile.open(fileobj=stream, mode="r|*") as archive:
        for member in archive:
            if not member.isfile() or member.size > 1024 * 1024:
                continue
            if member.name != "manifest.json" and not member.name.endswith(".json") and not member.name.startswith("blobs/sha256/"):
                continue
            data = archive.extractfile(member).read()
            if member.name == "manifest.json":
                manifests = json.loads(data)
            else:
                try:
                    value = json.loads(data)
                except (ValueError, UnicodeDecodeError):
                    continue
                if isinstance(value, dict) and "rootfs" in value and "architecture" in value:
                    configs[member.name] = "sha256:" + hashlib.sha256(data).hexdigest()
    if len(manifests) != 1 or manifests[0]["Config"] not in configs:
        raise RuntimeError("Expected one image configuration in Docker archive")
    return configs[manifests[0]["Config"]]


def image_config_digest(image):
    # Stream export: no second image archive is written to the host disk.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(["docker", "image", "save", image], stdout=subprocess.PIPE, stderr=errors)
        try:
            digest = archive_config_digest(process.stdout)
            if process.wait(timeout=120):
                raise RuntimeError("Docker image export failed")
            return digest
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)


def resources(tag, topology="separated"):
    paths = [ROOT / "namespace.yaml"]
    for directory in ("configmaps", "persistent-volumes", "services", "deployments"):
        paths.extend(sorted((ROOT / directory).rglob("*.yaml")))
    docs = [d for path in paths for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]
    # Apply prerequisites before workloads; RBAC is included in both entrypoints.
    order = {"Namespace": 0, "StorageClass": 1, "PersistentVolume": 2,
             "PersistentVolumeClaim": 3, "ConfigMap": 5,
             "ServiceAccount": 6, "ClusterRole": 7, "ClusterRoleBinding": 8, "Service": 9}
    docs.sort(key=lambda d: order.get(d["kind"], 10))
    for doc in docs:
        if doc["kind"] in ("Deployment", "DaemonSet"):
            spec = doc["spec"]["template"]["spec"]
            if topology == "single-node" and SERVICE_ROLE in spec.get("nodeSelector", {}):
                del spec["nodeSelector"][SERVICE_ROLE]
                spec["nodeSelector"]["node-type"] = "all"
            for container in spec.get("containers", []) + spec.get("initContainers", []):
                image = container["image"]
                name = image.split(":")[0]
                if name in APP_IMAGES:
                    container["image"] = f"{name}:{tag}"
                elif image.endswith(":latest") or image.endswith("-latest"):
                    raise RuntimeError(f"Mutable image in {doc['metadata']['name']}: {image}")
    return docs


def read_secrets(path):
    try:
        values = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        raise RuntimeError("The local secrets file must be valid JSON") from None
    except OSError:
        raise RuntimeError(f"Cannot read local secrets file {path}; see secrets.example.json") from None
    keys = {"sqlPassword", "grafanaAdminPassword"}
    if not isinstance(values, dict) or values.keys() != keys:
        raise RuntimeError("The local secrets file requires sqlPassword and grafanaAdminPassword")
    if any(not isinstance(value, str) or not value.strip() or value == "REEMPLAZAR"
           or any(ch in value for ch in "\0\r\n") for value in values.values()):
        raise RuntimeError("Replace both placeholders with non-empty single-line passwords")
    return values


def secret_resources(values):
    sql = values["sqlPassword"]
    # ADO.NET escapes a quote inside a quoted value by doubling it.
    connection = 'Server=pharmago-db;Database=PharmaDb;User Id=sa;Password="' + sql.replace('"', '""') + '"'
    credentials = {
        "db-secret": {"SA_PASSWORD": sql, "CONNECTION_STRING": connection},
        "grafana-secret": {"ADMIN_PASSWORD": values["grafanaAdminPassword"]},
    }
    return [{
        "apiVersion": "v1", "kind": "Secret", "type": "Opaque",
        "metadata": {"name": name, "namespace": "pharmago"},
        "data": {key: base64.b64encode(value.encode("utf-8")).decode("ascii")
                 for key, value in data.items()},
    } for name, data in credentials.items()]


def validate_topology(nodes, candidates, topology):
    def labels(node):
        return node["metadata"].get("labels", {})

    # Count even unavailable storage nodes: they could become eligible again.
    storage = [n for n in nodes if labels(n).get("node-type") in ("ops", "all")]
    if len(storage) != 1 or storage[0] not in candidates:
        raise RuntimeError("Current hostPath manifests require exactly one schedulable Ready ops/all storage node")
    owner = storage[0]
    hostname = labels(owner).get(HOSTNAME_LABEL)
    if not hostname or sum(labels(n).get(HOSTNAME_LABEL) == hostname for n in nodes) != 1:
        raise RuntimeError("The storage node must have a unique kubernetes.io/hostname label")
    if topology == "single-node":
        if len(nodes) != 1 or labels(owner).get("node-type") != "all":
            raise RuntimeError("single-node requires a one-node cluster labeled node-type=all")
    else:
        if labels(owner).get("node-type") == "all":
            raise RuntimeError("node-type=all is only supported with --topology single-node")
        roles = {labels(n).get(SERVICE_ROLE) for n in candidates}
        missing = SERVICE_ROLES - roles
        if missing:
            raise RuntimeError(f"Label schedulable Ready nodes with {SERVICE_ROLE}; missing: {', '.join(sorted(missing))}")
        if not any(labels(n).get("node-type") == "frontend" for n in candidates):
            raise RuntimeError("Label a schedulable Ready node node-type=frontend for UI and Kibana")
    return owner


class Cluster:
    def __init__(self, context, topology="separated"):
        self.context = context
        self.topology = topology

    def call(self, *args, stdin=None):
        return run("kubectl", "--context", self.context, "--request-timeout=30s", *args, stdin=stdin)

    def preflight(self, workloads=True):
        current = run("kubectl", "config", "current-context")
        if current != self.context:
            raise RuntimeError(f"Current context {current!r} differs from requested {self.context!r}")
        nodes = json.loads(self.call("get", "nodes", "-o", "json"))["items"]
        ready = [n for n in nodes if not n["spec"].get("unschedulable") and any(
            c["type"] == "Ready" and c["status"] == "True" for c in n["status"].get("conditions", []))]
        if not ready:
            raise RuntimeError("No schedulable Ready nodes")
        owner = None
        if workloads:
            # The Deployment pods have no tolerations for blocking node taints.
            candidates = [n for n in ready if not any(
                t["effect"] in ("NoSchedule", "NoExecute") for t in n["spec"].get("taints", []))]
            owner = validate_topology(nodes, candidates, self.topology)
        ns = self.call("get", "namespace", "pharmago", "--ignore-not-found", "-o", "json")
        if ns and json.loads(ns).get("status", {}).get("phase") == "Terminating":
            raise RuntimeError("Namespace pharmago is Terminating")
        return owner

    def volumes(self):
        found = []
        for name in PVS:
            value = self.call("get", "pv", name, "--ignore-not-found", "-o", "json")
            if value:
                pv = json.loads(value)
                if pv.get("metadata", {}).get("deletionTimestamp") or pv.get("status", {}).get("phase") in ("Released", "Failed"):
                    raise RuntimeError(f"PV {name} needs manual recovery; it will not be deleted")
                claim = pv["spec"].get("claimRef", {})
                expected = name.replace("-pv", "-pvc")
                if claim and (claim.get("namespace"), claim.get("name")) != ("pharmago", expected):
                    raise RuntimeError(f"PV {name} belongs to another claim")
                found.append({"name": name, "uid": pv["metadata"]["uid"], "claimUid": claim.get("uid"),
                              "storageNodeUid": pv["metadata"].get("annotations", {}).get(STORAGE_OWNER),
                              "hostPath": pv["spec"].get("hostPath", {}).get("path"),
                              "nodeAffinity": pv["spec"].get("nodeAffinity")})
        return found

    def plan_secrets(self, desired, sql_volume_exists):
        changes = []
        for doc in desired:
            name = doc["metadata"]["name"]
            try:
                found = self.call("-n", "pharmago", "get", "secret", name, "--ignore-not-found", "-o", "json")
            except RuntimeError as exc:
                # A fresh cluster has no namespace yet.
                if 'namespaces "pharmago" not found' not in str(exc):
                    raise RuntimeError(f"Cannot inspect Secret/{name}") from None
                found = ""
            if not found:
                if name == "db-secret" and sql_volume_exists:
                    raise RuntimeError("The existing SQL volume needs its original db-secret before deployment")
                changes.append(("create", doc))
                continue
            existing = json.loads(found)
            old_data = existing.get("data", {})
            password_key = "SA_PASSWORD" if name == "db-secret" else "ADMIN_PASSWORD"
            if old_data.get(password_key) != doc["data"][password_key]:
                raise RuntimeError(f"Local password differs from Secret/{name}; use the current password or rotate both together")
            metadata = existing["metadata"]
            annotations = metadata.get("annotations", {})
            last_applied = annotations.pop("kubectl.kubernetes.io/last-applied-configuration", None)
            data = {**old_data, **doc["data"]}
            if data != old_data or last_applied is not None:
                existing["data"] = data
                changes.append(("replace", existing))
        return changes

    def write_secrets(self, changes):
        for action, doc in changes:
            name = doc["metadata"]["name"]
            try:
                # Avoid copying credentials into last-applied annotations or command arguments.
                self.call(action, "-f", "-", stdin=json.dumps(doc))
            except RuntimeError:
                raise RuntimeError(f"Could not {action} Secret/{name}; verify access and retry") from None
            print(f"Configured Secret/{name}")

    def apply(self, docs):
        # One resource per call: failures stop immediately, including early ConfigMaps/RBAC.
        for doc in docs:
            self.call("apply", "-f", "-", stdin=json.dumps(doc))
            print(f"Applied {doc['kind']}/{doc['metadata']['name']}")

    def wait(self, doc, timeout):
        kind = doc["kind"].lower()
        self.call(f"--request-timeout={timeout + 30}s", "-n", "pharmago", "rollout", "status", f"{kind}/{doc['metadata']['name']}", f"--timeout={timeout}s")

    def migrate(self, users, timeout):
        name = f"pharmago-db-migrate-{uuid.uuid4().hex[:12]}"
        self.call("create", "-f", "-", stdin=json.dumps(migration_job(users, name, timeout)))
        print(f"Waiting for Job/{name}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = json.loads(self.call("-n", "pharmago", "get", "job", name, "-o", "json"))
            conditions = {c["type"] for c in job.get("status", {}).get("conditions", []) if c["status"] == "True"}
            if conditions & {"Failed", "FailureTarget"}:
                raise RuntimeError(f"Migration Job/{name} failed. Inspect kubectl logs job/{name} in pharmago.")
            if "Complete" in conditions:
                print(f"Completed Job/{name}")
                return name
            time.sleep(2)
        raise RuntimeError(f"Timed out waiting for migration Job/{name} in pharmago.")


def migration_job(users, name, timeout):
    users_pod = users["spec"]["template"]["spec"]
    source = users_pod["containers"][0]
    return {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {"name": name, "namespace": "pharmago"},
        "spec": {
            "backoffLimit": 0, "activeDeadlineSeconds": timeout, "ttlSecondsAfterFinished": 3600,
            "template": {
                "metadata": {"labels": {"app": "pharmago-db-migrate"}},
                "spec": {
                    "restartPolicy": "Never", "automountServiceAccountToken": False,
                    "nodeSelector": users_pod["nodeSelector"],
                    "containers": [{
                        "name": "migrate", "image": source["image"], "imagePullPolicy": source["imagePullPolicy"],
                        "args": ["--migrate"], "resources": source["resources"],
                        "env": [e for e in source["env"] if e["name"] == "ConnectionStrings__DefaultConnection"],
                    }],
                },
            },
        },
    }


def pin_storage(base, workloads, before, owner, topology):
    hostname = owner["labels"][HOSTNAME_LABEL]
    existing = {p["name"]: p for p in before}
    for pv in before:
        recorded = pv["storageNodeUid"]
        if recorded and recorded != owner["uid"]:
            raise RuntimeError(f"PV {pv['name']} belongs to another storage node; verify/recover its data before applying")
        if not recorded and topology == "separated":
            raise RuntimeError(f"PV {pv['name']} lacks {STORAGE_OWNER}; verify the existing data owner before adopting it")
    for doc in base:
        if doc["kind"] != "PersistentVolume":
            continue
        metadata = doc["metadata"]
        previous = existing.get(metadata["name"])
        if previous:
            if previous["hostPath"] != doc["spec"]["hostPath"]["path"] or not previous["nodeAffinity"]:
                raise RuntimeError(f"PV {metadata['name']} has an unexpected path or node affinity; verify its data owner")
            # The API does not allow changing the affinity of these existing PVs.
            doc["spec"]["nodeAffinity"] = previous["nodeAffinity"]
        else:
            doc["spec"]["nodeAffinity"] = {"required": {"nodeSelectorTerms": [
                {"matchExpressions": [{"key": HOSTNAME_LABEL, "operator": "In", "values": [hostname]}]}
            ]}}
        if not previous or previous["storageNodeUid"]:
            metadata.setdefault("annotations", {})[STORAGE_OWNER] = owner["uid"]
    for doc in workloads:
        spec = doc["spec"]["template"]["spec"]
        if any("persistentVolumeClaim" in v for v in spec.get("volumes", [])):
            spec.setdefault("nodeSelector", {})[HOSTNAME_LABEL] = hostname


def deploy(cluster, docs, timeout, credentials):
    owner = cluster.preflight()["metadata"]
    before = cluster.volumes()
    base = [d for d in docs if d["kind"] not in ("Deployment", "DaemonSet")]
    workloads = [d for d in docs if d["kind"] in ("Deployment", "DaemonSet")]
    pin_storage(base, workloads, before, owner, cluster.topology)
    changes = cluster.plan_secrets(secret_resources(credentials), any(p["name"] == "sql-pv" for p in before))
    cluster.apply([base[0]])  # Namespace must exist before creating its Secrets.
    cluster.write_secrets(changes)
    cluster.apply(base[1:])
    by_name = {d["metadata"]["name"]: d for d in workloads}
    sql = by_name.pop("pharmago-db")
    cluster.apply([sql])
    cluster.wait(sql, timeout)
    job = cluster.migrate(by_name["pharmago-users-service"], timeout)
    elasticsearch = by_name.pop("elasticsearch")
    cluster.apply([elasticsearch])
    cluster.wait(elasticsearch, timeout)
    remaining = list(by_name.values())
    cluster.apply(remaining)
    for doc in remaining:
        cluster.wait(doc, timeout)
    after = cluster.volumes()
    by_name = {p["name"]: p for p in after}
    for previous in before:
        actual = by_name.get(previous["name"])
        if not actual or actual["uid"] != previous["uid"] or (previous["claimUid"] and actual["claimUid"] != previous["claimUid"]):
            raise RuntimeError("PV or bound PVC identity changed during deployment")
    return {"volumesBefore": before, "volumesAfter": after, "topology": cluster.topology, "migrationJob": job,
            "storageNode": owner["name"],
            "pods": json.loads(cluster.call("-n", "pharmago", "get", "pods", "-o", "json"))}


def build(cluster, tag, profile, ui_only=False):
    cluster.preflight(workloads=False)
    if run("minikube", "-p", profile, "status", "--format={{.Kubeconfig}}") != "Configured":
        raise RuntimeError("Minikube profile kubeconfig is not configured")
    # Do not load images into a profile different from the selected cluster.
    profile_nodes = json.loads(run("minikube", "-p", profile, "kubectl", "--", "get", "nodes", "-o", "json"))["items"]
    cluster_nodes = json.loads(cluster.call("get", "nodes", "-o", "json"))["items"]
    if {n["metadata"]["uid"] for n in profile_nodes} != {n["metadata"]["uid"] for n in cluster_nodes}:
        raise RuntimeError("Minikube profile nodes differ from the requested Kubernetes context")
    result = []
    for name, dockerfile in APP_IMAGES.items():
        if ui_only and name != "pharmago-ui":
            continue
        context = CODE / ("Frontend" if name == "pharmago-ui" else "Backend")
        image = f"{name}:{tag}"
        # Refuse to overwrite a previously built tag with unrelated content.
        existing = run("docker", "image", "ls", "--quiet", image)
        if existing:
            raise RuntimeError(f"Image {image} already exists; choose a new tag")
        run("docker", "build", "-f", context / dockerfile, "-t", image, context)
        run("minikube", "-p", profile, "image", "load", image)
        image_id = run("docker", "image", "inspect", image, "--format={{.Id}}")
        config_digest = image_config_digest(image)
        # Verify each node, not only a profile-wide listing.
        for item in profile_nodes:
            node = item["metadata"]["name"]
            listing = run("minikube", "-p", profile, "ssh", "--node", node, "--", "sudo", "crictl", "images", "-o", "json")
            items = json.loads(listing).get("images", [])
            if not any(i.get("id") == config_digest and (image in i.get("repoTags", []) or f"docker.io/library/{image}" in i.get("repoTags", [])) for i in items):
                raise RuntimeError(f"Image {image} missing on node {node}")
        result.append({"image": image, "id": image_id, "configDigest": config_digest})
    return {"images": result, "profile": profile}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("render", "apply", "build", "stop"))
    parser.add_argument("--context")
    parser.add_argument("--image-tag", type=tag_value)
    parser.add_argument("--profile")
    parser.add_argument("--topology", choices=("separated", "single-node"), default="separated")
    parser.add_argument("--secrets-file", type=Path, default=ROOT / "secrets.local.json",
                        help="local JSON credentials file for apply")
    parser.add_argument("--ui-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.action in ("render", "apply", "build") and not args.image_tag:
        parser.error("--image-tag is required")
    if args.action != "render" and not args.context:
        parser.error("--context is required")
    if args.action == "build" and not args.profile:
        parser.error("--profile is required for Minikube image loading")
    if args.action == "render":
        value = json.dumps({"apiVersion": "v1", "kind": "List", "items": resources(args.image_tag, args.topology)}, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(value, encoding="utf-8")
        else:
            print(value)
        return
    cluster = Cluster(args.context, args.topology)
    if args.action == "apply":
        result = deploy(cluster, resources(args.image_tag, args.topology), args.timeout, read_secrets(args.secrets_file))
    elif args.action == "build":
        result = build(cluster, args.image_tag, args.profile, args.ui_only)
    else:
        cluster.preflight(workloads=False)
        cluster.call("-n", "pharmago", "scale", "deployment", "--all", "--replicas=0")
        # DaemonSets remain active; namespace, PVCs and PVs are retained.
        result = {"deploymentsScaledToZero": True, "daemonSetsRetained": True}
    result.update({"action": args.action, "context": args.context, "imageTag": args.image_tag,
                   "timeUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "commit": run("git", "-C", ROOT, "rev-parse", "HEAD"),
                   "workingTree": run("git", "-C", ROOT, "status", "--porcelain")})
    destination = args.output or ROOT / ".runtime" / f"{args.action}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Completed {args.action}. Local evidence: {destination}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
