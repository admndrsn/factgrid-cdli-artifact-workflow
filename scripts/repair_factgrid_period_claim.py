#!/usr/bin/env python3
"""Repair a single FactGrid period/style claim.

This is intentionally narrow: it removes claims on one item where a configured
property points to an old QID, then writes one replacement claim.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
from typing import Any

import requests


FACTGRID_API = "https://database.factgrid.de/w/api.php"


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def env_or_prompt(name: str, prompt: str, secret: bool = False) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    return getpass.getpass(prompt) if secret else input(prompt)


def api_post(session: requests.Session, **data: str) -> dict[str, Any]:
    response = session.post(FACTGRID_API, data={"format": "json", **data}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def login() -> requests.Session:
    username = env_or_prompt("FG_USER", "FactGrid username: ")
    password = env_or_prompt("FG_PASS", "FactGrid password: ", secret=True)
    session = requests.Session()
    token_payload = api_post(
        session,
        action="query",
        meta="tokens",
        type="login",
    )
    login_token = token_payload["query"]["tokens"]["logintoken"]
    api_post(
        session,
        action="login",
        lgname=username,
        lgpassword=password,
        lgtoken=login_token,
    )
    return session


def csrf_token(session: requests.Session) -> str:
    payload = api_post(session, action="query", meta="tokens")
    return payload["query"]["tokens"]["csrftoken"]


def qid_from_datavalue(value: object) -> str:
    if isinstance(value, dict):
        if value.get("id"):
            return clean(value.get("id"))
        if value.get("numeric-id"):
            return f"Q{clean(value.get('numeric-id'))}"
    return clean(value)


def matching_claim_ids(entity: dict[str, Any], properties: list[str], old_qid: str) -> list[tuple[str, str]]:
    claims = entity.get("claims", {})
    matches: list[tuple[str, str]] = []
    for prop in properties:
        for claim in claims.get(prop, []):
            claim_id = clean(claim.get("id"))
            datavalue = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if claim_id and qid_from_datavalue(datavalue) == old_qid:
                matches.append((prop, claim_id))
    return matches


def fetch_entity(session: requests.Session, qid: str) -> dict[str, Any]:
    payload = api_post(session, action="wbgetentities", ids=qid)
    entity = payload.get("entities", {}).get(qid)
    if not entity or "missing" in entity:
        raise RuntimeError(f"{qid} not found")
    return entity


def remove_claims(session: requests.Session, token: str, claim_ids: list[str], summary: str) -> None:
    if not claim_ids:
        return
    api_post(
        session,
        action="wbremoveclaims",
        claim="|".join(claim_ids),
        token=token,
        summary=summary,
    )


def create_item_claim(session: requests.Session, token: str, item_qid: str, prop: str, value_qid: str, summary: str) -> str:
    payload = api_post(
        session,
        action="wbcreateclaim",
        entity=item_qid,
        snaktype="value",
        property=prop,
        value='{"entity-type":"item","numeric-id":%s}' % value_qid.removeprefix("Q"),
        token=token,
        summary=summary,
    )
    return clean(payload.get("claim", {}).get("id"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item", default="Q2170617")
    parser.add_argument("--properties", default="P853,P583", help="Comma-separated properties to inspect")
    parser.add_argument("--old-qid", default="Q512164")
    parser.add_argument("--new-qid", default="Q512163")
    parser.add_argument("--new-property", default="", help="Property to write; defaults to the first matched property")
    parser.add_argument("--summary", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    if not re.fullmatch(r"Q\d+", args.item):
        raise SystemExit("--item must be a QID")
    if not re.fullmatch(r"Q\d+", args.old_qid) or not re.fullmatch(r"Q\d+", args.new_qid):
        raise SystemExit("--old-qid and --new-qid must be QIDs")

    properties = [p.strip() for p in args.properties.split(",") if p.strip()]
    session = login()
    entity = fetch_entity(session, args.item)
    matches = matching_claim_ids(entity, properties, args.old_qid)

    print(f"Item: {args.item}")
    print(f"Replace: {args.old_qid} -> {args.new_qid}")
    print("Matches:")
    if matches:
        for prop, claim_id in matches:
            print(f"  {prop}: {claim_id}")
    else:
        print("  none")

    new_prop = clean(args.new_property) or (matches[0][0] if matches else properties[0])
    summary = args.summary or f"Repair CDLI period for {args.item}: {args.old_qid} -> {args.new_qid}"

    if not args.write:
        print(f"\nDRY_RUN: would remove {len(matches)} claim(s) and add {new_prop} -> {args.new_qid}.")
        return
    if not matches:
        raise RuntimeError(f"No {args.old_qid} claims found on {args.item} for {properties}")

    token = csrf_token(session)
    remove_claims(session, token, [claim_id for _, claim_id in matches], summary)
    new_claim_id = create_item_claim(session, token, args.item, new_prop, args.new_qid, summary)
    print(f"Removed {len(matches)} claim(s).")
    print(f"Added {new_prop} -> {args.new_qid}: {new_claim_id}")


if __name__ == "__main__":
    main()
