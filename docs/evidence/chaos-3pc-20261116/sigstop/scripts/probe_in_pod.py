"""Corre dentro de un pod: GET catálogo y POST login por el Gateway cada ~1 s. Salida JSON por línea.
No imprime tokens ni cuerpos: solo código, latencia y validez."""
import json, os, sys, time, urllib.request, urllib.error, socket

BASE = "http://pharmago-api-gateway"
PWD = sys.stdin.readline().strip()  # la contraseña llega por stdin, no por argumentos
END = time.time() + float(os.environ.get("DURATION", "900"))


def call(path, body=None):
    t0 = time.time()
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST" if body else "GET")
    code, valid = 0, False
    try:
        with urllib.request.urlopen(req, timeout=2) as r:
            code = r.status
            data = json.loads(r.read() or b"null")
            valid = bool(data) and (isinstance(data, list) if body is None else bool(data.get("token")))
    except urllib.error.HTTPError as e:
        code = e.code
    except (socket.timeout, TimeoutError, urllib.error.URLError, ConnectionError, ValueError):
        code = 0
    return {"t": round(t0, 3), "path": path, "http": code, "valid": valid, "ms": round((time.time() - t0) * 1000, 1)}


i = 0
while time.time() < END:
    start = time.time()
    recs = [call("/api/drug"), call("/api/roles")]
    if i % 4 == 0:  # login cada ~8 s para quedar bajo la cuota de rate limiting
        recs.append(call("/api/login", {"userName": "admin", "password": PWD}))
    i += 1
    for rec in recs:
        print(json.dumps(rec), flush=True)
    time.sleep(max(0, 2 - (time.time() - start)))
