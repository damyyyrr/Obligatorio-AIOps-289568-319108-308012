"""Experimentos locales y acotados para disparar cada alerta de Grafana (issue #13).

Cada escenario tiene duración fija, restaura el estado al terminar (también ante Ctrl+C)
e imprime las horas UTC de inicio, restauración y fin. Pensado para Docker Desktop
(contexto docker-desktop): latencia y Ready usan `docker pause` sobre el contenedor del Pod.

    python alert-scenarios.py --context docker-desktop --client client errors
    python alert-scenarios.py --context docker-desktop --client client latency
    python alert-scenarios.py --context docker-desktop cpu | memory | ready
"""
import argparse
import datetime
import json
import subprocess
import time

NS = "pharmago"
PHARMACY = "pharmago-pharmacy-service"
LOAD = """
import collections, sys, time, urllib.request, urllib.error
end = time.time() + float(sys.argv[1]); codes = collections.Counter()
while time.time() < end:  # ~1 req/s: por debajo del limite de 100/min por IP del Gateway
    started = time.time()
    try:
        with urllib.request.urlopen("http://pharmago-api-gateway/api/drug", timeout=15) as r: codes[r.status] += 1
    except urllib.error.HTTPError as e: codes[e.code] += 1
    except Exception as e: codes[type(e).__name__] += 1
    time.sleep(max(0, 1.0 - (time.time() - started)))
print("load", dict(codes))
"""


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class Lab:
    def __init__(self, context, client):
        self.context, self.client = context, client

    def kubectl(self, *args, check=True):
        for _ in range(6):  # tolera cortes TLS intermitentes del proxy local
            result = subprocess.run(["kubectl", "--context", self.context, "-n", NS, *args],
                                    capture_output=True, text=True)
            if "x509" not in result.stderr:
                break
            time.sleep(2)
        if check and result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
        return result.stdout.strip()

    def pod(self, app):
        return self.kubectl("get", "pod", "-l", f"app={app}", "--field-selector=status.phase=Running",
                            "-o", "jsonpath={.items[0].metadata.name}")

    def container_ids(self, app):
        """Contenedores de todas las réplicas Running (Docker Desktop: docker ps por etiquetas del Pod)."""
        pods = self.kubectl("get", "pod", "-l", f"app={app}", "--field-selector=status.phase=Running",
                            "-o", "jsonpath={.items[*].metadata.name}").split()
        ids = []
        for pod in pods:
            out = subprocess.run(["docker", "ps", "-q", "--filter", f"label=io.kubernetes.pod.name={pod}",
                                  "--filter", f"label=io.kubernetes.container.name={app}"],
                                 capture_output=True, text=True, check=True).stdout.split()
            if len(out) != 1:
                raise RuntimeError(f"Se esperaba un contenedor para {pod}, hay {len(out)}")
            ids.extend(out)
        if not ids:
            raise RuntimeError(f"No hay Pods Running de {app}")
        return ids

    def load(self, seconds):
        process = subprocess.Popen(["kubectl", "--context", self.context, "-n", NS, "exec", "-i", self.client,
                                    "--", "python", "-", str(seconds)], stdin=subprocess.PIPE, text=True, encoding="utf-8")
        process.stdin.write(LOAD)
        process.stdin.close()
        return process


def log(event, **data):
    print(json.dumps({"ts": now(), "event": event, **data}), flush=True)


def errors(lab, hold, recover):
    """5xx: Pharmacy sin réplicas; el Gateway responde 503 a /api/drug."""
    replicas = lab.kubectl("get", f"deploy/{PHARMACY}", "-o", "jsonpath={.spec.replicas}")
    traffic = lab.load(hold + recover)
    time.sleep(20)  # tráfico sano previo
    log("inject", action="scale pharmacy 0", previous_replicas=replicas)
    try:
        lab.kubectl("scale", f"deploy/{PHARMACY}", "--replicas=0")
        time.sleep(hold)
    finally:
        lab.kubectl("scale", f"deploy/{PHARMACY}", f"--replicas={replicas}")
        log("restore", action=f"scale pharmacy {replicas}")
    lab.kubectl("rollout", "status", f"deploy/{PHARMACY}", "--timeout=180s")
    traffic.wait()


