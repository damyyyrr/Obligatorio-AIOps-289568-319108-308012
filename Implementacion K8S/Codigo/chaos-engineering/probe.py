"""Cliente dentro del pod de pruebas: destinos fijos y resultados sin cuerpos/secretos."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


def now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    if isinstance(value, list):
        value = sorted(value, key=lambda x: json.dumps(x, sort_keys=True))
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def request(url, payload=None, headers=None):
    started, sent = time.monotonic(), now()
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    code, value, retry = 0, None, None
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            code = response.status
            value = json.load(response)
    except urllib.error.HTTPError as error:
        code, retry = error.code, error.headers.get("Retry-After")
    except (OSError, ValueError):
        pass
    return {"sentUtc": sent, "receivedUtc": now(), "http": code,
            "latencyMs": round((time.monotonic() - started) * 1000, 3),
            "retryAfter": retry if retry and retry.isdigit() else None}, value


def sample(data):
    results = []
    routes = [("pharmago-api-gateway", "/api/drug"), ("pharmago-api-gateway", "/api/roles")]
    if data.get("directPharmacy"):
        # Conexión nueva al backend: una conexión reutilizada por YARP puede sobrevivir
        # a la actualización de NetworkPolicy. Registrar ambas rutas, sin confundirlas.
        routes.insert(0, ("pharmago-pharmacy-service", "/api/drug"))
    for target, path in routes:
        result, value = request("http://" + target + path)
        result.update(path=path, target=target, valid=isinstance(value, list) and bool(value),
                      fingerprint=fingerprint(value) if isinstance(value, list) else None)
        results.append(result)
    if data.get("login"):
        result, value = request("http://pharmago-api-gateway/api/login",
                                {"userName": data["username"], "password": data["password"]})
        result.update(path="/api/login", target="pharmago-api-gateway", valid=bool(isinstance(value, dict) and value.get("token")
                                                   and value.get("userName") == data["username"]))
        results.append(result)
    return results


def burst(data):
    count, concurrency, duration = data["count"], data["concurrency"], data["duration"]
    if not (1 <= count <= 240 and 1 <= concurrency <= 4 and 1 <= duration <= 180):
        raise ValueError("Carga fuera de los límites")
    run_id = data["runId"]
    if not re.fullmatch(r"[a-f0-9]{32}", run_id) or os.environ.get("PHARMAGO_CHAOS_RUNID") != run_id:
        raise ValueError("El generador no tiene identidad de ensayo")
    cancelled = Path("/tmp") / ("pharmago-chaos-" + run_id + ".cancel")
    if cancelled.exists() or time.time() >= data["untilEpoch"]:
        return []
    marker = Path("/tmp") / ("pharmago-chaos-" + run_id + ".pid")
    with marker.open("x") as stream:
        stream.write(str(os.getpid()))
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    deadline = time.monotonic() + min(duration, max(0, data["untilEpoch"] - time.time()))
    lock = threading.Lock()
    next_slot = [time.monotonic()]

    def one(_):
        with lock:
            slot = next_slot[0]
            next_slot[0] = max(slot, time.monotonic()) + 0.25
        stopped.wait(max(0, slot - time.monotonic()))
        if stopped.is_set() or cancelled.exists() or time.monotonic() >= deadline:
            return {"skipped": True}
        result, _ = request("http://pharmago-api-gateway/api/drug")
        return result

    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            return list(pool.map(one, range(count)))
    finally:
        marker.unlink(missing_ok=True)


def stop_burst(data):
    run_id = data["runId"]
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise ValueError("Identidad inválida")
    marker = Path("/tmp") / ("pharmago-chaos-" + run_id + ".pid")
    cancelled = Path("/tmp") / ("pharmago-chaos-" + run_id + ".cancel")
    if data.get("clear"):
        if marker.exists():
            raise RuntimeError("No retirar control mientras el generador está activo")
        if cancelled.exists():
            if cancelled.is_symlink() or cancelled.read_text() != run_id:
                raise ValueError("El archivo de control tiene otro propietario")
            cancelled.unlink()
        return {"cleared": True}
    try:
        with cancelled.open("x") as stream:
            stream.write(run_id)
    except FileExistsError:
        if cancelled.is_symlink() or cancelled.read_text() != run_id:
            raise ValueError("El archivo de control tiene otro propietario")
    # El marcador persiste hasta verificar fin del RPC o su deadline absoluto.
    # Evita que una ejecución remota demorada empiece a cargar después del aborto.
    if not marker.exists():
        return {"stopped": True}
    if marker.is_symlink():
        raise ValueError("No seguir enlaces en archivos de control")
    pid = int(marker.read_text())
    if pid <= 1:
        raise ValueError("PID inválido")
    environment = Path(f"/proc/{pid}/environ")
    if environment.exists():
        if ("PHARMAGO_CHAOS_RUNID=" + run_id).encode() not in environment.read_bytes().split(b"\0"):
            raise ValueError("El PID ya no pertenece al generador")
        os.kill(pid, signal.SIGTERM)
    for _ in range(150):
        if not marker.exists():
            return {"stopped": True}
        time.sleep(0.1)
    raise RuntimeError("El generador no confirmó parada; conservar archivo de control y escalar")


def observe(data):
    queries = {
        "targets": 'up{job=~"otlp-collector|pharmago-app-pods|kube-state-metrics|node-exporter|kubernetes-cadvisor"}',
        "cpu": 'sum by(pod)(rate(container_cpu_usage_seconds_total{job="kubernetes-cadvisor",namespace="pharmago",container=""}[1m]))',
        "memory": 'max by(pod)(container_memory_working_set_bytes{job="kubernetes-cadvisor",namespace="pharmago",container=""})',
        "storage": 'k8s_pod_filesystem_usage_bytes{namespace="pharmago"}',
        "diskFree": 'node_filesystem_avail_bytes{job="node-exporter",mountpoint=~"/|/var|/mnt/data",fstype!~"tmpfs|devtmpfs|squashfs"}',
        "nodeMemoryFree": 'node_memory_MemAvailable_bytes{job="node-exporter"}',
    }
    output = {}
    for name, query in queries.items():
        result, value = request("http://prometheus:9090/api/v1/query?" + urllib.parse.urlencode({"query": query}))
        output[name] = {"http": result["http"], "series": value.get("data", {}).get("result", [])
                        if isinstance(value, dict) else []}
    auth = base64.b64encode(("admin:" + data["grafanaPassword"]).encode()).decode()
    result, value = request("http://grafana:3000/api/prometheus/grafana/api/v1/rules",
                            headers={"Authorization": "Basic " + auth})
    output["alerts"] = {"http": result["http"], "rules": [
        {"name": rule["name"], "state": rule["state"], "health": rule.get("health")}
        for group in (value or {}).get("data", {}).get("groups", []) for rule in group["rules"]]}
    for name, url in (("jaeger", "http://jaeger:16686/api/services"),
                      ("elasticsearch", "http://elasticsearch:9200/_cluster/health")):
        result, _ = request(url)
        output[name] = {"http": result["http"]}
    return output


if __name__ == "__main__":
    data = json.load(sys.stdin)
    actions = {"sample": sample, "burst": burst, "observe": observe, "stop": stop_burst}
    print(json.dumps(actions[data["action"]](data)))
