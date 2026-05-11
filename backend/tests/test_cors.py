"""CORS allow-list enforcement.

The middleware reads its allow list from `settings.cors_allow_origins`,
which `conftest.py` does not override -> the default localhost set applies.
A production origin is not in that list and must not see an allow header.
"""


def test_localhost_origin_is_allowed(client):
    r = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_unknown_origin_does_not_receive_allow_header(client):
    r = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette returns 400 for an unmatched preflight; either way the
    # important assertion is that no allow-origin header echoes the origin.
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_actual_request_from_unknown_origin_blocked_by_browser(client):
    """A non-preflight GET still succeeds at HTTP level (CORS is enforced by
    the browser), but the response must not include allow-origin for an
    origin that is not in the list."""
    r = client.get("/health", headers={"Origin": "https://evil.example.com"})
    # The /health endpoint itself works; the lack of allow-origin is what
    # protects the user.
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
