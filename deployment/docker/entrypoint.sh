#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  mkdir -p /data
  chown -R foxforge:foxforge /data
  exec gosu foxforge "$@"
fi

exec "$@"
