# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 MikeFox303

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

_UPSTREAM = os.environ.get("FOXFORGE_PROXY_UPSTREAM", "http://foxforge-backend:8000").rstrip("/")
_PORT = int(os.environ.get("FOXFORGE_PROXY_PORT", "8080"))


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        headers = {
            "Accept": self.headers.get("Accept", "application/json"),
            "X-Forwarded-For": self.client_address[0],
            "X-Forwarded-Proto": "http",
            "X-Forwarded-Host": self.headers.get("Host", "proxy.invalid"),
            # Representative deployment identity metadata. FoxForge must not
            # interpret either header as an application principal.
            "X-Authenticated-User": self.headers.get("X-Authenticated-User", "umbreld-user"),
        }
        for name in ("Authorization", "Content-Type", "Idempotency-Key", "X-Request-Id"):
            value = self.headers.get(name)
            if value is not None:
                headers[name] = value

        request = Request(
            f"{_UPSTREAM}{self.path}",
            data=body,
            headers=headers,
            method=self.command,
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed CI upstream
                payload = response.read()
                self._respond(response.status, response.headers.get("Content-Type"), payload)
        except HTTPError as exc:
            self._respond(exc.code, exc.headers.get("Content-Type"), exc.read())

    def _respond(self, status: int, content_type: str | None, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        self._proxy()

    def log_message(self, format: str, *args: object) -> None:
        # Keep CI logs concise and avoid reflecting request headers.
        del format, args


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", _PORT), ProxyHandler).serve_forever()
