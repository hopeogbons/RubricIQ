#!/usr/bin/env python3
"""Production smoke test for RubricIQ.

Hits a deployed backend and asserts the happy-path is healthy. Designed to
be run from a laptop after a deploy, not in CI:

    python scripts/smoke_test.py \\
        --api-url https://api.rubriciq.com \\
        --app-origin https://app.rubriciq.com \\
        --email you@example.com \\
        --password '<superadmin password>'

Exits 0 on success, 1 on the first failing check, with a one-line reason.
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

import json


@dataclass
class Config:
    api_url: str
    app_origin: str
    email: str
    password: str


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    expected_status: int | tuple[int, ...] | None = 200,
) -> tuple[int, dict[str, str], bytes]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = resp.read()
            status_code = resp.status
            response_headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        status_code = exc.code
        response_headers = {k.lower(): v for k, v in exc.headers.items()}

    if expected_status is not None:
        allowed = (
            (expected_status,)
            if isinstance(expected_status, int)
            else expected_status
        )
        if status_code not in allowed:
            raise AssertionError(
                f"{method} {url} -> {status_code} "
                f"(expected one of {allowed}); body={payload[:300]!r}"
            )

    return status_code, response_headers, payload


def _json(payload: bytes) -> Any:
    return json.loads(payload.decode("utf-8")) if payload else None


def step(name: str) -> None:
    print(f"  > {name} ... ", end="", flush=True)


def ok(detail: str = "") -> None:
    print(f"OK{(' ' + detail) if detail else ''}")


def fail(detail: str) -> None:
    print(f"FAIL: {detail}")
    sys.exit(1)


def check_health(cfg: Config) -> None:
    step("GET /health")
    status_code, _, payload = _request("GET", f"{cfg.api_url}/health")
    body = _json(payload)
    if body.get("status") != "ok":
        fail(f"unexpected /health body: {body}")
    ok(f"env={body.get('env')}")


def login(cfg: Config) -> str:
    step("POST /auth/login")
    _, _, payload = _request(
        "POST",
        f"{cfg.api_url}/auth/login",
        body={"email": cfg.email, "password": cfg.password},
    )
    token = _json(payload).get("access_token")
    if not token:
        fail("login returned no access_token")
    ok()
    return token


def check_me(cfg: Config, token: str) -> dict[str, Any]:
    step("GET /auth/me")
    _, _, payload = _request(
        "GET",
        f"{cfg.api_url}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    me = _json(payload)
    if me.get("role") != "superadmin":
        fail(f"expected role=superadmin, got {me.get('role')}")
    if not me.get("is_active"):
        fail("superadmin is not active")
    ok(f"role={me['role']} email={me['email']}")
    return me


def check_rubrics_list(cfg: Config, token: str) -> None:
    step("GET /rubrics")
    _, _, payload = _request(
        "GET",
        f"{cfg.api_url}/rubrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = _json(payload)
    if not isinstance(data, list):
        fail(f"/rubrics did not return a list: {data!r}")
    ok(f"{len(data)} rubric(s)")


def check_cors(cfg: Config) -> None:
    step(f"OPTIONS /health with Origin {cfg.app_origin}")
    _, headers, _ = _request(
        "OPTIONS",
        f"{cfg.api_url}/health",
        headers={
            "Origin": cfg.app_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    allow = headers.get("access-control-allow-origin")
    if allow != cfg.app_origin:
        fail(
            f"CORS allow-origin = {allow!r}, expected exactly {cfg.app_origin!r}. "
            "Set CORS_ALLOW_ORIGINS in the backend to the frontend origin."
        )
    ok()

    step("OPTIONS /health with foreign Origin is rejected")
    _, headers, _ = _request(
        "OPTIONS",
        f"{cfg.api_url}/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
        expected_status=None,
    )
    if "access-control-allow-origin" in headers:
        fail(
            f"CORS leaks: allow-origin header present for foreign origin: "
            f"{headers.get('access-control-allow-origin')!r}"
        )
    ok()


def check_callback_auth(cfg: Config) -> None:
    step("POST /webhooks/n8n-callback without X-API-Key -> 401")
    _request(
        "POST",
        f"{cfg.api_url}/webhooks/n8n-callback",
        body={"learner_id": "00000000-0000-0000-0000-000000000000", "status": "failed"},
        expected_status=401,
    )
    ok()

    step("POST /webhooks/n8n-callback with wrong key -> 401")
    _request(
        "POST",
        f"{cfg.api_url}/webhooks/n8n-callback",
        headers={"X-API-Key": "definitely-not-the-real-secret"},
        body={"learner_id": "00000000-0000-0000-0000-000000000000", "status": "failed"},
        expected_status=401,
    )
    ok()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", "https://api.rubriciq.com"),
        help="Public backend base URL (no trailing slash).",
    )
    parser.add_argument(
        "--app-origin",
        default=os.environ.get("APP_ORIGIN", "https://app.rubriciq.com"),
        help="Public frontend origin (used for the CORS preflight check).",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("SUPERADMIN_EMAIL"),
        help="Superadmin email. Defaults to $SUPERADMIN_EMAIL.",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SUPERADMIN_PASSWORD"),
        help="Superadmin password. Defaults to $SUPERADMIN_PASSWORD.",
    )
    args = parser.parse_args()

    if not args.email or not args.password:
        print("ERROR: superadmin --email / --password are required (or set env vars).")
        return 1

    cfg = Config(
        api_url=args.api_url.rstrip("/"),
        app_origin=args.app_origin.rstrip("/"),
        email=args.email,
        password=args.password,
    )

    print(f"Smoke test against {cfg.api_url}")
    check_health(cfg)
    token = login(cfg)
    check_me(cfg, token)
    check_rubrics_list(cfg, token)
    check_cors(cfg)
    check_callback_auth(cfg)
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
