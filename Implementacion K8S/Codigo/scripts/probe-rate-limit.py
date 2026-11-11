"""Sondeo funcional del rate limiting del API Gateway (issue #9 / RES-02).

Envía ráfagas contra un Gateway en ejecución y cuenta cuántas solicitudes atraviesan el
limitador (cualquier código distinto de 429) frente a cuántas reciben 429. No necesita
los microservicios: con upstreams caídos el Gateway responde 502, lo que igualmente
prueba que la solicitud superó el limitador.

Uso:
    python probe-rate-limit.py --base http://127.0.0.1:5099 --mode IP --out result.json
"""
import argparse
import concurrent.futures
import json
import urllib.error
import urllib.request
import uuid
from collections import Counter

PATH = "/api/drug"


def send(base, headers=None, method="GET", path=PATH):
    request = urllib.request.Request(base + path, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers)


def scenario(name, base, count, header_factory, method="GET", path=PATH):
    statuses = Counter()
    retry_after = None
    for i in range(count):
        status, headers = send(base, header_factory(i), method, path)
        statuses[status] += 1
        if status == 429 and retry_after is None:
            retry_after = headers.get("Retry-After")
    passed = sum(v for k, v in statuses.items() if k != 429)
    return {
        "scenario": name,
        "sent": count,
        "passed_limiter": passed,
        "rejected_429": statuses.get(429, 0),
        "status_counts": {str(k): v for k, v in sorted(statuses.items())},
        "first_retry_after": retry_after,
    }


def rotating_paths(base, count):
    statuses = Counter(send(base, path=f"{PATH}/{i}")[0] for i in range(count))
    return {
        "scenario": "rotating_paths",
        "sent": count,
        "passed_limiter": sum(v for k, v in statuses.items() if k != 429),
        "rejected_429": statuses.get(429, 0),
        "status_counts": {str(k): v for k, v in sorted(statuses.items())},
    }


def burst(base, count, headers):
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
        results = list(pool.map(lambda _: send(base, headers)[0], range(count)))
    statuses = Counter(results)
    return {
        "scenario": "concurrent_burst_single_token",
        "sent": count,
        "passed_limiter": sum(v for k, v in statuses.items() if k != 429),
        "rejected_429": statuses.get(429, 0),
        "status_counts": {str(k): v for k, v in sorted(statuses.items())},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--mode", required=True, choices=["IP", "User"])
    parser.add_argument("--label", default="")
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--scenario", default=None, help="ejecutar solo este escenario")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    status, _ = send(args.base, path="/health/live")
    results = {"label": args.label, "mode": args.mode, "health_live": status, "scenarios": []}

    # Cada escenario debería ejecutarse contra un Gateway recién iniciado (contadores vacíos):
    # todos salen de la misma IP real y, si el mecanismo es correcto, comparten bucket.
    c = args.count
    scenarios = {
        "baseline_no_headers": lambda: scenario("baseline_no_headers", args.base, c, lambda i: {}),
        "spoof_x_real_ip_rotating": lambda: scenario(
            "spoof_x_real_ip_rotating", args.base, c, lambda i: {"X-Real-IP": f"198.51.100.{i % 250}"}),
        "spoof_x_forwarded_for_rotating": lambda: scenario(
            "spoof_x_forwarded_for_rotating", args.base, c, lambda i: {"X-Forwarded-For": f"203.0.113.{i % 250}"}),
        "spoof_x_user_id_rotating": lambda: scenario(
            "spoof_x_user_id_rotating", args.base, c, lambda i: {"X-User-Id": f"victim-{i}"}),
        "rotating_random_tokens": lambda: scenario(
            "rotating_random_tokens", args.base, c * 3, lambda i: {"Authorization": f"Bearer {uuid.uuid4()}"}),
        "rotating_paths": lambda: rotating_paths(args.base, c),
        "login_bruteforce": lambda: scenario(
            "login_bruteforce", args.base, 30, lambda i: {"Content-Type": "application/json"},
            method="POST", path="/api/login"),
        "concurrent_burst_single_token":lambda: burst(args.base, 200, {"Authorization": "Bearer burst-session"}),
    }
    selected = [args.scenario] if args.scenario else list(scenarios)
    results["scenarios"] = [scenarios[name]() for name in selected]
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
