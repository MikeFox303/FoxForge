# Retired MikeFox303 Bambuddy fork — migration record

The former `MikeFox303/bambuddy` repository was retired as a production dependency on 2026-09-03.

## Former production state

- downstream main head: `f26ce2df334841cc8ead0c0933fdcb01bf33ba4c`
- live rollback image used during migration: `ghcr.io/mikefox303/bambuddy:1.2.5.5-x2d.73@sha256:9abf0d5bfb612dd1f473a7632f2b7aa404ef06db759e979b388bd7466cc84fb0`
- Store-era general rollback image: `ghcr.io/mikefox303/bambuddy:1.2.5.5-x2d.204@sha256:0539eb76a64994081a868a30cb854097a0e9a9732dc0d60f05666748fe341743`

These image references are historical records, not active dependencies.

## Official production replacement

Umbrel packaging now consumes the official stable Bambuddy image directly:

`ghcr.io/maziggy/bambuddy:1.2.5.5@sha256:dc627d618cc3d3252ae4ab33af74c4679c66a9a06e0e3bbb7aefa32d1a4d4a07`

The migration was published to `MikeFox303/umbrel-3d-printing-store` through commit `17259751f48642dd02dd07e6a1b52d8021d97d9e` and subsequent release-gate cleanup.

## Accepted Umbrel network invariants

The working X2D + Virtual Printer deployment preserved:

- `network_mode: host`
- `APP_HOST: 192.168.0.100`
- `PORT: 8000`
- `NET_BIND_SERVICE`
- `VIRTUAL_PRINTER_ADVERTISE_ADDRESS: 192.168.0.100`
- `VIRTUAL_PRINTER_PASV_ADDRESS: 192.168.0.100`

## Live acceptance completed before retirement

- official Bambuddy health: PASS
- Umbrel app proxy: PASS
- X2D connected/IDLE: PASS
- X2D ports 8883/990/322/6000 reachable: PASS
- AMS 2 Pro 4/4 trays visible: PASS
- Spoolman connected: PASS
- Virtual Printer runtime enabled/running: PASS
- five Spoolman slot assignments preserved: PASS
- Bambuddy restart persistence: PASS
- Spoolman restart persistence: PASS

Future Bambuddy experiments belong in FoxForge or short-lived upstream contribution branches, not in a parallel production distribution.
