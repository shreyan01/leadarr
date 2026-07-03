from __future__ import annotations

from unittest.mock import MagicMock

from app.core.rate_limit import _client_identity


def _make_request(*, auth_header: str | None = None, client_host: str | None = "1.2.3.4") -> MagicMock:
    request = MagicMock()
    request.headers = {"authorization": auth_header} if auth_header else {}
    request.client = MagicMock(host=client_host) if client_host else None
    return request


def test_identity_uses_ip_when_unauthenticated():
    request = _make_request(client_host="203.0.113.5")
    assert _client_identity(request) == "ip:203.0.113.5"


def test_identity_uses_token_bucket_when_authenticated():
    request = _make_request(auth_header="Bearer abc.def.ghi")
    identity = _client_identity(request)
    assert identity.startswith("token:")


def test_different_tokens_get_different_identities():
    id_a = _client_identity(_make_request(auth_header="Bearer token-a"))
    id_b = _client_identity(_make_request(auth_header="Bearer token-b"))
    assert id_a != id_b


def test_same_token_gets_same_identity():
    id_a = _client_identity(_make_request(auth_header="Bearer token-a"))
    id_b = _client_identity(_make_request(auth_header="Bearer token-a"))
    assert id_a == id_b


def test_missing_client_falls_back_to_unknown():
    request = _make_request(client_host=None)
    assert _client_identity(request) == "ip:unknown"
