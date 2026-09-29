#!/usr/bin/env python3
"""Check whether FactGrid's MediaWiki API is returning JSON.

This script intentionally does not read or print credentials. It is meant for
diagnosing cases where login code receives HTML or an empty response instead of
the JSON that wikibaseintegrator expects.
"""

from __future__ import annotations

import argparse
import json

import requests


FACTGRID_API = "https://database.factgrid.de/w/api.php"
HEADERS = {
    "User-Agent": "TokenWorks-FactGrid-api-check/0.1",
    "Accept": "application/json, */*",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=FACTGRID_API)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    params = {"action": "query", "meta": "siteinfo", "siprop": "general", "format": "json"}
    response = requests.get(args.api_url, params=params, headers=HEADERS, timeout=args.timeout)
    content_type = response.headers.get("content-type", "")
    print(f"status={response.status_code}")
    print(f"content-type={content_type!r}")
    print(f"url={response.url}")
    text = response.text
    try:
        data = response.json()
    except json.JSONDecodeError:
        print("json=failed")
        print(f"first_500_chars={text[:500]!r}")
        return
    print("json=ok")
    general = data.get("query", {}).get("general", {})
    print(f"sitename={general.get('sitename', '')}")
    print(f"generator={general.get('generator', '')}")


if __name__ == "__main__":
    main()
