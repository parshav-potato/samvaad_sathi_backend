import json
import os
import random
import string

import httpx


BASE_URL = "http://127.0.0.1:8000"
API = "/api"


def rand_email() -> str:
    s = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"resume_{s}@example.com"


def main() -> None:
    # Use repo-local sample file for portability
    repo_root = os.path.dirname(os.path.dirname(__file__))
    file_path = os.path.join(repo_root, "assets", "sample_resume.txt")
    if not os.path.exists(file_path):
        print(json.dumps({"ok": False, "error": f"Sample file not found: {file_path}"}))
        return

    email = rand_email()
    payload = {"email": email, "password": "Passw0rd!1", "name": "Tester"}

    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        r = client.post(f"{API}/users", json=payload)
        if r.status_code >= 300:
            print(json.dumps({"ok": False, "step": "register", "status": r.status_code, "body": r.text[:300]}))
            return
        body = r.json()
        token = None
        for k in ("authorizedUser", "authorized_user"):
            if k in body and isinstance(body[k], dict) and "token" in body[k]:
                token = body[k]["token"]
                break
        if not token:
            print(json.dumps({"ok": False, "error": "Token not found", "body": body}, default=str))
            return

        headers = {"Authorization": f"Bearer {token}"}
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "text/plain")}
            r = client.post(f"{API}/extract-resume", headers=headers, files=files)
            try:
                out = r.json()
            except Exception:
                out = (r.text or "")[:500]
            print(json.dumps({"ok": 200 <= r.status_code < 300, "status": r.status_code, "body": out}, default=str))


if __name__ == "__main__":
    main()


