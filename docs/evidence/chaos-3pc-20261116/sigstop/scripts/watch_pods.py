"""Registra cada ~1 s Ready, nodo, UID y reinicios de los pods de Gateway, Users y Pharmacy."""
import json, subprocess, sys, time

KUBE = ["kubectl", "--kubeconfig", r"C:\Users\vicen\.kube\pharmago-hamachi.yaml", "--context", "pharmago-hamachi", "-n", "pharmago"]
APPS = ("pharmago-api-gateway", "pharmago-users-service", "pharmago-pharmacy-service")
out, end = open(sys.argv[1], "a", encoding="utf8"), time.time() + float(sys.argv[2])
while time.time() < end:
    t = time.time()
    try:
        items = json.loads(subprocess.run(KUBE + ["get", "pods", "-o", "json"], capture_output=True, text=True, timeout=10).stdout)["items"]
        pods = [{"app": p["metadata"]["labels"].get("app"), "pod": p["metadata"]["name"], "uid": p["metadata"]["uid"],
                 "node": p["spec"].get("nodeName"),
                 "ready": any(c["type"] == "Ready" and c["status"] == "True" for c in p["status"].get("conditions", [])),
                 "restarts": sum(c.get("restartCount", 0) for c in p["status"].get("containerStatuses", []))}
                for p in items if p["metadata"]["labels"].get("app") in APPS]
        out.write(json.dumps({"t": round(t, 3), "pods": pods}) + "\n"); out.flush()
    except Exception as e:  # noqa: BLE001
        out.write(json.dumps({"t": round(t, 3), "error": str(e)[:200]}) + "\n"); out.flush()
    time.sleep(max(0, 1 - (time.time() - t)))
