#!/bin/sh
# Agente dentro del contenedor: stdin por kubectl exec; nunca instalar herramientas.
set -eu
umask 077
mode=${1:?mode}; scenario=${2:?scenario}; id=${3:?run-id}
seconds=${4:-1}; mb=${5:-32}
case "$id" in *[!a-f0-9]*|'') exit 2;; esac
[ "${#id}" -eq 32 ] || exit 2
case "$scenario" in cpu|ram|storage) ;; *) exit 2;; esac
case "$seconds:$mb" in *[!0-9:]*|'') exit 2;; esac
[ "$seconds" -ge 1 ] && [ "$seconds" -le 180 ] || exit 2
[ "$mb" -ge 1 ] && [ "$mb" -le 128 ] || exit 2
[ -d /tmp ] && [ ! -L /tmp ] || exit 2
dir="/tmp/pharmago-chaos-$id"

owned() {
    [ -d "$dir" ] && [ ! -L "$dir" ] && [ ! -L "$dir/owner" ] &&
        [ "$(cat "$dir/owner")" = "$id" ]
}
cleanup() {
    [ ! -e "$dir" ] && return 0
    owned || return 3
    if [ -f "$dir/pids" ] && [ ! -L "$dir/pids" ]; then
        while read -r pid; do
            case "$pid" in *[!0-9]*|'') return 3;; esac
            # No matar un PID reutilizado por otro trabajo.
            if [ -r "/proc/$pid/environ" ] &&
                tr '\000' '\n' < "/proc/$pid/environ" | grep -qx "PHARMAGO_CHAOS_RUNID=$id"; then
                kill "$pid" 2>/dev/null || true
                n=0
                while [ "$n" -lt 10 ] && [ -r "/proc/$pid/environ" ] &&
                    tr '\000' '\n' < "/proc/$pid/environ" | grep -qx "PHARMAGO_CHAOS_RUNID=$id"; do
                    sleep 0.1
                    n=$((n + 1))
                done
                if [ -r "/proc/$pid/environ" ] &&
                    tr '\000' '\n' < "/proc/$pid/environ" | grep -qx "PHARMAGO_CHAOS_RUNID=$id"; then
                    kill -KILL "$pid" 2>/dev/null || true
                fi
                wait "$pid" 2>/dev/null || true
            fi
        done < "$dir/pids"
    fi
    # Nombres exclusivos creados por este agente; no hay borrado recursivo.
    rm -f "$dir/payload" "$dir/pipe" "$dir/pids" "$dir/owner"
    rmdir "$dir"
}

if [ "$mode" = cleanup ]; then
    cleanup
    printf '{"cleaned":true}\n'
    exit 0
fi
if [ "$mode" = status ]; then
    if owned; then
        size=0
        [ ! -f "$dir/payload" ] || size=$(wc -c < "$dir/payload")
        printf '{"active":true,"bytes":%s}\n' "$size"
    elif [ ! -e "$dir" ]; then printf '{"active":false,"bytes":0}\n'
    else exit 3; fi
    exit 0
fi
[ "$mode" = run ] || exit 2
mkdir "$dir" # Falla si ya existía: no adoptar archivos ajenos ni symlinks.
printf '%s\n' "$id" > "$dir/owner"
: > "$dir/pids"
trap 'cleanup' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

if [ "$scenario" = cpu ]; then
    for n in 1 2; do
        env PHARMAGO_CHAOS_RUNID="$id" sh -c 'while :; do :; done' &
        printf '%s\n' "$!" >> "$dir/pids"
    done
elif [ "$scenario" = ram ]; then
    if [ -f /sys/fs/cgroup/memory.max ]; then
        limit=$(cat /sys/fs/cgroup/memory.max); used=$(cat /sys/fs/cgroup/memory.current)
    else
        limit=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
        used=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
    fi
    case "$limit:$used" in *[!0-9:]*|'') exit 4;; esac
    bytes=$(( mb * 1048576 ))
    [ "$limit" -le 1073741824 ] && [ $((bytes * 3)) -le "$limit" ] || exit 4
    [ $((limit - used)) -ge $((bytes * 2 + 33554432)) ] || exit 4
    mkfifo "$dir/pipe"
    # dd retiene un bloque residente mientras escribe en un pipe sin lector activo.
    # sleep mantiene abierto el extremo de lectura; no se escribe RAM a /tmp.
    env PHARMAGO_CHAOS_RUNID="$id" dd if=/dev/zero of="$dir/pipe" bs="$bytes" count=1 2>/dev/null &
    printf '%s\n' "$!" >> "$dir/pids"
    env PHARMAGO_CHAOS_RUNID="$id" sleep "$seconds" < "$dir/pipe" &
    printf '%s\n' "$!" >> "$dir/pids"
elif [ "$scenario" = storage ]; then
    [ "$mb" -le 64 ] || exit 4
    available=$(df -Pk "$dir" | awk 'NR == 2 {print $4}')
    case "$available" in *[!0-9]*|'') exit 4;; esac
    [ "$available" -ge $(( (mb + 1024) * 1024 )) ] || exit 4
    dd if=/dev/zero of="$dir/payload" bs=1048576 count="$mb" conv=fsync 2>/dev/null
fi
printf '{"injected":true,"scenario":"%s","runId":"%s","observedUtc":"%s"}\n' "$scenario" "$id" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
sleep "$seconds"
# Trap retira procesos, FIFO y archivo incluso ante TERM/INT/HUP.
