"""Reconstruye observaciones de #7, sin operar infraestructura ni inventar tiempos."""
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "issue-7-20261110" / "proof.json"
OUTPUT = HERE / "reconstruction.json"


def instant(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("El timestamp debe incluir zona horaria")
    return result


def elapsed(start, end):
    seconds = (instant(end) - instant(start)).total_seconds()
    if seconds < 0:
        raise ValueError("La observación no puede preceder a la inyección")
    return round(seconds, 6)


def reconstruct():
    raw = SOURCE.read_bytes()
    source = json.loads(raw)
    rows = []
    for index, event in enumerate(source["experiments"]):
        fault = event["faultUtc"]
        requests = [r for r in event["requests"] if instant(r["sentUtc"]) >= instant(fault)]
        invalid = sorted((r for r in requests if not r["validResponse"]),
                         key=lambda r: instant(r["receivedUtc"]))
        if not invalid:
            raise ValueError("El caso no contiene una señal funcional de falla")
        detected = invalid[0]["receivedUtc"]
        successes = sorted((r for r in requests if r["validResponse"]
                            and instant(r["receivedUtc"]) > instant(detected)),
                           key=lambda r: instant(r["receivedUtc"]))
        if not successes:
            raise ValueError("El caso no contiene una respuesta válida tras la falla")
        not_ready = next(s for s in event["states"] if not s["ready"]
                         and instant(s["timeUtc"]) >= instant(fault))
        recovered = event["recovered"]
        ready_delay = elapsed(fault, recovered["timeUtc"])
        if not recovered["ready"] or abs(ready_delay - event["readyAgainSeconds"]) > 0.02:
            raise ValueError("La recuperación calculada no coincide con la evidencia original")
        rows.append({
            "app": event["app"], "endpoint": event["endpoint"],
            "sourcePointer": f"/experiments/{index}",
            "tInject": fault,
            "tFirstInvalidResponseObserved": detected,
            "tFirstPodNotReadyObserved": not_ready["timeUtc"],
            "tFirstValidResponseAfterDetection": successes[0]["receivedUtc"],
            "tPodReadyAgainObserved": recovered["timeUtc"],
            "secondsFromInjection": {
                "firstInvalidResponse": elapsed(fault, detected),
                "firstPodNotReady": elapsed(fault, not_ready["timeUtc"]),
                "firstValidResponseAfterDetection": elapsed(fault, successes[0]["receivedUtc"]),
                "podReadyAgain": ready_delay,
            },
            "recordedRequestsIncludingBeforeInjection": len(event["requests"]),
            "validResponsesIncludingBeforeInjection": event["validResponses"],
            "tStartOfUserImpact": None, "tAck": None, "tRepairOfRootCause": None,
            "tRestoreWith120SecondWindow": None, "tVerified": None,
            "ttdFromMeasuredUserImpactSeconds": None, "ttaSeconds": None,
            "ttRestoreSeconds": None,
        })
    if len(rows) != 3:
        raise ValueError("Se esperaban los tres ensayos publicados de #7")
    return {
        "kind": "retrospective-analysis-not-a-new-chaos-run",
        "source": "docs/evidence/issue-7-20261110/proof.json",
        # Hash semántico estable en clones con LF o CRLF; no identifica bytes originales.
        "sourceCanonicalJsonSha256": hashlib.sha256(json.dumps(
            source, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest(),
        "sourceContext": source["context"], "sourceImageTag": source["imageTag"],
        "reference": "faultUtc; injection time, not independently measured user-impact onset",
        "detection": "receipt of first recorded invalid business response after injection; not human acknowledgement or Grafana Firing",
        "limitations": [
            "No new infrastructure operation, human acknowledgement or communication is claimed.",
            "Ready and first successful request are not a sustained service-restoration measurement.",
            "The source does not validate the new 120-second stability policy or all six runbooks.",
            "Missing timestamps and incident intervals remain null; no averages are computed.",
        ],
        "observations": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compara sin escribir archivos")
    args = parser.parse_args()
    result = reconstruct()
    if args.check:
        if json.loads(OUTPUT.read_text(encoding="utf-8")) != result:
            raise SystemExit("FAIL: reconstruction.json difiere de la fuente histórica")
        print("PASS: tres cronologias coinciden con la fuente; tiempos ausentes conservados")
    else:
        OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Escrita reconstruction.json desde la evidencia existente; sin operar infraestructura")


if __name__ == "__main__":
    main()
