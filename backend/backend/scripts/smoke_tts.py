"""Smoke test for POST /api/tts/convert (ElevenLabs TTS endpoint)."""

import json
import os
import random
import string

import httpx

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")
API = os.getenv("SMOKE_API_PREFIX", "/api")


def rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def print_result(name: str, resp: httpx.Response | None, error: str | None = None) -> None:
    if error is not None:
        print(json.dumps({"name": name, "status": None, "ok": False, "error": error}))
        return
    ok = 200 <= resp.status_code < 300
    body: object
    if resp.headers.get("content-type", "").startswith("audio/"):
        body = f"<audio bytes: {len(resp.content)}>"
    else:
        try:
            body = resp.json()
        except Exception:
            body = (resp.text or "")[:300]
    print(json.dumps({"name": name, "status": resp.status_code, "ok": ok, "body": body}, default=str))


def main() -> None:
    email = f"{rand_str()}@example.com"
    password = "pass123!"
    name = "TTS Smoke User"

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # ── 1. Register ──────────────────────────────────────────────────────
        r = client.post(f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /users (register)", r)
        body = r.json() if r.status_code < 300 else {}
        token = None
        for key in ("authorizedUser", "authorized_user", "authorizedAccount", "authorized_account"):
            if key in body and isinstance(body[key], dict) and "token" in body[key]:
                token = body[key]["token"]
                break

        if not token:
            print(json.dumps({"name": "ABORT", "ok": False, "error": "Could not obtain auth token"}))
            return

        headers = {"Authorization": f"Bearer {token}"}

        # ── 2. TTS – happy path ───────────────────────────────────────────────
        r = client.post(
            f"{API}/tts/convert",
            json={"text": "Hello! This is a test of the ElevenLabs text to speech integration."},
            headers=headers,
        )
        print_result("POST /tts/convert (happy path)", r)

        if r.status_code == 200:
            audio_size = len(r.content)
            latency = r.headers.get("x-latency-ms", "n/a")
            print(json.dumps({
                "name": "TTS audio details",
                "ok": True,
                "audio_bytes": audio_size,
                "latency_ms": latency,
                "content_type": r.headers.get("content-type"),
            }))

        # ── 3. TTS – no auth (should 403/401) ────────────────────────────────
        r = client.post(
            f"{API}/tts/convert",
            json={"text": "Unauthorized test"},
        )
        print_result("POST /tts/convert (no auth – expect 4xx)", r)

        # ── 4. TTS – empty text (should 422) ─────────────────────────────────
        r = client.post(
            f"{API}/tts/convert",
            json={"text": ""},
            headers=headers,
        )
        print_result("POST /tts/convert (empty text – expect 422)", r)

        # ── 5. TTS – custom voice_id field present ────────────────────────────
        r = client.post(
            f"{API}/tts/convert",
            json={
                "text": "Testing custom voice field.",
                "voice_id": "hpp4J3VqNfWAUOO0d1Us",
            },
            headers=headers,
        )
        print_result("POST /tts/convert (explicit voice_id)", r)


if __name__ == "__main__":
    main()
