# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ARG VCS_REF="unknown"
ARG VERSION="0.1.0.dev0"

LABEL org.opencontainers.image.title="FoxForge" \
      org.opencontainers.image.description="Self-hosted multi-vendor 3D printer management" \
      org.opencontainers.image.source="https://github.com/MikeFox303/FoxForge" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FOXFORGE_HOST=0.0.0.0 \
    FOXFORGE_PORT=8000 \
    FOXFORGE_DATA_DIR=/data \
    FOXFORGE_CONFIG=/data/config.json \
    FOXFORGE_STATIC_DIR=/app/static

WORKDIR /app
COPY backend/ /tmp/foxforge-backend/
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir -c /tmp/foxforge-backend/constraints.txt /tmp/foxforge-backend \
    && rm -rf /tmp/foxforge-backend \
    && groupadd --gid 1000 foxforge \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin foxforge \
    && mkdir -p /data /app/static \
    && chown -R foxforge:foxforge /data /app
COPY --from=frontend --chown=foxforge:foxforge /src/frontend/dist/ /app/static/
COPY deployment/docker/entrypoint.sh /usr/local/bin/foxforge-entrypoint
RUN chmod 0755 /usr/local/bin/foxforge-entrypoint

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()" || exit 1

ENTRYPOINT ["foxforge-entrypoint"]
CMD ["foxforge"]
