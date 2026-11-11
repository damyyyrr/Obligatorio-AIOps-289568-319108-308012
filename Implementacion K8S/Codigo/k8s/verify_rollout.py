"""Bounded functional traffic through ClusterIP during rollout and revision rollback.

Run in a test cluster with the application already healthy. No seed or schema Down.
Requires curl in the stable Elasticsearch pod and PHARMAGO_TEST_PASSWORD locally.
Only sanitized observations are written; no response bodies or credentials.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urlencode

import manage

APPS = ("pharmago-users-service", "pharmago-pharmacy-service", "pharmago-api-gateway")
ROUTES = {"/api/drug": 3, "/api/roles": 3, "/api/login": 8}


def now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    if isinstance(value, list):
        value = sorted(value, key=lambda item: json.dumps(item, sort_keys=True))
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def classify(code, curl_exit, valid):
    if curl_exit == 28:
        return "timeout"
    if curl_exit:
        return "transportError"
    if code != 200:
        return "httpError"
    return "success" if valid else "validationError"


def summarize(samples):
    counts = {key: sum(s["outcome"] == key for s in samples) for key in
              ("success", "httpError", "timeout", "transportError", "validationError")}
    latencies = sorted(s["latencyMs"] for s in samples)
    return {"sent": len(samples), **counts,
            "httpCodes": {str(code): sum(s["http"] == code for s in samples)
                          for code in sorted({s["http"] for s in samples})},
            "latencyMs": {"p50": latencies[math.ceil(len(latencies) * .5) - 1],
                          "p95": latencies[math.ceil(len(latencies) * .95) - 1],
                          "max": max(latencies)} if samples else {}}


class Trial:
    def __init__(self, args):
        self.args = args
        self.cluster = manage.Cluster(args.context)
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.phase = "before"
        self.deadline = time.monotonic() + 900
        self.expected = {}
        self.report = {"startedUtc": now(), "context": args.context, "candidateTag": args.image_tag,
                       "baseCommit": manage.run("git", "rev-parse", "HEAD"),
                       "dirtyTree": bool(manage.run("git", "status", "--porcelain")),
                       "cadenceSeconds": ROUTES, "httpTimeoutSeconds": 2, "retries": 0, "maxTrafficSeconds": 900,
                       "samples": [], "observations": [], "actions": []}

    def kub(self, *args, stdin=None, timeout=35):
        result = subprocess.run(["kubectl", "--context", self.args.context, "-n", "pharmago", *args],
                                input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        if result.returncode:
            # Avoid echoing output from exec commands, which can contain response bodies.
            raise RuntimeError(f"kubectl {args[0]} failed ({result.returncode})")
        return result.stdout

    def get(self, *args):
        return json.loads(self.kub("get", *args, "-o", "json"))

    def curl(self, url, payload=None):
        args = ["exec", "-i", self.client, "-c", "elasticsearch", "--", "curl", "-sS",
                "--max-time", "2", "--write-out", "\n%{http_code} %{time_total}\n"]
        if payload is not None:
            args += ["-H", "Content-Type: application/json", "--data-binary", "@-"]
        result = subprocess.run(["kubectl", "--context", self.args.context, "-n", "pharmago",
                                 *args, url], input=payload, capture_output=True, text=True,
                                encoding="utf-8", timeout=12)
        body, _, status = result.stdout.rstrip("\n").rpartition("\n")
        code, seconds = status.split() if re.fullmatch(r"\d{3} [\d.]+", status) else ("0", "0")
        return int(code), result.returncode, round(float(seconds) * 1000, 3), body

    def sample(self, path):
        sent, phase = now(), self.phase
        payload = json.dumps({"userName": self.args.username, "password": os.environ["PHARMAGO_TEST_PASSWORD"]}) \
            if path == "/api/login" else None
        started = time.monotonic()
        try:
            code, exit_code, latency, body = self.curl(f"http://pharmago-api-gateway{path}", payload)
        except subprocess.TimeoutExpired:
            code, exit_code, latency, body = 0, 28, (time.monotonic() - started) * 1000, ""
        except OSError:
            code, exit_code, latency, body = 0, 125, (time.monotonic() - started) * 1000, ""
        valid = False
        if code == 200 and exit_code == 0:
            try:
                value = json.loads(body)
                if path == "/api/login":
                    valid = bool(value.get("token")) and value.get("userName") == self.args.username
                else:
                    digest = fingerprint(value)
                    valid = isinstance(value, list) and bool(value) and digest == self.expected.get(path)
            except (ValueError, AttributeError, TypeError):
                pass
        return {"sentUtc": sent, "receivedUtc": now(), "phase": phase, "path": path,
                "http": code, "curlExit": exit_code, "latencyMs": round(latency, 3),
                "validResponse": valid, "outcome": classify(code, exit_code, valid)}

    def traffic(self, path, interval):
        deadline = time.monotonic()
        while not self.stop.is_set() and time.monotonic() < self.deadline:
            sample = self.sample(path)
            with self.lock:
                self.report["samples"].append(sample)
            deadline += interval
            self.stop.wait(max(0, deadline - time.monotonic()))

    def observe(self):
        while not self.stop.is_set() and time.monotonic() < self.deadline:
            try:
                pods = self.get("pods")["items"]
                states = []
                for pod in pods:
                    app = pod["metadata"].get("labels", {}).get("app")
                    if app not in APPS:
                        continue
                    states.append({"app": app, "pod": pod["metadata"]["name"], "uid": pod["metadata"]["uid"],
                                   "node": pod["spec"].get("nodeName"), "image": pod["spec"]["containers"][0]["image"],
                                   "terminating": bool(pod["metadata"].get("deletionTimestamp")),
                                   "ready": any(c["type"] == "Ready" and c["status"] == "True"
                                                for c in pod["status"].get("conditions", [])),
                                   "containers": [{"imageID": c.get("imageID"), "restarts": c["restartCount"]}
                                                  for c in pod["status"].get("containerStatuses", [])]})
                slices = self.get("endpointslices")["items"]
                endpoints = [{"service": s["metadata"]["labels"].get("kubernetes.io/service-name"),
                              "endpoints": [{"pod": e.get("targetRef", {}).get("name"),
                                             "conditions": e.get("conditions")} for e in s.get("endpoints", [])]}
                             for s in slices if s["metadata"]["labels"].get("kubernetes.io/service-name") in APPS]
                with self.lock:
                    self.report["observations"].append({"timeUtc": now(), "phase": self.phase,
                                                        "pods": states, "endpointSlices": endpoints})
            except Exception as exc:
                with self.lock:
                    self.report.setdefault("observerErrors", []).append(type(exc).__name__)
            self.stop.wait(2)

    def snapshot(self):
        sqlcmd = ('export SQLCMDPASSWORD="$MSSQL_SA_PASSWORD"; '
                  'exec /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -C -b -h -1 -W -w 65535')
        query = ("SET NOCOUNT ON; USE PharmaDb; SELECT MigrationId FROM dbo.__EFMigrationsHistory ORDER BY MigrationId; "
                 "SELECT Id,Code,Stock,Price,Deleted FROM dbo.Drugs ORDER BY Id; "
                 "SELECT Id,UserName FROM dbo.Users ORDER BY Id;")
        data = self.kub("exec", "-i", "deployment/pharmago-db", "--", "sh", "-c", sqlcmd, stdin=query)
        return {"businessAndSchemaSha256": hashlib.sha256(data.encode()).hexdigest(),
                "migrationIds": [line.strip() for line in data.splitlines() if line.strip()[:14].isdigit()],
                "sqlPodUids": [p["metadata"]["uid"] for p in self.get("pods", "-l", "app=pharmago-db")["items"]],
                "volumes": self.cluster.volumes()}

    def metrics(self):
        expr = ('sum by(service_name,pod,endpoint,status_code) (pharmago_http_requests_total'
                '{job="otlp-collector",namespace="pharmago",endpoint=~"/api/(drug|roles|login)"})')
        code, error, _, body = self.curl("http://prometheus:9090/api/v1/query?" + urlencode({"query": expr}))
        if code != 200 or error:
            raise RuntimeError("Prometheus query failed")
        return json.loads(body)["data"]["result"]

    def wait(self, app):
        self.kub("rollout", "status", f"deployment/{app}", "--timeout=240s", timeout=260)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            pods = self.get("pods", "-l", f"app={app}")["items"]
            if not any(p["metadata"].get("deletionTimestamp") for p in pods):
                return
            time.sleep(1)
        raise RuntimeError(f"Terminating pods did not drain: {app}")

    def save(self):
        self.args.output.parent.mkdir(parents=True, exist_ok=True)
        self.args.output.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")

    def run(self):
        self.cluster.preflight()
        deployments = {app: self.get("deployment", app) for app in APPS}
        for app, doc in deployments.items():
            if doc["spec"]["template"]["spec"]["containers"][0]["image"].endswith(":" + self.args.image_tag):
                raise RuntimeError(f"Candidate already deployed: {app}")
            self.wait(app)
        self.client = "pod/" + self.get("pods", "-l", "app=elasticsearch")["items"][0]["metadata"]["name"]
        for path in ("/api/drug", "/api/roles"):
            code, error, _, body = self.curl("http://pharmago-api-gateway" + path)
            value = json.loads(body)
            if code != 200 or error or not isinstance(value, list) or not value:
                raise RuntimeError("Functional baseline failed")
            self.expected[path] = fingerprint(value)
        if self.sample("/api/login")["outcome"] != "success":
            raise RuntimeError("Login baseline failed")
        self.report["before"] = self.snapshot()
        self.report["deploymentsBefore"] = {app: {"revision": d["metadata"]["annotations"]["deployment.kubernetes.io/revision"],
                                                    "image": d["spec"]["template"]["spec"]["containers"][0]["image"],
                                                    "replicas": d["spec"]["replicas"]} for app, d in deployments.items()}
        self.report["metricsBefore"] = self.metrics()
        changed = []
        failure = None
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self.traffic, path, interval) for path, interval in ROUTES.items()]
            futures.append(pool.submit(self.observe))
            try:
                time.sleep(20)
                docs = {d["metadata"]["name"]: d for d in manage.resources(self.args.image_tag) if d["kind"] == "Deployment"}
                self.phase = "migration"
                self.report["migrationJob"] = self.cluster.migrate(docs[APPS[0]], 180)
                for app in APPS:
                    self.phase = "rollout:" + app
                    action = {"phase": self.phase, "startUtc": now()}
                    changed.append(app)
                    # Only the three application Deployments are replaced. SQL/UI/telemetry remain unchanged.
                    self.kub("apply", "-f", "-", stdin=json.dumps(docs[app]))
                    self.wait(app)
                    action["endUtc"] = now()
                    self.report["actions"].append(action)
                    self.save()
                self.phase = "after-rollout"
                time.sleep(20)
                self.report["afterRollout"] = self.snapshot()
            except (Exception, KeyboardInterrupt) as exc:
                failure = type(exc).__name__ + ": " + str(exc)
            finally:
                # Restore exact saved application revisions, including on an interrupted/failed candidate.
                for app in reversed(changed):
                    self.phase = "rollback:" + app
                    action = {"phase": self.phase, "startUtc": now()}
                    try:
                        revision = self.report["deploymentsBefore"][app]["revision"]
                        self.kub("rollout", "undo", f"deployment/{app}", f"--to-revision={revision}")
                        self.wait(app)
                        restored = self.get("deployment", app)
                        if restored["spec"]["template"] != deployments[app]["spec"]["template"]:
                            raise RuntimeError("Rollback template mismatch")
                        action.update(endUtc=now(), restoredTemplate=True)
                    except Exception as exc:
                        action["error"] = type(exc).__name__ + ": " + str(exc)
                        failure = failure or action["error"]
                    self.report["actions"].append(action)
                self.phase = "after-rollback"
                time.sleep(20)
                self.stop.set()
                for future in futures:
                    try:
                        future.result()
                    except Exception as exc:
                        failure = failure or type(exc).__name__
        self.report["afterRollback"] = self.snapshot()
        self.report["metricsAfter"] = self.metrics()
        self.report["endedUtc"] = now()
        samples = self.report["samples"]
        self.report["summary"] = summarize(samples)
        self.report["trafficWindowSeconds"] = round((datetime.fromisoformat(max(s["receivedUtc"] for s in samples))
                                                     - datetime.fromisoformat(min(s["sentUtc"] for s in samples))).total_seconds(), 3)
        self.report["byPhase"] = {phase: summarize([s for s in samples if s["phase"] == phase])
                                  for phase in sorted({s["phase"] for s in samples})}
        self.report["byRoute"] = {path: summarize([s for s in samples if s["path"] == path]) for path in ROUTES}
        self.report["coexistence"] = {app: any(len({p["image"] for p in o["pods"]
                                                  if p["app"] == app and p["ready"] and not p["terminating"]}) == 2
                                             for o in self.report["observations"]) for app in APPS}
        expected_phases = {"before", "migration", "after-rollout", "after-rollback"} | {
            direction + ":" + app for direction in ("rollout", "rollback") for app in APPS}
        # A fast no-op migration may finish between requests, so its phase is optional.
        expected_phases.remove("migration")
        self.report["passed"] = (not failure and not self.report.get("observerErrors")
                                 and time.monotonic() < self.deadline
                                 and expected_phases <= self.report["byPhase"].keys()
                                 and len(changed) == 3 and all(self.report["coexistence"].values())
                                 and self.report["summary"]["success"] == len(samples) and bool(samples)
                                 and self.report["before"] == self.report.get("afterRollout") == self.report["afterRollback"])
        if failure:
            self.report["failure"] = failure
        self.save()
        print(json.dumps({"passed": self.report["passed"], **self.report["summary"]}))
        return 0 if self.report["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--image-tag", required=True, type=manage.tag_value)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("PHARMAGO_TEST_PASSWORD"):
        parser.error("Set PHARMAGO_TEST_PASSWORD for an existing test user")
    trial = Trial(args)
    try:
        return trial.run()
    except Exception as exc:
        trial.report.update(passed=False, failure=type(exc).__name__ + ": " + str(exc), endedUtc=now())
        trial.save()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
