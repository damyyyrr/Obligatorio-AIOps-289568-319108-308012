"""Analiza una medición SIGSTOP: tiempo desde la suspensión hasta que la dotación vuelve a Ready, y conteo de sondas."""
import json, sys

probe_f, pods_f, stop_ts, app, path = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
probes = [json.loads(l) for l in open(probe_f, encoding="utf8") if l.startswith("{")]
pods = [json.loads(l) for l in open(pods_f, encoding="utf8") if l.startswith("{")]
snaps = [s for s in pods if "pods" in s]

base = [s for s in snaps if s["t"] < stop_ts]
want = len([p for p in base[-1]["pods"] if p["app"] == app and p["ready"]]) if base else 1
went_down = ready_back = None
for s in snaps:
    if s["t"] < stop_ts:
        continue
    ready = len([p for p in s["pods"] if p["app"] == app and p["ready"]])
    if went_down is None and ready < want:
        went_down = s["t"]
    if went_down is not None and ready >= want:
        ready_back = s["t"]
        break
restarts = {p["pod"]: p["restarts"] for p in snaps[-1]["pods"] if p["app"] == app}
sel = [p for p in probes if p["path"] == path]
ok = sum(1 for p in sel if p["http"] == 200 and p["valid"])
noresp = sum(1 for p in sel if p["http"] == 0)
win = [p for p in sel if stop_ts <= p["t"] <= (ready_back or 1e12)]
def cnt(xs):
    a = sum(1 for p in xs if p["http"] == 200 and p["valid"]); b = sum(1 for p in xs if p["http"] == 0)
    return {"total": len(xs), "valid": a, "no_response": b, "other": len(xs) - a - b}
first_fail = next((p["t"] for p in sel if p["t"] >= stop_ts and not (p["http"] == 200 and p["valid"])), None)
last_fail = max((p["t"] for p in sel if not (p["http"] == 200 and p["valid"])), default=None)
print(json.dumps({"window_stop_to_ready": cnt(win), "whole_run": cnt(sel),
                  "first_fail_after_s": None if first_fail is None else round(first_fail - stop_ts, 2),
                  "last_fail_after_s": None if last_fail is None else round(last_fail - stop_ts, 2)}))
print(json.dumps({"app": app, "path": path, "replicas_ready_before": want,
                  "notready_after_s": None if went_down is None else round(went_down - stop_ts, 2),
                  "ready_after_s": None if ready_back is None else round(ready_back - stop_ts, 2),
                  "probes_total": len(sel), "probes_valid": ok, "probes_no_response": noresp,
                  "probes_other": len(sel) - ok - noresp, "restarts_end": restarts}, indent=1))
