"""Crea (si no existe) la vista de datos de Kibana para los logs de PharmaGo (issue #12).

Fluent Bit escribe en índices diarios pharmago-logs-YYYY.MM.DD con @timestamp.
Es idempotente: si la vista ya existe, no hace nada.

Uso (con port-forward a Kibana o desde un pod del clúster):
    python kibana-data-view.py --kibana http://127.0.0.1:5601
"""
import argparse
import json
import urllib.error
import urllib.request

DATA_VIEW_ID = "pharmago-logs"


def call(method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"kbn-xsrf": "pharmago", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kibana", required=True)
    args = parser.parse_args()
    base = args.kibana.rstrip("/")

    try:
        call("GET", f"{base}/api/data_views/data_view/{DATA_VIEW_ID}")
        print(f"La vista {DATA_VIEW_ID} ya existe.")
        return
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise

    status, _ = call("POST", f"{base}/api/data_views/data_view", {
        "data_view": {"id": DATA_VIEW_ID, "name": "PharmaGo logs", "title": "pharmago-logs-*",
                      "timeFieldName": "@timestamp"},
    })
    print(f"Vista {DATA_VIEW_ID} creada (HTTP {status}).")


if __name__ == "__main__":
    main()
