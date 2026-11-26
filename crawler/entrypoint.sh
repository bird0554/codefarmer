#!/bin/sh
set -eu

# Docker named volumes are mounted after image creation, so initialize their
# ownership at runtime before dropping privileges for the crawler process.
mkdir -p "${DATA_DIR:-/data}"
chown -R appuser:appuser "${DATA_DIR:-/data}"
exec su -s /bin/sh appuser -c "exec $*"
