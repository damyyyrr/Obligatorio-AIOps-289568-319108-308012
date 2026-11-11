"""Resume los eventos de probe-resilience.py por fase (issue #10 / RES-03).

Entrada: un par <nombre>.json (eventos, reloj del pod) y <nombre>.meta.json (marcas de la
falla, reloj del host). Se alinean los relojes con begin (pod) - t_load_host (host).
Fases: antes de la falla, durante la falla y después de restaurar.

Uso:
    python summarize-resilience.py resultados/after-sql-freeze.json [...] --out resumen.json
"""
import argparse
import json
import os
from collections import Counter


def pct(values, q):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]


def phase_stats(events):
    lat = [e["latency_s"] for e in events]
    return {
        "sent": len(events),
        "ok_2xx": sum(1 for e in events if isinstance(e["status"], int) and e["status"] < 300),
        "status": {str(k): v for k, v in sorted(Counter(map(str, (e["status"] for e in events))).items())},
        "p50_s": pct(lat, 0.5), "p95_s": pct(lat, 0.95), "max_s": max(lat) if lat else None,
    }


def summarize(path):
    data = json.load(open(path, encoding="utf-8"))
    meta = json.load(open(path[:-5] + ".meta.json", encoding="utf-8"))
    offset = data["begin"] - meta["t_load_host"]
    fail, restore = meta["t_fail"] + offset, meta["t_restore"] + offset
    events = data["events"]
    result = {"version": meta["version"], "scenario": meta["scenario"],
              "failure_window_s": round(restore - fail, 1),
              "gateway_proxied": meta["gateway_proxied"], "client_requests": len(events),
              "restarts": meta["restarts"], "skipped_inflight_cap": data["skipped_inflight_cap"],
              "paths": {}}
    for route in sorted({e["path"] for e in events}):
        rows = [e for e in events if e["path"] == route]
        after = [e for e in rows if e["t"] >= restore]
        first_ok = next((e["t"] for e in after
                         if isinstance(e["status"], int) and e["status"] < 300), None)
        # Recuperación estable: desde aquí, todas las solicitudes de la ruta fueron 2xx.
        stable = None
        for i, e in enumerate(after):
            if all(isinstance(x["status"], int) and x["status"] < 300 for x in after[i:]):
                stable = e["t"]
                break
        result["paths"][route] = {
            "before": phase_stats([e for e in rows if e["t"] < fail]),
            "during": phase_stats([e for e in rows if fail <= e["t"] < restore]),
            "after": phase_stats(after),
            "first_2xx_after_restore_s": round(first_ok - restore, 1) if first_ok else None,
            "stable_2xx_after_restore_s": round(stable - restore, 1) if stable else None,
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    results = [summarize(p) for p in args.inputs if os.path.exists(p[:-5] + ".meta.json")]
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    for r in results:
        print(f"== {r['version']} / {r['scenario']}  ventana={r['failure_window_s']}s  "
              f"cliente={r['client_requests']} gateway_proxied={r['gateway_proxied']} restarts=[{r['restarts']}]")
        for route, p in r["paths"].items():
            d = p["during"]
            print(f"   {route:10s} durante: {d['status']} max={d['max_s']}s p95={d['p95_s']}s | "
                  f"después: {p['after']['status']} 1er2xx={p['first_2xx_after_restore_s']}s "
                  f"estable={p['stable_2xx_after_restore_s']}s")


if __name__ == "__main__":
    main()
