#!/bin/sh
# Agente acotado; el lock serializa arranque, aborto y limpieza por run-id.
set -eu
umask 077
mode=${1:?mode}; scenario=${2:?scenario}; id=${3:?run-id}
seconds=${4:-1}; mb=${5:-32}; until_epoch=${6:-0}
case "$id" in *[!a-f0-9]*|'') exit 2;; esac
[ "${#id}" -eq 32 ] || exit 2
case "$scenario" in cpu|ram|storage) ;; *) exit 2;; esac
case "$seconds:$mb:$until_epoch" in *[!0-9:]*|'') exit 2;; esac
[ "$seconds" -ge 1 ] && [ "$seconds" -le 180 ] || exit 2
[ "$mb" -ge 1 ] && [ "$mb" -le 128 ] || exit 2
[ -d /tmp ] && [ ! -L /tmp ] || exit 2
command -v flock >/dev/null || exit 4
dir="/tmp/pharmago-chaos-$id"
cancel="$dir.cancel"
lock="$dir.lock"
locked=false

owned_file() {
    [ -f "$1" ] && [ ! -L "$1" ] && [ "$(cat "$1")" = "$id" ]
}
owned() {
    [ -d "$dir" ] && [ ! -L "$dir" ] && owned_file "$dir/owner"
}
release_lock() {
    if [ "$locked" = true ]; then
        flock -u 9
        exec 9>&-
        locked=false
    fi
}
take_lock() {
    if [ ! -e "$lock" ] && [ ! -L "$lock" ]; then
        (set -C; printf '%s\n' "$id" > "$lock") 2>/dev/null || true
    fi
    owned_file "$lock" || return 3
    exec 9<>"$lock"
    flock -w 5 9 || return 3
    locked=true
}
cancelled() {
    if [ -e "$cancel" ] || [ -L "$cancel" ]; then
        owned_file "$cancel" || exit 3
        return 0
    fi
    return 1
}
cleanup() {
    take_lock || return 3
    # Conservar cancelación aun si el RPC de run todavía no comenzó.
    # El mismo flock protege la comprobación, los forks y el registro de PIDs.
    if [ ! -e "$cancel" ] && [ ! -L "$cancel" ]; then
        (set -C; printf '%s\n' "$id" > "$cancel") 2>/dev/null || return 3
    fi
    owned_file "$cancel" || return 3
    if [ -e "$dir" ] || [ -L "$dir" ]; then
        owned || return 3
        if [ -f "$dir/pids" ] && [ ! -L "$dir/pids" ]; then
            while read -r pid; do
                case "$pid" in *[!0-9]*|'') return 3;; esac
                [ "$pid" -gt 1 ] || return 3
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
                        kill -KILL "$pid" 2>/dev/null || return 3
                    fi
                    wait "$pid" 2>/dev/null || true
                fi
            done < "$dir/pids"
        fi
        # Solo nombres exclusivos del agente; no hay borrado recursivo.
        rm -f "$dir/payload" "$dir/pipe" "$dir/pids" "$dir/owner" || return 3
        rmdir "$dir" || return 3
    fi
    release_lock
}
finish() {
    code=$?
    trap - EXIT INT TERM HUP
    release_lock
    if ! cleanup; then release_lock; exit 3; fi
    exit "$code"
}
trap release_lock EXIT

if [ "$mode" = cleanup ]; then
    cleanup
    printf '{"cleaned":true,"cancelled":true}\n'
    exit 0
fi
take_lock
if [ "$mode" = status ]; then
    active=false; size=0; stopped=false
    if owned; then
        active=true
        [ ! -f "$dir/payload" ] || size=$(wc -c < "$dir/payload")
    elif [ -e "$dir" ] || [ -L "$dir" ]; then exit 3; fi
    if cancelled; then stopped=true; fi
    printf '{"active":%s,"bytes":%s,"cancelled":%s}\n' "$active" "$size" "$stopped"
    exit 0
fi
if [ "$mode" = clear ]; then
    # El controlador exige RPC terminado o deadline + 15 s antes de retirar esto.
    [ ! -e "$dir" ] && [ ! -L "$dir" ] || exit 3
    if cancelled; then rm "$cancel"; fi
    rm "$lock"
    printf '{"cleared":true}\n'
    exit 0
fi
[ "$mode" = run ] && [ "$until_epoch" -gt 0 ] || exit 2
if cancelled; then printf '{"injected":false,"reason":"cancelled"}\n'; exit 0; fi
current=$(date +%s)
if [ "$current" -ge "$until_epoch" ]; then
    printf '{"injected":false,"reason":"expired"}\n'
    exit 0
fi
stop_epoch=$((current + seconds))
[ "$stop_epoch" -le "$until_epoch" ] || stop_epoch=$until_epoch
mkdir "$dir"
printf '%s\n' "$id" > "$dir/owner"
: > "$dir/pids"
trap finish EXIT
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
    env PHARMAGO_CHAOS_RUNID="$id" dd if=/dev/zero of="$dir/pipe" bs="$bytes" count=1 2>/dev/null &
    printf '%s\n' "$!" >> "$dir/pids"
    env PHARMAGO_CHAOS_RUNID="$id" sleep "$seconds" < "$dir/pipe" &
    printf '%s\n' "$!" >> "$dir/pids"
elif [ "$scenario" = storage ]; then
    [ "$mb" -le 64 ] || exit 4
    available=$(df -Pk "$dir" | awk 'NR == 2 {print $4}')
    case "$available" in *[!0-9]*|'') exit 4;; esac
    [ "$available" -ge $(( (mb + 1024) * 1024 )) ] || exit 4
    env PHARMAGO_CHAOS_RUNID="$id" dd if=/dev/zero of="$dir/payload" bs=1048576 count="$mb" conv=fsync 2>/dev/null &
    writer=$!
    printf '%s\n' "$writer" >> "$dir/pids"
    wait "$writer"
fi
release_lock
printf '{"injected":true,"scenario":"%s","runId":"%s","observedUtc":"%s"}\n' "$scenario" "$id" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
while [ "$(date +%s)" -lt "$stop_epoch" ]; do
    if cancelled; then break; fi
    sleep 1
done
# EXIT publica cancelación y limpia antes de confirmar fin del RPC.
