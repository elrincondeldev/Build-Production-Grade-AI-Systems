"""CLI: call the hello API with httpx, the way services call each other.

Start the server in one terminal, then in another:
    uv run hello-client
"""

from __future__ import annotations

import argparse

import httpx


def call_echo(client: httpx.Client, message: str, repeat: int = 1, request_id: str | None = None) -> dict:
    headers = {"X-Request-ID": request_id} if request_id else {}
    resp = client.post("/echo", json={"message": message, "repeat": repeat}, headers=headers)
    resp.raise_for_status()  # turn 4xx/5xx into exceptions instead of silently using bad data
    return resp.json()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Call the hello API (Lab 0).")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--message", default="hello Kestrel")
    parser.add_argument("--repeat", type=int, default=2)
    args = parser.parse_args(argv)

    # Always set a timeout. httpx defaults to 5 s; being explicit documents intent.
    with httpx.Client(base_url=args.base_url, timeout=httpx.Timeout(5.0)) as client:
        print("GET /health ->", client.get("/health").json())
        print("POST /echo  ->", call_echo(client, args.message, args.repeat, request_id="lab0-demo-1"))
        bad = client.post("/echo", json={"message": "", "repeat": 9})
        print(f"POST /echo with bad input -> {bad.status_code}")
        for err in bad.json()["detail"]:
            print(f"   {'.'.join(str(p) for p in err['loc'])}: {err['msg']}")


if __name__ == "__main__":
    main()
