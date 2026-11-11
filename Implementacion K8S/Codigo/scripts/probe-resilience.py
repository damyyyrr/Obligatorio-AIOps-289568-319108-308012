"""Carga acotada para medir timeouts y contención de fallas (issue #10 / RES-03).

Lanza solicitudes GET a ritmo fijo contra una o más rutas durante --duration segundos.
Cada solicitud corre en su propio hilo, así una dependencia colgada no frena el ritmo
de envío. Registra inicio (epoch), latencia y estado de cada solicitud.
Estados: código HTTP, "timeout" (supera --client-timeout) o "error" (fallo de transporte).
Solo usa GET: nunca reintenta ni envía escrituras.

Uso:
    python probe-resilience.py --base http://pharmago-api-gateway --path /api/drug \
        --path /api/roles --rate 4 --duration 110 --out events.json
"""
import argparse
import json
import socket
import threading
import time
import urllib.error
import urllib.request


def one(url, client_timeout, events, lock):
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=client_timeout) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except (socket.timeout, TimeoutError):
        status = "timeout"
    except urllib.error.URLError as error:
        status = "timeout" if isinstance(error.reason, (socket.timeout, TimeoutError)) else "error"
    except Exception:  # noqa: BLE001 - se clasifica como error de transporte
        status = "error"
    with lock:
        events.append({"t": round(started, 3), "path": url.split("/", 3)[-1],
                       "status": status, "latency_s": round(time.time() - started, 3)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--rate", type=float, default=4.0, help="solicitudes por segundo en total")
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--client-timeout", type=float, default=120.0)
    parser.add_argument("--max-inflight", type=int, default=400)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    events, lock, threads = [], threading.Lock(), []
    begin = time.time()
    interval = 1.0 / args.rate
    i = 0
    skipped = 0
    while time.time() - begin < args.duration:
        target = begin + i * interval
        delay = target - time.time()
        if delay > 0:
            time.sleep(delay)
        threads = [t for t in threads if t.is_alive()]
        if len(threads) >= args.max_inflight:
            skipped += 1
        else:
            url = args.base + args.path[i % len(args.path)]
            thread = threading.Thread(target=one, args=(url, args.client_timeout, events, lock), daemon=True)
            thread.start()
            threads.append(thread)
        i += 1
    for thread in threads:
        thread.join(args.client_timeout + 5)

    events.sort(key=lambda e: e["t"])
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({"begin": begin, "rate": args.rate, "duration": args.duration,
                   "client_timeout": args.client_timeout, "skipped_inflight_cap": skipped,
                   "events": events}, handle)
    print(json.dumps({"sent": len(events), "skipped": skipped}))


if __name__ == "__main__":
    main()
