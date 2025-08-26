import json
import random
import string
from datetime import datetime

import httpx

BASE_URL = "http://127.0.0.1:8000"
API = "/api"


def rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


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


def safe_json(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:
        return (resp.text or "")[:300]


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


def main() -> None:
    email = f"{rand_str()}@example.com"
    password = "pass123!"
    name = "Smoke User"

    account_username = f"u_{rand_str()}"
    account_email = f"{rand_str()}@example.com"
    account_password = "Passw0rd!"

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        r, err = safe_call(client, "GET", "/docs")
        print_result("GET /docs", r, err)

        # Users register/login/me
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users", r, err)
        user_id = r.json().get("id") if (r and 200 <= r.status_code < 300) else None
        user_token = extract_token(r.json()) if (r and 200 <= r.status_code < 300) else None

        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login", r, err)
        login_token = extract_token(r.json()) if (r and 200 <= r.status_code < 300) else None

        token = login_token or user_token
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r, err = safe_call(client, "GET", f"{API}/me", headers=headers)
        print_result("GET /api/me", r, err)

        # Negative: missing auth
        r, err = safe_call(client, "GET", f"{API}/me")
        print_result("GET /api/me (no auth)", r, err)

        # Negative: wrong password login
        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": "wrong"})
        print_result("POST /api/login (wrong password)", r, err)

        # Duplicate users register
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users (duplicate)", r, err)

        # Account routes
        r, err = safe_call(client, "POST", f"{API}/auth/signup", json={"username": account_username, "email": account_email, "password": account_password})
        print_result("POST /api/auth/signup", r, err)
        acc_id = r.json().get("id") if (r and 200 <= r.status_code < 300) else None

        r, err = safe_call(client, "POST", f"{API}/auth/signin", json={"username": account_username, "email": account_email, "password": account_password})
        print_result("POST /api/auth/signin", r, err)

        r, err = safe_call(client, "GET", f"{API}/accounts")
        print_result("GET /api/accounts", r, err)

        if acc_id:
            r, err = safe_call(client, "GET", f"{API}/accounts/{acc_id}")
            print_result("GET /api/accounts/{id}", r, err)

            # Update account (username only for demo via query params)
            r, err = safe_call(client, "PATCH", f"{API}/accounts/{acc_id}", params={"query_id": acc_id, "update_username": f"{account_username}_upd"})
            print_result("PATCH /api/accounts/{id}", r, err)

            r, err = safe_call(client, "DELETE", f"{API}/accounts", params={"id": acc_id})
            print_result("DELETE /api/accounts?id=", r, err)


if __name__ == "__main__":
    main()
