"""Dataset sintético docente: celda 4 de practico_detectores_aiops.ipynb.

Se conserva el orden de las operaciones y de la RNG; el test de procedencia compara
cada valor con la celda original. Las fechas son sintéticas y no tienen zona horaria.
"""
import numpy as np
import pandas as pd

SEED = 42
FEATURES = ("requests", "error_rate", "latency_ms", "cpu_pct")


def generate_dataset(seed=SEED):
    rng = np.random.default_rng(seed)
    minutes = pd.date_range("2026-06-03 08:00", periods=300, freq="min")
    n = len(minutes)
    hour = minutes.hour.to_numpy() + minutes.minute.to_numpy() / 60.0
    # Misma familia de trafico que clases 10-11: rampa matinal, no un salto de regimen.
    traffic = 70 + 90 * np.clip(np.sin((hour - 8) * np.pi / 6), 0, None)
    requests = np.maximum(25, np.rint(traffic + rng.normal(0, 8, n))).astype(float)
    error_rate = np.clip(0.0035 + 0.000045 * requests + rng.normal(0, 0.0010, n), 0.0008, None)
    latency_ms = np.clip(68 + 0.22 * requests + rng.normal(0, 6.5, n), 40, None)
    cpu_pct = np.clip(16 + 0.17 * requests + rng.normal(0, 4.0, n), 8, None)

    kind = np.full(n, "normal", dtype=object)


    def window(start, end):
        return np.asarray((minutes >= start) & (minutes < end))


    # Job batch legitimo: CPU alto, el resto sigue el manifold. NO es incidente.
    for start in ("2026-06-03 08:25", "2026-06-03 09:12", "2026-06-03 10:30", "2026-06-03 11:42"):
        m = window(start, pd.Timestamp(start) + pd.Timedelta(minutes=5))
        kind[m] = "batch"
        cpu_pct[m] = rng.uniform(70, 84, m.sum())
        requests[m] = np.maximum(25, requests[m] - rng.integers(8, 14, m.sum()))
        error_rate[m] = np.clip(0.0035 + 0.000045 * requests[m] + rng.normal(0, 0.0008, m.sum()), 0.0008, None)
        latency_ms[m] = np.clip(68 + 0.22 * requests[m] + rng.normal(0, 5.0, m.sum()), 40, None)

    # Spikes univariados de error_rate: contaminan media y sigma, casi no mueven al MAD.
    for ts in ("2026-06-03 08:18", "2026-06-03 08:41", "2026-06-03 09:05"):
        m = window(ts, pd.Timestamp(ts) + pd.Timedelta(minutes=1))
        kind[m] = "spike_error"
        error_rate[m] = rng.uniform(0.021, 0.025, m.sum())

    # Incidente clasico (combinacion rara): poco trafico, mucho error, latencia alta.
    m = window("2026-06-03 09:50", "2026-06-03 09:58")
    kind[m] = "incidente_5xx"
    requests[m] = rng.integers(30, 44, m.sum())
    error_rate[m] = rng.uniform(0.036, 0.048, m.sum())
    latency_ms[m] = rng.uniform(210, 260, m.sum())
    cpu_pct[m] = rng.uniform(28, 40, m.sum())

    # Timeouts: trafico medio, error y latencia altos.
    m = window("2026-06-03 09:22", "2026-06-03 09:26")
    kind[m] = "timeouts"
    error_rate[m] = rng.uniform(0.023, 0.028, m.sum())
    latency_ms[m] = rng.uniform(175, 200, m.sum())

    # Pico de carga sobre el manifold: extremo en un eje, relacion habitual.
    m = window("2026-06-03 11:18", "2026-06-03 11:26")
    kind[m] = "pico_carga"
    requests[m] = rng.integers(165, 185, m.sum())
    error_rate[m] = 0.0035 + 0.000045 * requests[m] + rng.normal(0, 0.0007, m.sum())
    latency_ms[m] = 68 + 0.22 * requests[m] + rng.normal(0, 5.0, m.sum())
    cpu_pct[m] = 16 + 0.17 * requests[m] + rng.normal(0, 3.5, m.sum())

    # Latencia silenciosa: solo un eje se rompe.
    m = window("2026-06-03 10:40", "2026-06-03 10:46")
    kind[m] = "latencia_silenciosa"
    latency_ms[m] = rng.uniform(195, 230, m.sum())

    # Combinacion sutil: poco trafico + error alto, pero cada eje crudo queda bajo 3 MAD.
    # Es un incidente_5xx atenuado: se ve en el plano, no en un histograma.
    m = window("2026-06-03 10:08", "2026-06-03 10:15")
    kind[m] = "combo_sutil"
    requests[m] = rng.integers(50, 62, m.sum())
    error_rate[m] = rng.uniform(0.0132, 0.0140, m.sum())
    latency_ms[m] = rng.uniform(118, 128, m.sum())
    cpu_pct[m] = 16 + 0.17 * requests[m] + rng.normal(0, 3.5, m.sum())

    # Degradacion colectiva: la latencia sube de a poco. El primer minuto casi no se ve.
    m = window("2026-06-03 11:50", "2026-06-03 12:08")
    kind[m] = "degradacion"
    ramp = np.linspace(8, 95, m.sum())
    latency_ms[m] = latency_ms[m] + ramp

    # Degradacion parcial: CPU y latencia, sin errores.
    m = window("2026-06-03 12:22", "2026-06-03 12:27")
    kind[m] = "cpu_latencia"
    cpu_pct[m] = rng.uniform(78, 90, m.sum())
    latency_ms[m] = rng.uniform(180, 215, m.sum())

    # Micro-burst: facil para todos.
    m = window("2026-06-03 12:41", "2026-06-03 12:43")
    kind[m] = "micro_burst"
    error_rate[m] = rng.uniform(0.055, 0.070, m.sum())
    latency_ms[m] = rng.uniform(240, 280, m.sum())

    anomalous_kinds = {
        "spike_error", "incidente_5xx", "timeouts", "latencia_silenciosa",
        "combo_sutil", "degradacion", "cpu_latencia", "micro_burst",
    }
    data = pd.DataFrame({
        "timestamp": minutes,
        "requests": requests,
        "error_rate": error_rate,
        "latency_ms": latency_ms,
        "cpu_pct": cpu_pct,
        "kind": kind,
    })
    data["is_anomaly"] = data["kind"].isin(anomalous_kinds)

    return data
