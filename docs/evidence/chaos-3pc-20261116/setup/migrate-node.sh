#!/bin/bash
# Pasa este nodo k3s de Hamachi a Tailscale. Se corre como root dentro de Ubuntu (WSL).
# Uso: bash migrate-node.sh NOMBRE IP_SERVER   (token en /root/.k3s-token, auth key en /root/.ts-key)
# Se corta ante cualquier error. No hay set -x: los secretos no se escriben en el log.
set -euo pipefail
exec > >(tee /root/pharmago-migrate.log) 2>&1
trap 'echo "ERROR en la linea $LINENO: migracion NO terminada. Mandar foto de esta ventana."; rm -f /root/.ts-key /root/.k3s-token' ERR

NAME=$1; A_TS=$2
TAG=k8s-20261116-01
IMAGES="docker.io/library/pharmago-users-service:$TAG docker.io/library/pharmago-pharmacy-service:$TAG docker.io/library/pharmago-api-gateway:$TAG docker.io/library/pharmago-ui:$TAG"
BACKUP=/root/pharmago-images.tar
step() { echo; echo "== $*"; }

[ -s /root/.ts-key ] && [ -s /root/.k3s-token ] || { echo "Faltan la clave o el token"; exit 1; }

step "1/6 Tailscale"
if ! command -v tailscale >/dev/null; then curl -fsSL https://tailscale.com/install.sh | sh; fi
systemctl enable --now tailscaled
tailscale up --authkey="$(cat /root/.ts-key)" --hostname="$NAME" --accept-dns=false
rm -f /root/.ts-key
MY=$(tailscale ip -4 | head -1)
[ -n "$MY" ] || { echo "Tailscale no dio IP"; exit 1; }
echo "IP Tailscale: $MY"

step "2/6 Server alcanzable por Tailscale (antes de tocar nada)"
ok=0
for i in $(seq 1 24); do
  r=$(curl -sk --max-time 5 "https://$A_TS:6444/ping" || true)
  if [ "$r" = pong ]; then ok=1; break; fi
  sleep 5
done
[ "$ok" = 1 ] || { echo "No se llega al server $A_TS:6444 por Tailscale. No se desinstalo nada."; exit 1; }
echo "Server OK"

step "3/6 Backup de imagenes PharmaGo"
if [ ! -s "$BACKUP" ]; then
  k3s ctr -n k8s.io images export "$BACKUP.tmp" $IMAGES
  [ -s "$BACKUP.tmp" ] || { echo "Backup vacio. No se desinstalo nada."; exit 1; }
  mv "$BACKUP.tmp" "$BACKUP"
fi
ls -lh "$BACKUP"

step "4/6 Desinstalar agente viejo (Hamachi)"
if [ -x /usr/local/bin/k3s-agent-uninstall.sh ]; then /usr/local/bin/k3s-agent-uninstall.sh; fi

step "5/6 Instalar agente nuevo (Tailscale)"
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION='v1.34.1+k3s1' K3S_URL="https://$A_TS:6444" \
  K3S_TOKEN="$(cat /root/.k3s-token)" sh -s - agent --node-name "$NAME" --node-ip "$MY" --flannel-iface tailscale0
rm -f /root/.k3s-token
systemctl is-active --quiet k3s-agent || { echo "k3s-agent no quedo activo"; exit 1; }
ready=0
for i in $(seq 1 30); do
  if k3s ctr -n k8s.io images ls -q >/dev/null 2>&1; then ready=1; break; fi
  sleep 5
done
[ "$ready" = 1 ] || { echo "containerd no respondio"; exit 1; }

step "6/6 Importar imagenes y verificar"
k3s ctr -n k8s.io images import "$BACKUP"
have=$(k3s ctr -n k8s.io images ls -q)
for img in $IMAGES; do
  printf '%s\n' "$have" | grep -qx "$img" || { echo "Falta la imagen $img"; exit 1; }
done
echo "4 imagenes OK"

trap - ERR
echo; echo MIGRATE_DONE
