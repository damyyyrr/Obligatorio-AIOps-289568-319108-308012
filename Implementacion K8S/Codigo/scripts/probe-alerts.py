"""Registra las transiciones de estado de las reglas de Grafana (issue #13).

Consulta /api/prometheus/grafana/api/v1/rules cada --every segundos y escribe una línea JSON
por cambio (regla, estado previo, estado nuevo, hora UTC y valores de las instancias).
Uso (dentro del clúster, contraseña de admin por variable de entorno):
    GRAFANA_PASSWORD=... python probe-alerts.py --grafana http://grafana:3000 --seconds 1200 --out alerts.jsonl
"""
import argparse
import base64
import datetime
import json
import os
import time
import urllib.request


def fetch(base, auth):
    request = urllib.request.Request(f"{base}/api/prometheus/grafana/api/v1/rules",
                                     headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(request, timeout=10) as response:
        groups = json.load(response)["data"]["groups"]
    states = {}
    for group in groups:
        for rule in group["rules"]:
            alerts = [{"state": a["state"], "labels": {k: v for k, v in a["labels"].items()
                                                         if k in ("pod", "container", "service_name")},
                       "value": a.get("value")} for a in rule.get("alerts", [])]
            # Normal/Pending/Alerting/NoData/Error a nivel de instancia; firing/pending/inactive a nivel de regla.
            states[rule["name"]] = {"state": rule["state"], "health": rule.get("health"), "alerts": alerts}
    return states


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grafana", required=True)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument("--every", type=float, default=5)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    auth = base64.b64encode(f"{args.user}:{os.environ['GRAFANA_PASSWORD']}".encode()).decode()

    previous = {}
    deadline = time.time() + args.seconds
    with open(args.out, "a", encoding="utf-8") as handle:
        while time.time() < deadline:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            try:
                states = fetch(args.grafana, auth)
            except Exception as error:  # noqa: BLE001 - registrar y seguir
                handle.write(json.dumps({"ts": now, "error": str(error)}) + "\n")
                handle.flush()
                time.sleep(args.every)
                continue
            for name, current in states.items():
                key = (current["state"], current["health"])
                if previous.get(name) != key:
                    handle.write(json.dumps({"ts": now, "rule": name, "from": previous.get(name, (None,))[0],
                                             "to": current["state"], "health": current["health"],
                                             "alerts": current["alerts"]}, ensure_ascii=False) + "\n")
                    handle.flush()
                    print(f"{now} {name}: {previous.get(name, (None,))[0]} -> {current['state']} ({current['health']})")
                    previous[name] = key
            time.sleep(args.every)


if __name__ == "__main__":
    main()
