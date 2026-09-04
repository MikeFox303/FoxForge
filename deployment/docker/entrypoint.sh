#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  mkdir -p /data
  chown foxforge:foxforge /data

  ownership_marker=/data/.foxforge-ownership-v1
  if [ ! -f "$ownership_marker" ]; then
    # One-time compatibility migration for volumes created by older images.
    # Do not recursively walk a growing artifact/history tree on every restart.
    chown -R foxforge:foxforge /data
    : > "$ownership_marker"
    chown foxforge:foxforge "$ownership_marker"
  fi

  exec gosu foxforge "$@"
fi

exec "$@"
