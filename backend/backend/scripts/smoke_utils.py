import json
import os
import httpx

# Allow overriding base URL/prefix for smoke runs (e.g., pointing at staging)
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")
API = os.getenv("SMOKE_API_PREFIX", "/api")


def safe_json(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:
        return (resp.text or "")[:300]


def print_result(name: str, resp: httpx.Response | None, error: str | None = None) -> None:
    if error is not None:
        print(json.dumps({"name": name, "status": None, "ok": False, "error": error}))
        return
    ok = 200 <= resp.status_code < 300 if resp is not None else False
    print(json.dumps({
        "name": name,
        "status": None if resp is None else resp.status_code,
        "ok": ok,
        "body": None if resp is None else safe_json(resp)
    }, default=str))


def safe_call(client: httpx.Client, method: str, url: str, **kwargs) -> tuple[httpx.Response | None, str | None]:
    try:
        r = client.request(method, url, **kwargs)
        return r, None
    except Exception as e:
        return None, str(e)


def extract_token(body: dict) -> str | None:
    for key in ("authorizedUser", "authorized_user", "authorizedAccount", "authorized_account"):
        if key in body and isinstance(body[key], dict) and "token" in body[key]:
            return body[key]["token"]
    return None


def auth_headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}

