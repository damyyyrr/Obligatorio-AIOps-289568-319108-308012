"""Seis ensayos acotados de PharmaGo. Por defecto solo imprime el plan, sin clúster."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from urllib.parse import urlparse
import uuid

HERE = Path(__file__).resolve().parent
NAMESPACE = "pharmago"
TARGET = "pharmago-pharmacy-service"
LOCK = "pharmago-chaos-lock"
OWNER = "pharmago.io/chaos-run"
SELECTOR_KEY = "pharmago.io/chaos-isolated"
SCENARIOS = ("requests", "cpu", "ram", "storage", "network", "disconnect")


def now():
    return datetime.now(timezone.utc).isoformat()


def host_available_bytes():
    if os.name == "nt":
        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in
                ("totalPhysical", "availablePhysical", "totalPage", "availablePage",
                 "totalVirtual", "availableVirtual", "extended")]
        state = Memory()
        state.length = ctypes.sizeof(state)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            raise RuntimeError("No se pudo comprobar memoria del host")
        return state.availablePhysical
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("No se pudo comprobar memoria del host")


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_local_server(server):
    uri = urlparse(server)
    if uri.scheme != "https" or uri.hostname not in ("127.0.0.1", "localhost", "::1", "kubernetes.docker.internal"):
        raise ValueError("Solo se admite un API server local explícito; no destinos externos")


def limits_safe(container):
    limits = container.get("resources", {}).get("limits", {})
    memory, cpu = limits.get("memory", ""), str(limits.get("cpu", ""))
    match = re.fullmatch(r"(\d+)Mi", memory)
    millicpu = int(cpu[:-1]) if re.fullmatch(r"\d+m", cpu) else int(cpu) * 1000 if cpu.isdigit() else 0
    return bool(match and 64 <= int(match[1]) <= 512 and 0 < millicpu <= 1000)


def validate_settings(args):
    if not args.context or args.context.startswith("-"):
        raise ValueError("Se requiere --context explícito")
    if not 1 <= args.duration <= 180 or not 1 <= args.megabytes <= 128:
        raise ValueError("Duración 1..180 s; memoria 1..128 MiB")
    if args.scenario == "storage" and args.megabytes > 64:
        raise ValueError("El ensayo de disco admite hasta 64 MiB")
    if not 1 <= args.requests <= 240 or not 1 <= args.concurrency <= 4:
        raise ValueError("Hasta 240 solicitudes y 4 workers")
    if args.execute and not args.operator.strip():
        raise ValueError("Identificar --operator; no se atribuyen roles humanos automáticamente")


class Cluster:
    def __init__(self, context):
        self.context = context

    def kub(self, *args, stdin=None, timeout=35):
        result = subprocess.run(["kubectl", "--context", self.context, "-n", NAMESPACE,
                                 "--request-timeout=" + ("0" if args[0] == "exec" else "25s"), *args],
                                input=stdin.encode("utf-8") if stdin is not None else None,
                                capture_output=True, timeout=timeout)
        if result.returncode:
            # Nunca reflejar stdin/stdout/stderr: exec puede contener credenciales/respuestas.
            raise RuntimeError(f"kubectl {args[0]} falló ({result.returncode}); revisar localmente")
        # text=True transforma LF en CRLF al escribir stdin desde Windows y rompe sh.
        return result.stdout.decode("utf-8")

    def get(self, resource, name=None):
        args = ["get", resource] + ([name] if name else []) + ["-o", "json"]
        return json.loads(self.kub(*args))

    def optional(self, resource, name):
        value = self.kub("get", resource, name, "--ignore-not-found", "-o", "json")
        return json.loads(value) if value.strip() else None

    def create(self, doc):
        return json.loads(self.kub("create", "-f", "-", "-o", "json", stdin=json.dumps(doc)))

    def patch(self, kind, name, operations):
        # Estos patches solo incluyen UID/selectores; nunca secretos.
        self.kub("patch", kind, name, "--type=json", "--patch", json.dumps(operations))

    def exec_script(self, pod, source, arguments, container=None, timeout=35):
        args = ["exec", "-i", pod]
        if container:
            args += ["-c", container]
        return self.kub(*args, "--", *arguments, stdin=source, timeout=timeout)

    def rpc(self, pod, data, timeout=45):
        command = ["python", "-c", (HERE / "probe.py").read_text(encoding="utf-8")]
        if data["action"] == "burst":
            if not re.fullmatch(r"[a-f0-9]{32}", data["runId"]):
                raise ValueError("Identidad inválida de generador")
            command = ["env", "PHARMAGO_CHAOS_RUNID=" + data["runId"], *command]
        return json.loads(self.exec_script(pod, json.dumps(data),
                                          command,
                                          timeout=timeout))


def require_ready(pods):
    if not pods or any(not any(c["type"] == "Ready" and c["status"] == "True"
                              for c in p.get("status", {}).get("conditions", [])) for p in pods):
        raise RuntimeError("No todos los pods del alcance están Ready")


def snapshot(cluster):
    pods = cluster.get("pods")["items"]
    claims = cluster.get("pvc")["items"]
    volumes = {p["spec"].get("volumeName") for p in claims}
    return {
        "timeUtc": now(),
        "pods": [{"name": p["metadata"]["name"], "uid": p["metadata"]["uid"],
                  "app": p["metadata"].get("labels", {}).get("app"),
                  "phase": p.get("status", {}).get("phase"),
                  "node": p["spec"].get("nodeName"),
                  "conditions": p.get("status", {}).get("conditions", []),
                  "containers": [{k: c.get(k) for k in ("name", "ready", "restartCount", "imageID")}
                                 for c in p.get("status", {}).get("containerStatuses", [])]}
                 for p in pods],
        "claims": {p["metadata"]["name"]: {"uid": p["metadata"]["uid"],
                   "volume": p["spec"].get("volumeName"), "phase": p["status"].get("phase")}
                   for p in claims},
        "volumes": {p["metadata"]["name"]: p["metadata"]["uid"]
                    for p in cluster.get("pv")["items"] if p["metadata"]["name"] in volumes},
        "deployments": {d["metadata"]["name"]: {"uid": d["metadata"]["uid"],
                         "replicas": d["spec"].get("replicas"),
                         "images": [c["image"] for c in d["spec"]["template"]["spec"]["containers"]]}
                        for d in cluster.get("deployments")["items"]},
    }


def namespace_lab(cluster):
    config = json.loads(cluster.kub("config", "view", "--minify", "-o", "json"))
    validate_local_server(config["clusters"][0]["cluster"]["server"])
    ns = cluster.get("namespace", NAMESPACE)
    if ns["metadata"].get("labels", {}).get("pharmago.io/chaos-lab") != "true":
        raise RuntimeError("El namespace no está identificado explícitamente como laboratorio de caos")
    return ns["metadata"]["uid"]


def assert_capacity(cluster):
    available = host_available_bytes()
    if available < 2 * 1024 ** 3:
        raise RuntimeError("Precheck: menos de 2 GiB de RAM libre en el host; no se inyectará carga")
    for node in cluster.get("nodes")["items"]:
        conditions = {c["type"]: c["status"] for c in node["status"].get("conditions", [])}
        if conditions.get("Ready") != "True" or any(conditions.get(k) == "True" for k in
                                                   ("MemoryPressure", "DiskPressure", "PIDPressure")):
            raise RuntimeError("Nodo sin Ready o con presión; abortar")
    return available


def owned_delete(cluster, resource, name, run_id, expected_uid=None):
    doc = cluster.optional(resource, name)
    if doc is None:
        return
    if doc["metadata"].get("labels", {}).get(OWNER) != run_id or (
            expected_uid and doc["metadata"]["uid"] != expected_uid):
        raise RuntimeError("Se rechaza borrar un recurso con otro propietario/UID")
    roots = {"configmap": "/api/v1", "networkpolicy": "/apis/networking.k8s.io/v1"}
    plurals = {"configmap": "configmaps", "networkpolicy": "networkpolicies"}
    if resource not in roots or not re.fullmatch(r"[a-z0-9-]+", name):
        raise ValueError("Tipo/nombre fuera del alcance de limpieza")
    # DELETE condicionado por UID y versión: no borrar un reemplazo ni cambios concurrentes.
    options = {"apiVersion": "v1", "kind": "DeleteOptions", "preconditions": {
        "uid": doc["metadata"]["uid"], "resourceVersion": doc["metadata"]["resourceVersion"]}}
    cluster.kub("delete", "--raw", f"{roots[resource]}/namespaces/{NAMESPACE}/{plurals[resource]}/{name}",
                "-f", "-", stdin=json.dumps(options))
    for _ in range(10):
        remaining = cluster.optional(resource, name)
        if remaining is None:
            return
        if remaining["metadata"]["uid"] != doc["metadata"]["uid"]:
            raise RuntimeError("El recurso fue reemplazado durante limpieza; no tocar el nuevo")
        time.sleep(1)
    raise RuntimeError("No se confirmó la eliminación del recurso temporal")


def restore_fault(cluster, journal):
    if namespace_lab(cluster) != journal["namespaceUid"]:
        raise RuntimeError("Cambió el UID del laboratorio; requiere recuperación manual")
    run_id, scenario = journal["runId"], journal["scenario"]
    if not re.fullmatch(r"[a-f0-9]{32}", run_id) or scenario not in SCENARIOS:
        raise ValueError("Journal inválido")
    if scenario == "network":
        owned_delete(cluster, "networkpolicy", "pharmago-chaos-" + run_id, run_id)
    if scenario == "disconnect":
        current = cluster.get("service", TARGET)
        if current["metadata"]["uid"] != journal["serviceUid"]:
            raise RuntimeError("Cambió la identidad del Service; no modificarlo")
        selector = current["spec"]["selector"]
        if SELECTOR_KEY in selector:
            if selector[SELECTOR_KEY] != run_id:
                raise RuntimeError("El selector pertenece a otro ensayo")
            path = "/spec/selector/pharmago.io~1chaos-isolated"
            cluster.patch("service", TARGET, [{"op": "test", "path": "/metadata/uid", "value": journal["serviceUid"]},
                {"op": "test", "path": path, "value": run_id}, {"op": "remove", "path": path}])
        if cluster.get("service", TARGET)["spec"]["selector"] != journal["selectorBefore"]:
            raise RuntimeError("El selector no coincide con el original; no sobrescribir cambios ajenos")
    if scenario in ("cpu", "ram", "storage"):
        pod = cluster.optional("pod", journal["pod"])
        if pod and pod["metadata"]["uid"] == journal["podUid"]:
            cluster.exec_script(journal["pod"], (HERE / "fault.sh").read_text(),
                                ["sh", "-s", "--", "cleanup", scenario, run_id, "1", "1"], TARGET)
            status = json.loads(cluster.exec_script(journal["pod"], (HERE / "fault.sh").read_text(),
                                ["sh", "-s", "--", "status", scenario, run_id, "1", "1"], TARGET))
            if status["active"]:
                raise RuntimeError("El agente sigue activo después de la limpieza")
        # Un pod eliminado/reemplazado pierde su capa efímera; nunca ejecutar en el reemplazo.
    if scenario == "requests":
        pod = cluster.optional("pod", "pharmago-chaos-load")
        if pod and pod["metadata"]["uid"] == journal["loadPodUid"]:
            result = cluster.rpc("pharmago-chaos-load", {"action": "stop", "runId": run_id})
            if not result.get("stopped"):
                raise RuntimeError("No se confirmó parada del generador")


def watchdog(path):
    """Proceso independiente: revierte si muere el controlador; no requiere credenciales de app."""
    initial = json.loads(path.read_text(encoding="utf-8"))
    cluster = Cluster(initial["context"])
    if namespace_lab(cluster) != initial["namespaceUid"]:
        raise RuntimeError("El watchdog no reconoce el laboratorio")
    atomic_json(path.parent / "watchdog-ready.json", {"ready": True})
    deadline = initial["faultDeadlineEpoch"]
    final_deadline = initial["overallDeadlineEpoch"]
    while time.time() < final_deadline:
        journal = json.loads(path.read_text(encoding="utf-8"))
        if journal.get("finished") or journal.get("finishing"):
            return
        if time.time() >= deadline and not journal.get("faultRestored"):
            try:
                restore_fault(cluster, journal)
                atomic_json(path.parent / "watchdog-result.json", {"timeUtc": now(), "faultRestored": True})
            except Exception as error:
                atomic_json(path.parent / "watchdog-result.json", {"timeUtc": now(), "error": type(error).__name__})
        time.sleep(2)
    journal = json.loads(path.read_text(encoding="utf-8"))
    restore_fault(cluster, journal)
    clear_remote_control(cluster, journal)
    owned_delete(cluster, "configmap", LOCK, journal["runId"], journal["lockUid"])


def clear_remote_control(cluster, journal):
    if journal["scenario"] == "requests":
        pod = cluster.optional("pod", "pharmago-chaos-load")
        if pod and pod["metadata"]["uid"] == journal["loadPodUid"]:
            if not cluster.rpc("pharmago-chaos-load", {"action": "stop", "runId": journal["runId"], "clear": True}).get("cleared"):
                raise RuntimeError("No se confirmó retirada del control del generador")
    elif journal["scenario"] in ("cpu", "ram", "storage"):
        pod = cluster.optional("pod", journal["pod"])
        if pod and pod["metadata"]["uid"] == journal["podUid"]:
            result = json.loads(cluster.exec_script(journal["pod"], (HERE / "fault.sh").read_text(),
                ["sh", "-s", "--", "clear", journal["scenario"], journal["runId"], "1", "1"], TARGET))
            if not result.get("cleared"):
                raise RuntimeError("No se confirmó retirada del control del agente")


class Trial:
    def __init__(self, args):
        self.args, self.cluster = args, Cluster(args.context)
        self.run_id = uuid.uuid4().hex
        self.directory = args.output.resolve() / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.journal_path = self.directory / "journal.json"
        self.report = {"runId": self.run_id, "scenario": args.scenario, "startedUtc": now(),
                       "operatorDeclared": args.operator, "tAck": None, "samples": [],
                       "observations": [], "events": [], "status": "PRECHECK", "liveValidation": True}
        self.report["sourceHashes"] = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                       for name in ("chaos.py", "fault.sh", "probe.py")}
        self.journal = None
        self.future = None
        self.expected = {}
        self.secret = {"username": args.username, "password": os.environ.get("PHARMAGO_TEST_PASSWORD", ""),
                       "grafanaPassword": os.environ.get("PHARMAGO_GRAFANA_PASSWORD", "")}

    def event(self, name, **data):
        entry = {"timeUtc": now(), "event": name, **data}
        self.report["events"].append(entry)
        print(json.dumps(entry), flush=True)
        self.save()

    def save(self):
        atomic_json(self.directory / "report.json", self.report)
        if self.journal:
            atomic_json(self.journal_path, self.journal)

    def sample(self, login=False):
        samples = self.cluster.rpc("pharmago-chaos-client", {"action": "sample", "login": login,
            "directPharmacy": self.args.scenario in ("network", "disconnect"), **self.secret})
        for item in samples:
            key = (item.get("target", "pharmago-api-gateway"), item["path"])
            if key in self.expected:
                item["valid"] = item["valid"] and item.get("fingerprint") == self.expected[key]
        self.report["samples"].extend(samples)
        return all(s["http"] == 200 and s["valid"] for s in samples)

    def observe(self):
        observation = {"timeUtc": now(), "cluster": snapshot(self.cluster),
                       "telemetry": self.cluster.rpc("pharmago-chaos-client", {"action": "observe", **self.secret})}
        self.report["observations"].append(observation)
        self.save()
        telemetry = observation["telemetry"]
        required = {"otlp-collector", "pharmago-app-pods", "node-exporter", "kubernetes-cadvisor", "kube-state-metrics"}
        targets = telemetry["targets"]["series"]
        if not required <= {s["metric"].get("job") for s in targets} or any(float(s["value"][1]) != 1 for s in targets):
            raise RuntimeError("Pérdida de targets: detener la inyección y resolver S3")
        for metric in ("cpu", "memory", "storage", "diskFree", "nodeMemoryFree"):
            if not telemetry[metric]["series"]:
                raise RuntimeError("Métricas de recursos incompletas: no continuar a ciegas")
        if any(float(s["value"][1]) < 256 * 1024 ** 2 for s in telemetry["nodeMemoryFree"]["series"]):
            raise RuntimeError("Menos de 256 MiB libres en un nodo: retirar el estímulo")
        if any(float(s["value"][1]) < 1024 ** 3 for s in telemetry["diskFree"]["series"]):
            raise RuntimeError("Filesystem de datos con menos de 1 GiB libre: retirar el estímulo")
        rules = telemetry["alerts"]["rules"]
        if len(rules) < 5 or any(r["health"] != "ok" for r in rules):
            raise RuntimeError("Se perdió evaluación sana de las alertas")
        if any(telemetry[k]["http"] != 200 for k in ("jaeger", "elasticsearch")):
            raise RuntimeError("Se perdió el backend de observabilidad")
        return observation

    def resource_status(self):
        if self.args.scenario not in ("cpu", "ram", "storage"):
            return
        result = json.loads(self.cluster.exec_script(self.journal["pod"], (HERE / "fault.sh").read_text(),
            ["sh", "-s", "--", "status", self.args.scenario, self.run_id, "1", "1"], TARGET))
        self.report.setdefault("injectionStates", []).append({"timeUtc": now(), **result})

    def check_effect(self):
        scenario = self.args.scenario
        injected_at = next(e["timeUtc"] for e in self.report["events"] if e["event"] == "inject-requested")
        during = [s for s in self.report["samples"] if injected_at <= s["receivedUtc"] < self.report["faultRestoredUtc"]]
        if scenario in ("network", "disconnect"):
            target = TARGET
            if not any(s["path"] == "/api/drug" and s.get("target", "pharmago-api-gateway") == target
                       and s["http"] != 200 for s in during):
                raise RuntimeError("No se observó corte de conexiones nuevas; comprobar enforcement del CNI en red"
                                   if scenario == "network" else "No se observó corte de conexiones nuevas al Service desconectado")
            if not any(s["path"] == "/api/roles" and s["http"] == 200 and s["valid"] for s in during):
                raise RuntimeError("No se verificó la ruta Users no afectada durante el corte")
        elif scenario == "requests":
            result = self.report.get("injectionResult", [])
            if not any(r.get("http") == 429 for r in result):
                raise RuntimeError("No se observó efecto de la cuota; no declarar PASS por enviar solicitudes")
        else:
            states = self.report.get("injectionStates", [])
            if not any(s.get("active") for s in states):
                raise RuntimeError("No se observó el agente activo")
            if scenario == "storage" and not any(s.get("bytes") == self.args.megabytes * 1048576 for s in states):
                raise RuntimeError("No se verificaron los bytes de almacenamiento inyectados")
            if scenario in ("cpu", "ram"):
                metric = "cpu" if scenario == "cpu" else "memory"
                def values(observation):
                    return [float(s["value"][1]) for s in observation["telemetry"][metric]["series"]
                            if s["metric"].get("pod") == self.journal["pod"]]
                baseline = values(self.report["observations"][0])
                observed = [v for o in self.report["observations"] if injected_at <= o["timeUtc"] < self.report["faultRestoredUtc"]
                            for v in values(o)]
                required = 0.05 if scenario == "cpu" else self.args.megabytes * 1048576 * 0.5
                if not baseline or not observed or max(observed) - max(baseline) < required:
                    raise RuntimeError("El incremento de recurso no fue observado en las métricas del pod")

    def preflight(self):
        namespace_uid = namespace_lab(self.cluster)
        self.report["hostAvailableBytesBefore"] = assert_capacity(self.cluster)
        self.report["sourceCommit"] = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"],
            text=True, capture_output=True, check=True, timeout=10).stdout.strip()
        self.report["dirtyTree"] = bool(subprocess.run(["git", "-C", str(HERE), "status", "--porcelain"],
            text=True, capture_output=True, check=True, timeout=10).stdout.strip())
        if not self.secret["password"] or not self.secret["grafanaPassword"]:
            raise RuntimeError("Faltan credenciales de prueba en variables de entorno locales")
        if self.cluster.optional("configmap", LOCK):
            raise RuntimeError("Hay un ensayo o recuperación pendiente; no adoptar su lock")
        pods = self.cluster.get("pods")["items"]
        require_ready([p for p in pods if p["status"].get("phase") != "Succeeded"])
        target_pods = [p for p in pods if p["metadata"].get("labels", {}).get("app") == TARGET]
        if not target_pods:
            raise RuntimeError("Falta el servicio Pharmacy")
        target = sorted(target_pods, key=lambda p: p["metadata"]["name"])[0]
        container = next(c for c in target["spec"]["containers"] if c["name"] == TARGET)
        if not limits_safe(container):
            raise RuntimeError("Se requieren límites de 64..512Mi y CPU >0 hasta 1 core")
        for mount in container.get("volumeMounts", []):
            path = mount["mountPath"].rstrip("/")
            if path == "" or path == "/tmp" or path.startswith("/tmp/"):
                raise RuntimeError("No ejecutar sobre /tmp montado: podría contener datos persistentes")
        for name in ("pharmago-chaos-client", "pharmago-chaos-load"):
            client = self.cluster.get("pod", name)
            if client["metadata"].get("labels", {}).get("pharmago.io/chaos-client") != "true":
                raise RuntimeError("El cliente no está identificado como recurso de laboratorio")
            if name == "pharmago-chaos-load":
                load_uid = client["metadata"]["uid"]
        if self.args.scenario == "network" and self.cluster.get("networkpolicies")["items"]:
            raise RuntimeError("Hay políticas existentes: no se puede garantizar aislamiento sin analizarlas")
        before = snapshot(self.cluster)
        if not self.sample(login=True):
            raise RuntimeError("Baseline funcional inválido; no inyectar otro fallo")
        self.expected = {(s.get("target", "pharmago-api-gateway"), s["path"]): s["fingerprint"]
                         for s in self.report["samples"] if "fingerprint" in s}
        telemetry = self.observe()["telemetry"]
        targets = telemetry["targets"]["series"]
        jobs = {x["metric"].get("job") for x in targets}
        required = {"otlp-collector", "pharmago-app-pods", "node-exporter", "kubernetes-cadvisor", "kube-state-metrics"}
        if not required <= jobs or any(float(x["value"][1]) != 1 for x in targets):
            raise RuntimeError("Targets incompletos o caídos; resolver S3 antes de inyectar")
        rules = telemetry["alerts"]["rules"]
        if len(rules) < 5 or any(r["health"] != "ok" or r["state"] != "inactive" for r in rules):
            raise RuntimeError("Las cinco alertas no están sanas e inactivas")
        if any(telemetry[k]["http"] != 200 for k in ("jaeger", "elasticsearch")):
            raise RuntimeError("Backend de trazas/logs no disponible")
        service = self.cluster.get("service", TARGET)
        if SELECTOR_KEY in service["spec"]["selector"]:
            raise RuntimeError("Selector de otra inyección presente")
        self.journal = {"runId": self.run_id, "context": self.args.context, "namespaceUid": namespace_uid,
                        "scenario": self.args.scenario, "pod": target["metadata"]["name"],
                        "podUid": target["metadata"]["uid"], "loadPodUid": load_uid,
                        "serviceUid": service["metadata"]["uid"],
                        "selectorBefore": service["spec"]["selector"], "lockUid": None,
                        "faultDeadlineEpoch": time.time() + self.args.duration + 45,
                        "overallDeadlineEpoch": time.time() + 600, "faultRestored": False, "finished": False}
        self.report["before"] = before
        self.save()
        lock = self.cluster.create({"apiVersion": "v1", "kind": "ConfigMap", "metadata": {
            "name": LOCK, "namespace": NAMESPACE, "labels": {OWNER: self.run_id}},
            "data": {"scenario": self.args.scenario, "runId": self.run_id}})
        self.journal["lockUid"] = lock["metadata"]["uid"]
        self.save()

    def inject(self):
        scenario = self.args.scenario
        current = self.cluster.get("pod", self.journal["pod"])
        if current["metadata"]["uid"] != self.journal["podUid"]:
            raise RuntimeError("Cambió el pod entre precheck e inyección")
        self.event("inject-requested", mechanism={"network": "NetworkPolicy ingress", "disconnect": "Service selector"}.get(scenario, scenario))
        if scenario == "network":
            self.cluster.create({"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
                "metadata": {"name": "pharmago-chaos-" + self.run_id, "namespace": NAMESPACE,
                             "labels": {OWNER: self.run_id}},
                "spec": {"podSelector": {"matchLabels": {"app": TARGET}}, "policyTypes": ["Ingress"],
                         "ingress": [{"from": [{"podSelector": {"matchExpressions": [{
                             "key": "app", "operator": "NotIn", "values": ["pharmago-api-gateway",
                             "pharmago-chaos-client", "pharmago-chaos-load"]}]}}]}]}})
            return None
        if scenario == "disconnect":
            self.cluster.patch("service", TARGET, [
                {"op": "test", "path": "/metadata/uid", "value": self.journal["serviceUid"]},
                {"op": "test", "path": "/spec/selector", "value": self.journal["selectorBefore"]},
                {"op": "add", "path": "/spec/selector/pharmago.io~1chaos-isolated", "value": self.run_id}])
            return None
        if scenario == "requests":
            return lambda: self.cluster.rpc("pharmago-chaos-load", {"action": "burst", "runId": self.run_id, "count": self.args.requests,
                "concurrency": self.args.concurrency, "duration": self.args.duration,
                "untilEpoch": self.journal["faultDeadlineEpoch"]}, timeout=self.args.duration + 30)
        return lambda: self.cluster.exec_script(self.journal["pod"], (HERE / "fault.sh").read_text(),
            ["timeout", "--signal=TERM", "--kill-after=5s", str(self.args.duration + 10), "sh", "-s", "--",
             "run", scenario, self.run_id, str(self.args.duration), str(self.args.megabytes),
             str(int(self.journal["faultDeadlineEpoch"]))], TARGET,
            timeout=self.args.duration + 25)

    def recover_window(self):
        start, candidate = time.monotonic(), None
        stable_at = None
        restart_baseline = None
        while time.monotonic() - start < 300:
            assert_capacity(self.cluster)
            valid = self.sample(login=candidate is None)
            observation = self.observe()
            pods = [p for p in observation["cluster"]["pods"] if p["phase"] != "Succeeded"]
            if not pods or not all(any(c["type"] == "Ready" and c["status"] == "True"
                                       for c in p["conditions"]) for p in pods):
                valid = False
            restarts = {p["uid"]: sum(c["restartCount"] or 0 for c in p["containers"]) for p in pods}
            if candidate is not None and restarts != restart_baseline:
                valid = False
            if valid:
                if candidate is None:
                    candidate, stable_at = time.monotonic(), now()
                    restart_baseline = restarts
                if time.monotonic() - candidate >= 120 and self.sample(login=True):
                    latest = self.report["observations"][-1]["telemetry"]
                    rules = latest["alerts"]["rules"]
                    if rules and all(r["state"] == "inactive" and r["health"] == "ok" for r in rules):
                        self.report.update(tRestore=stable_at, tVerified=now())
                        return
            else:
                candidate = None
                restart_baseline = None
            time.sleep(5)
        raise RuntimeError("No se verificaron 120 s estables y alertas OK en el presupuesto")

    def run(self):
        watch = None
        try:
            self.preflight()
            flags = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS} if os.name == "nt" else {"start_new_session": True}
            with (self.directory / "watchdog-local.log").open("w") as output:
                watch = subprocess.Popen([sys.executable, str(HERE / "chaos.py"), "--recover", str(self.journal_path),
                                          "--watchdog", "--execute"], stdout=output, stderr=output, **flags)
            for _ in range(50):
                if watch.poll() is not None:
                    raise RuntimeError("El watchdog no pudo iniciar")
                if (self.directory / "watchdog-ready.json").exists():
                    break
                time.sleep(0.2)
            else:
                raise RuntimeError("El watchdog no confirmó preparación; no inyectar")
            self.report["status"] = "RUNNING"
            worker = self.inject()
            pool = ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(worker) if worker else None
                self.future = future
                deadline = time.monotonic() + self.args.duration
                while time.monotonic() < deadline:
                    assert_capacity(self.cluster)
                    self.sample()
                    self.resource_status()
                    self.observe()
                    if future and future.done():
                        self.report["injectionResult"] = future.result()
                    time.sleep(5)
                if future:
                    self.report["injectionResult"] = future.result(timeout=30)
            finally:
                # No esperar al worker antes de retirar el estímulo ante presión/aborto.
                pool.shutdown(wait=False, cancel_futures=True)
            restore_fault(self.cluster, self.journal)
            self.journal["faultRestored"] = True
            self.report["faultRestoredUtc"] = now()
            self.event("fault-restored")
            self.check_effect()
            self.recover_window()
            after = snapshot(self.cluster)
            self.report["after"] = after
            if any(after[key] != self.report["before"][key] for key in ("claims", "volumes", "deployments")):
                raise RuntimeError("Cambió inventario de datos/configuración durante el ensayo")
            self.report["status"] = "PASS"
        except (Exception, KeyboardInterrupt) as error:
            self.report["status"] = "FAIL"
            self.event("abort", errorType=type(error).__name__, reason=str(error)
                       if isinstance(error, (ValueError, RuntimeError)) else "Fallo de herramienta o interrupción")
        finally:
            if self.journal:
                try:
                    restore_fault(self.cluster, self.journal)
                    self.journal["faultRestored"] = True
                    if self.future is not None:
                        try:
                            self.future.result(timeout=30)
                        except Exception:
                            # Timeout/cancelación local no confirma el fin de un RPC remoto.
                            if time.time() < self.journal["faultDeadlineEpoch"] + 15:
                                raise RuntimeError("RPC de resultado incierto: conservar cancelación y lock hasta deadline + 15s")
                        restore_fault(self.cluster, self.journal)
                    if watch:
                        # No retirar tombstones mientras el watchdog aún pueda recrearlos.
                        self.journal["finishing"] = True
                        self.save()
                        watch.wait(timeout=10)
                    clear_remote_control(self.cluster, self.journal)
                    owned_delete(self.cluster, "configmap", LOCK, self.run_id, self.journal["lockUid"])
                    self.journal["finished"] = True
                    self.report["cleanup"] = "verified"
                except Exception as error:
                    self.report.update(status="FAIL", cleanup="MANUAL_RECOVERY_REQUIRED", cleanupError=type(error).__name__)
            self.report["finishedUtc"] = now()
            self.save()
        return self.report["status"] == "PASS"


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("scenario", nargs="?", choices=SCENARIOS)
    result.add_argument("--context")
    result.add_argument("--execute", action="store_true")
    result.add_argument("--operator", default="")
    result.add_argument("--username", default="admin")
    result.add_argument("--duration", type=int, default=60)
    result.add_argument("--megabytes", type=int, default=32)
    result.add_argument("--requests", type=int, default=240)
    result.add_argument("--concurrency", type=int, default=4)
    result.add_argument("--output", type=Path, default=Path(".runtime/chaos"))
    result.add_argument("--recover", type=Path)
    result.add_argument("--watchdog", action="store_true", help=argparse.SUPPRESS)
    return result


def main():
    args = parser().parse_args()
    if args.recover:
        if not args.execute:
            raise ValueError("La recuperación también requiere --execute")
        if args.watchdog:
            watchdog(args.recover)
        else:
            journal = json.loads(args.recover.read_text(encoding="utf-8"))
            cluster = Cluster(journal["context"])
            restore_fault(cluster, journal)
            if journal["scenario"] in ("requests", "cpu", "ram", "storage") and time.time() < journal["faultDeadlineEpoch"] + 15:
                raise RuntimeError("Cancelación aplicada: esperar deadline + 15s antes de retirar controles de un RPC incierto")
            clear_remote_control(cluster, journal)
            owned_delete(cluster, "configmap", LOCK, journal["runId"], journal["lockUid"])
            journal.update(faultRestored=True, finished=True)
            atomic_json(args.recover, journal)
        return 0
    if not args.scenario:
        raise ValueError("Elegir uno de los seis escenarios")
    validate_settings(args)
    if not args.execute:
        print(json.dumps({"mode": "DRY_RUN_OFFLINE", "scenario": args.scenario, "context": args.context,
                          "namespace": NAMESPACE, "target": TARGET, "durationSeconds": args.duration,
                          "megabytes": args.megabytes, "requests": args.requests,
                          "maxConcurrency": args.concurrency, "maxRequestsPerSecond": 4,
                          "requiredHostFreeGiB": 2, "restorationWindowSeconds": 120,
                          "mutations": False, "requiresCniEnforcement": args.scenario == "network"}))
        return 0
    return 0 if Trial(args).run() else 1


def interrupt(*_):
    raise KeyboardInterrupt()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt)
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"ERROR: {type(error).__name__}: revisar precondiciones locales", file=sys.stderr)
        sys.exit(1)
