# Caos sobre tres PCs físicas — 16/11/2026

Ejecución de los seis escenarios del controlador de caos con **Gateway, Users y Pharmacy en tres computadoras físicas distintas**, una por integrante. Código en `ae24ebe` (`obligatorio`), árbol limpio, imágenes `k8s-20261116-01`. Resultado: **seis categorías PASS con limpieza verificada**. `network` aprobó en su segundo intento; el primero dio FAIL por un corte de conectividad de la PC A, ajeno al código (ver más abajo).

## Topología

| Nodo k3s | PC | RAM física | Etiquetas | Pods de servicio |
|---|---|---|---|---|
| `pharmago-a` (server) | Integrante 1 | 16 GB | `node-type=ops`, `pharmago.io/service=gateway` | Gateway, SQL, Elasticsearch, Prometheus, Grafana, Jaeger, Collector |
| `pharmago-b` (agent) | Integrante 2 | 16 GB | `node-type=frontend`, `pharmago.io/service=users` | Users ×2, UI, Kibana |
| `pharmago-c` (agent) | Integrante 3 | 8 GB | `pharmago.io/service=pharmacy` | Pharmacy ×2, clientes de caos |

Fluent Bit, node-exporter y kubelet-storage corren como DaemonSet en los tres. Cada nodo es k3s `v1.34.1+k3s1` dentro de Ubuntu 24.04 en WSL2 (kernel 6.18, red *mirrored*). Ver `nodes.json`, `nodes.txt` y `pods.txt`. La request de catálogo recorre las tres PCs: Gateway (A) → Pharmacy (C) → SQL (A); login y roles: Gateway (A) → Users (B) → SQL (A).

## Cómo se armó

1. **Minikube descartado para multi-PC.** Minikube no suma nodos de otros equipos. Se usó k3s en WSL2 en cada PC.
2. **Primer intento: Hamachi.** Los tres equipos en una red Hamachi; k3s server y agents sobre las IPs `25.x` con red espejada de WSL (`setup/unirse-nodo.ps1`, `setup/abrir-firewall.ps1`). El plano de control funcionó (nodos Ready, kubelet accesible por TCP), pero **el tráfico entre pods de distintas PCs no pasó**: una captura en la PC A mostró VXLAN (UDP 8472) saliendo hacia B y ningún paquete entrante. El socket VXLAN lo abre el kernel; la red espejada de WSL no lo entregó. Sin eso no hay DNS del clúster ni llamadas entre servicios.
3. **Solución: Tailscale dentro de Ubuntu.** `tailscaled` es un proceso de usuario con su propia interfaz `tailscale0`; flannel VXLAN corre encima (`--flannel-iface tailscale0`). Se reinstaló el server sobre su IP Tailscale y cada integrante migró su nodo con `setup/migrar-tailscale.ps1` + `setup/migrate-node.sh` (corta ante cualquier error, no desinstala sin backup de imágenes ni sin verificar el server, no registra secretos). Después: DNS del clúster OK y ping entre pods de 7–15 ms.
4. **Despliegue** con `apply-k8s.ps1` sin cambios de código; seed docente; login y catálogo verificados vía Gateway.

Otros ajustes del entorno, sin tocar el código: el puerto 6443 estaba ocupado por Kubernetes de Docker Desktop (se usó 6444); el 9100 por un servicio de Logitech en la PC A (se detuvo); WSL apagaba Ubuntu inactivo, por lo que cada agente mantuvo una sesión abierta.

## Resultados

| Escenario | runId | Resultado | Efecto observado |
|---|---|---|---|
| requests | `f2a9ead2` | PASS | 240 solicitudes: 111 HTTP 200 y 129 HTTP 429 (rate limiting) |
| cpu | `a053806f` | PASS | 130 s de carga en un pod Pharmacy (PC C); recuperación estable |
| ram | `f8320615` | PASS | 32 MiB retenidos y liberados en un pod Pharmacy |
| storage | `3d981e0b` | PASS | 26 pasadas de escritura sincronizada; `sustained_io_observed`, `deviceSaturation=null` |
| network (1.º) | `a956bc49` | **FAIL** | Corte aplicado y restaurado; abortó en la ventana de estabilidad (ver abajo) |
| disconnect | `f278a53d` | PASS | Conexión nueva directa a Pharmacy sin respuesta; Gateway 200; restaurado |
| network (2.º) | `4a616be7` | PASS | Pharmacy directa: 6/6 sin respuesta durante el corte; Gateway 12/12 HTTP 200; luego todo 200 |

Los runIds completos, tiempos (`injectRequestedUtc`, `faultRestoredUtc`, `tRestore`, `tVerified`) y conteos de sondas están en `summary.json`. Reportes y journals completos, comprimidos, en `reports/`. Ningún escenario dejó política, selector ni archivo propio: `cleanup=verified` en las siete corridas.

## Primer `network`: FAIL por causa externa

La NetworkPolicy se aplicó, cortó las conexiones nuevas a Pharmacy y se retiró correctamente (17:47:20–17:48:25). Durante la ventana de 120 s de estabilidad, entre 17:49:00 y 17:49:45, Users y Pharmacy (PCs B y C) perdieron contacto con SQL y Grafana (PC A): fallaron sus health checks SQL y la consulta de alertas devolvió sin respuesta, por lo que el controlador abortó con `Se perdió evaluación sana de las alertas`.

`tailscale-pc-a-20261116-1749.log` muestra la causa: a las **17:49:27** la PC A perdió salida UDP (`UDP is blocked`), Tailscale cambió de relay DERP (hasta ~4 s de latencia) y dio timeouts al abrir conexiones hacia B y C. Coincide con una caída de señal Wi-Fi de la PC A. No se relaciona con el código ni con el controlador; la repetición con conexión estable aprobó sin cambios. Se conserva el FAIL sin modificar criterios.

## Límites

- Laboratorio sobre VPN por Internet (Tailscale), no una LAN de datacenter: la latencia entre nodos es real. La PC A concentra SQL, observabilidad y Gateway; su conectividad es un punto único de falla, como mostró el primer `network`.
- NetworkPolicy aplicada por el controlador embebido de k3s (kube-router), no por Calico como en los PASS del 13/11.
- `operatorDeclared=operador-pc-a`; `tAck=null`: las inyecciones y reversiones fueron automáticas y no se mide reconocimiento humano.
- `requests` y `storage` conservan el alcance de sus versiones (cuota por instancia; I/O sostenida sin saturación).
- Las IPs incluidas son de la red privada Tailscale (100.64.0.0/10); el log de Tailscale tiene las IPs públicas redactadas. No se incluyen tokens, claves ni contraseñas.