def latency(lab, hold, recover):
    """p95: congela todas las réplicas de Pharmacy 1,5 s de cada 2,5 s; responden 200 pero tarde.

    1,5 s queda por debajo del timeout de 2 s de /health/live, así que el kubelet no reinicia.
    Se congelan todas porque YARP (PowerOfTwoChoices) desvía el tráfico a la réplica libre."""
    containers = lab.container_ids(PHARMACY)
    traffic = lab.load(hold + recover)
    time.sleep(20)
    log("inject", action="pause/unpause pharmacy 1.5s/1.0s", containers=[c[:12] for c in containers])
    end = time.time() + hold
    try:
        while time.time() < end:
            subprocess.run(["docker", "pause", *containers], check=True, capture_output=True)
            time.sleep(1.5)
            subprocess.run(["docker", "unpause", *containers], check=True, capture_output=True)
            time.sleep(1.0)
    finally:
        subprocess.run(["docker", "unpause", *containers], capture_output=True)
        log("restore", action="unpause pharmacy")
    traffic.wait()


def cpu(lab, hold, recover):
    """CPU: dos bucles de shell en el contenedor de Pharmacy (límite 500m)."""
    pod = lab.pod(PHARMACY)
    log("inject", action="busy loops", pod=pod, seconds=hold)
    lab.kubectl("exec", pod, "-c", PHARMACY, "--", "sh", "-c",
                f"for i in 1 2; do timeout {hold} sh -c 'while :; do :; done' & done; wait", check=False)
    log("restore", action="loops ended")
    time.sleep(recover)


def memory(lab, hold, recover):
    """Memoria: dd retiene un bloque hasta ~92 % del límite del contenedor (cgroup v1 o v2).

    dd queda bloqueado escribiendo en un pipe que nadie lee, con el bloque residente."""
    pod = lab.pod(PHARMACY)
    script = ("if [ -f /sys/fs/cgroup/memory.max ]; then limit=$(cat /sys/fs/cgroup/memory.max); "
              "used=$(cat /sys/fs/cgroup/memory.current); else "
              "limit=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes); "
              "used=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes); fi; "
              "add=$(( limit * 92 / 100 - used )); echo limit=$limit used=$used add=$add; "
              f"dd if=/dev/zero bs=$add count=1 2>/dev/null | sleep {int(hold)}; true")
    log("inject", action="hold memory", pod=pod, seconds=hold)
    print(lab.kubectl("exec", pod, "-c", PHARMACY, "--", "sh", "-c", script, check=False))
    log("restore", action="memory released")
    time.sleep(recover)


def ready(lab, hold, recover):
    """Ready: congela SQL; Users y Pharmacy fallan /health/ready y quedan Running sin Ready."""
    containers = lab.container_ids("pharmago-db")
    log("inject", action="pause sql", containers=[c[:12] for c in containers], seconds=hold)
    try:
        subprocess.run(["docker", "pause", *containers], check=True, capture_output=True)
        time.sleep(hold)
    finally:
        subprocess.run(["docker", "unpause", *containers], capture_output=True)
        log("restore", action="unpause sql")
    time.sleep(recover)


SCENARIOS = {"errors": (errors, 100, 60), "latency": (latency, 100, 60), "cpu": (cpu, 130, 90),
             "memory": (memory, 130, 90), "ready": (ready, 80, 90)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", choices=SCENARIOS)
    parser.add_argument("--context", required=True)
    parser.add_argument("--client", default="client", help="Pod con python para generar tráfico")
    parser.add_argument("--hold", type=float)
    parser.add_argument("--recover", type=float)
    args = parser.parse_args()
    run, hold, recover = SCENARIOS[args.scenario]
    log("start", scenario=args.scenario)
    run(Lab(args.context, args.client), args.hold or hold, args.recover or recover)
    log("end", scenario=args.scenario)


if __name__ == "__main__":
    main()
