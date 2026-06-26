"""Lightweight smoke test for the dashboard API.

Usage:
    # 1. start the server:  python main.py dashboard --port 8099
    # 2. in another shell:  python scripts/smoke_api.py [--base http://127.0.0.1:8099]

Probes every read endpoint, prints status + top-level shape, and dumps the
OpenAPI route table. Used to confirm refactors don't change behavior — capture
the output before a change and diff it after. Exits non-zero if any check fails.
"""
import argparse
import json
import sys
import urllib.request

READ_ENDPOINTS = [
    "/api/auth/status",
    "/api/stats",
    "/api/gamification",
    "/api/quests",
    "/api/combat-history",
    "/api/jobs",
    "/api/jobs?status=applied",
    "/api/contacts",
    "/api/emails",
    "/api/templates",
    "/api/email-stats",
    "/api/profile",
    "/api/scrapers/status",
    "/api/scrape/progress",
    "/api/activity",
    "/api/llm-usage",
]


def _get(url: str):
    with urllib.request.urlopen(url, timeout=15) as resp:
        return resp.status, json.loads(resp.read().decode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8099")
    args = parser.parse_args()

    failures = 0
    print(f"== smoke against {args.base} ==")
    for ep in READ_ENDPOINTS:
        try:
            status, body = _get(args.base + ep)
            if isinstance(body, list):
                shape = f"list[{len(body)}]"
            elif isinstance(body, dict):
                shape = "keys: " + ", ".join(list(body.keys())[:10])
            else:
                shape = type(body).__name__
            flag = "ok " if status == 200 else "ERR"
            if status != 200:
                failures += 1
            print(f"  [{flag}] {status} {ep:32} {shape}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  [ERR] --- {ep:32} {e}")

    # Dump the route table (method + path) for diffing across refactors.
    try:
        _, spec = _get(args.base + "/openapi.json")
        routes = sorted(
            f"{method.upper():6} {path}"
            for path, methods in spec["paths"].items()
            for method in methods
        )
        print(f"\n== {len(routes)} routes ==")
        print("\n".join(routes))
    except Exception as e:  # noqa: BLE001
        print(f"  could not fetch openapi.json: {e}")

    print(f"\n{'PASS' if failures == 0 else f'FAIL ({failures} errors)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
