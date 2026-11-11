"""Envía una solicitud con un traceparent W3C conocido y la busca por trace ID en Jaeger (issue #11).

Uso (dentro del clúster):
    python probe-trace.py --base http://pharmago-api-gateway --path /api/drug \
        --jaeger http://jaeger:16686 --out trace.json
Imprime el trace ID, el estado HTTP y el árbol de spans (servicio, operación, duración, error).
"""
import argparse
import json
import secrets
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--method", default="GET")
    parser.add_argument("--jaeger", required=True)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    trace_id = secrets.token_hex(16)
    traceparent = f"00-{trace_id}-{secrets.token_hex(8)}-01"
    request = urllib.request.Request(args.base + args.path, method=args.method,
                                     headers={"traceparent": traceparent})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except Exception as error:  # noqa: BLE001
        status = type(error).__name__
    elapsed = round(time.time() - started, 3)

    trace = None
    for _ in range(30):  # el Collector agrupa cada 5 s; Jaeger indexa enseguida
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"{args.jaeger}/api/traces/{trace_id}", timeout=5) as response:
                data = json.load(response)["data"]
                if data and len(data[0]["spans"]) >= 3:
                    trace = data[0]
                    time.sleep(6)  # dar tiempo a spans rezagados del mismo lote
                    with urllib.request.urlopen(f"{args.jaeger}/api/traces/{trace_id}", timeout=5) as again:
                        trace = json.load(again)["data"][0]
                    break
        except urllib.error.HTTPError:
            pass

    spans = []
    if trace:
        services = {pid: p["serviceName"] for pid, p in trace["processes"].items()}
        for span in sorted(trace["spans"], key=lambda s: s["startTime"]):
            tags = {t["key"]: t["value"] for t in span.get("tags", [])}
            parent = next((r["spanID"] for r in span.get("references", []) if r["refType"] == "CHILD_OF"), None)
            spans.append({
                "span_id": span["spanID"], "parent": parent, "service": services[span["processID"]],
                "operation": span["operationName"], "duration_ms": round(span["duration"] / 1000, 1),
                "kind": tags.get("span.kind"), "http_status": tags.get("http.status_code"),
                "error": tags.get("error", False) or tags.get("otel.status_code") == "ERROR",
                "db": tags.get("db.system"),
            })
    result = {"trace_id": trace_id, "http_status": status, "client_elapsed_s": elapsed,
              "found_in_jaeger": trace is not None, "span_count": len(spans), "spans": spans}
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"trace_id={trace_id} http={status} t={elapsed}s jaeger={'OK' if trace else 'NO'} spans={len(spans)}")
    for span in spans:
        mark = " ERROR" if span["error"] else ""
        print(f"  {span['service']:26s} {str(span['kind']):7s} {span['operation'][:40]:40s} "
              f"{span['duration_ms']:>8} ms http={span['http_status']} db={span['db']}{mark}")


if __name__ == "__main__":
    main()
