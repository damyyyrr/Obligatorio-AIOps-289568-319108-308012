#!/bin/bash
# uso: run_stop.sh <nombre> <dll-local|remote> <duracion_s>
export MSYS_NO_PATHCONV=1
S="C:/Users/vicen/AppData/Local/Temp/claude/46378892a81121ed/298cbf53-e134-4166-b58f-0e477df46ceb/scratchpad"
K='kubectl --kubeconfig C:/Users/vicen/.kube/pharmago-hamachi.yaml --context pharmago-hamachi -n pharmago'
N=$1; DLL=$2; D=$3
cd $S/sigstop
PW=$(sed -n 's/.*Password para todos: \([^ ]*\).*/\1/p' "C:/Users/vicen/OneDrive/Escritorio/aiops/Obligatorio-AIOps-289568-319108-308012/Implementacion K8S/Codigo/Backend/seed-data.sql" | head -1)
(echo "$PW" | $K exec -i recovery-probe -- env DURATION=$D python /tmp/probe.py > $N-probe.jsonl 2>$N-probe.err) &
(python $S/watch_pods.py $N-pods.jsonl $D) &
if [ "$DLL" != remote ]; then
  sleep 20
  P=$(wsl -d Ubuntu-24.04 -u root -- pgrep -o -f "$DLL" | tr -d '\r')
  echo "PID $P"
  wsl -d Ubuntu-24.04 -u root -- kill -STOP "$P"
  date +%s.%N > $N-stop-ts.txt
  cat $N-stop-ts.txt
fi
wait
echo DONE; wc -l $N-*.jsonl
