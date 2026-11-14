# Quickstart Kubernetes — PharmaGo

La preparación completa está en la [guía Kubernetes](../k8s/README-k8s.md). El flujo actual requiere perfil/contexto explícitos, tag de imagen y Secrets externos; los comandos antiguos sin argumentos ya no son válidos.

## Antes de construir o desplegar

- Instalar las dependencias Python de `k8s/requirements.txt`.
- Identificar un perfil Minikube propio y un contexto accesible; comprobar nodos Ready y capacidad.
- Preparar etiquetas según la topología: tres roles de servicio y un nodo propietario de los PV. El modo `single-node` es para desarrollo y no acredita separación física.
- Preparar `k8s/secrets.local.json` según `secrets.example.json`. En una instalación con datos, conservar las credenciales vigentes.
- Para el escenario de red, el laboratorio necesita un CNI que aplique NetworkPolicy. Seguir también la [guía de caos](../chaos-engineering/README.md).

Los scripts no crean un perfil Minikube ni cambian el contexto activo: construyen/cargan imágenes y aplican recursos al clúster ya identificado. La guía completa explica la creación de un perfil y sus etiquetas; este resumen no reemplaza ese paso.

## Construcción y apply

Desde la raíz del repositorio, en Bash, sustituir los valores entre `<...>` por los verificados y usar un tag nuevo:

```bash
bash 'Implementacion K8S/Codigo/k8s/build-images.sh' --context '<contexto>' --profile '<perfil>' --image-tag '<tag-nuevo>'
```

Comprobar el resultado antes de continuar. Con ese tag cargado en los nodos:

```bash
bash 'Implementacion K8S/Codigo/k8s/apply-k8s.sh' --context '<contexto>' --image-tag '<tag-nuevo>' --timeout 600
```

El modo predeterminado es `separated`. Solo para un nodo de desarrollo etiquetado `node-type=all`, agregar `--topology single-node` al apply. Un archivo de credenciales distinto se selecciona con `--secrets-file '<archivo-local-ignorado>'`. El apply no inserta seed ni resetea datos.

PowerShell dispone de wrappers con `-Context`, `-Profile`, `-ImageTag`, `-Topology` y `-SecretsFile` según corresponda; ver los ejemplos de la guía completa. En Bash, los wrappers usan `python3` o la ruta de `PHARMAGO_PYTHON`.

## Acceso y comprobación

Abrir terminales separadas y mantener cada port-forward en primer plano, con contexto explícito:

```bash
kubectl --context '<contexto>' -n pharmago port-forward service/pharmago-ui 4200:80
```

```bash
kubectl --context '<contexto>' -n pharmago port-forward service/pharmago-api-gateway 5000:80
```

La UI queda en http://127.0.0.1:4200 y usa el Gateway en http://127.0.0.1:5000. Comprobar catálogo y login con los datos de laboratorio existentes; HTTP 200 del HTML no equivale a un flujo funcional aprobado. Para Grafana, Prometheus, Jaeger y Kibana seguir las guías de [métricas](../../../docs/aiops-k8s-metrics.md), [trazas](../../../docs/evidence/issue-11-20261112/README.md) y [logs](como-revisar-logs-kibana.md).

Las credenciales son las vigentes del laboratorio, no valores predeterminados de esta guía. El helper heredado `port-forward.sh` usa el contexto global y muestra textos de credenciales antiguos; los comandos explícitos anteriores evitan depender de ese comportamiento.

Para parar conservando datos, seguir [parada y recuperación](../k8s/README-k8s.md#parada-y-recuperación). `cleanup` escala Deployments a cero y conserva PV/PVC; no apaga todos los recursos del clúster.
