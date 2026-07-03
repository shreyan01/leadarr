"""Reads what the server's own TLS handshake presents — the certificate,
protocol version, cipher — without sending anything beyond the ClientHello
any browser sends to open an HTTPS connection. No exploitation surface here:
this is the read-only half of a normal connection.
"""
from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class TlsInfo:
    https: bool
    tls_version: str | None = None
    cert_issuer: str | None = None
    cert_expires_at: datetime | None = None
    error: str | None = None


def inspect_tls(hostname: str, port: int = 443, timeout_s: float = 10.0) -> TlsInfo:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=timeout_s) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                cert = tls_sock.getpeercert()
                version = tls_sock.version()
    except (socket.error, ssl.SSLError, OSError) as exc:
        return TlsInfo(https=False, error=str(exc))

    issuer = _format_dn(cert.get("issuer", ())) if cert else None
    expires_at = _parse_cert_date(cert.get("notAfter")) if cert else None

    return TlsInfo(https=True, tls_version=version, cert_issuer=issuer, cert_expires_at=expires_at)


def _format_dn(dn_tuples: tuple) -> str:
    parts = []
    for rdn in dn_tuples:
        for key, value in rdn:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def _parse_cert_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    # Python's ssl module formats notAfter like 'Jun  1 12:00:00 2027 GMT'
    parsed = datetime.strptime(raw, "%b %d %H:%M:%S %Y %Z")
    return parsed.replace(tzinfo=timezone.utc)
