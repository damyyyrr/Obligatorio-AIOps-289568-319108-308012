"""Reparte solicitudes en round-robin entre varias réplicas del Gateway y cuenta 200/404 vs 429.

Sirve para mostrar que el contador es local a cada réplica: con N réplicas y balanceo
uniforme, un mismo cliente obtiene hasta N × límite por ventana.

Uso:
    python probe-rate-limit-replicas.py --base http://127.0.0.1:5099 --base http://127.0.0.1:5100 \
        --count 300 --out result.json
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict


def send(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", action="append", required=True)
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--path", default="/api/drug")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    per_replica = defaultdict(Counter)
    started = time.time()
    for i in range(args.count):
        base = args.base[i % len(args.base)]
        per_replica[base][send(base + args.path)] += 1
    elapsed = time.time() - started

    total = Counter()
    for counts in per_replica.values():
        total.update(counts)
    result = {
        "replicas": len(args.base),
        "sent": args.count,
        "elapsed_s": round(elapsed, 2),
        "passed_limiter": sum(v for k, v in total.items() if k != 429),
        "rejected_429": total.get(429, 0),
        "per_replica": {
            base: {
                "passed_limiter": sum(v for k, v in c.items() if k != 429),
                "rejected_429": c.get(429, 0),
            }
            for base, c in per_replica.items()
        },
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
