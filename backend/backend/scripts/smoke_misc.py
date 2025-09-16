import os
from datetime import datetime

import httpx

from scripts.smoke_utils import BASE_URL, API, safe_call, print_result, safe_json


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Root, docs and health
        r, err = safe_call(client, "GET", "/")
        print_result("GET /", r, err)
        r, err = safe_call(client, "GET", "/docs")
        print_result("GET /docs", r, err)

        r, err = safe_call(client, "GET", f"{API}/health")
        print_result("GET /api/health", r, err)

        # Negative health (wrong path)
        r, err = safe_call(client, "GET", f"{API}/_health")
        print_result("GET /api/_health (expect 404)", r, err)

        # Positive: minimal PDF resume upload requires auth; here we only validate endpoint exists unauth (expect 403)
        files_pdf = {"file": ("sample.pdf", b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n", "application/pdf")}
        r, err = safe_call(client, "POST", f"{API}/extract-resume", files=files_pdf)
        print_result("POST /api/extract-resume (pdf, no auth)", r, err)


if __name__ == "__main__":
    main()


