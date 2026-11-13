#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "${PHARMAGO_PYTHON:-python}" "$HERE/chaos.py" ram "$@"
