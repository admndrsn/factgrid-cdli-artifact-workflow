#!/usr/bin/env python3
"""Repair the TokenWorks finding-spot authority item for Mari/Tell Hariri.

The downloaded lookup row for ``Mari (mod. Tell Hariri)`` incorrectly mapped it
to FactGrid ``Q389650`` / Gherla. During the pilot this created TokenWorks
``Q132022`` as "Gherla", and artifact finding-spot claims for Mari now point to
that item. Since those claims are semantically intended to point to Mari, this
script repurposes ``Q132022`` as the Mari authority item and updates its
FactGrid Item ID claim to ``Q389896``.
"""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from wikibaseintegrator import WikibaseIntegrator, datatypes
from wikibaseintegrator.wbi_config import config
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.wbi_login import Login


TW_API = "https://wikibase.tk-wiki-kg.com/w/api.php"
DEFAULT_QID = "Q132022"
FACTGRID_ITEM_ID_PROPERTY = "P378"
OLD_FACTGRID_QID = "Q389650"
NEW_FACTGRID_QID = "Q389896"


def api_login() -> WikibaseIntegrator:
    username = os.environ.get("TW_USER") or input("TokenWorks username: ")
    password = os.environ.get("TW_PASS") or getpass.getpass("TokenWorks password: ")
    config["MEDIAWIKI_API_URL"] = TW_API
    config["PROPERTY_CONSTRAINTS_CHECK"] = False
    login = Login(user=username, password=password)
    return WikibaseIntegrator(login=login)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=60), retry=retry_if_exception_type(Exception))
def robust_write(entity, summary: str):
    return entity.write(summary=summary)


def claim_values(item, prop: str) -> list[str]:
    values: list[str] = []
    for claim in item.claims.get(prop):
        try:
            values.append(str(claim.mainsnak.datavalue["value"]))
        except Exception:
            values.append(str(claim))
    return values


def repair(args: argparse.Namespace) -> None:
    wbi = api_login()
    item = wbi.item.get(entity_id=args.qid)
    old_labels = item.labels.get_json()
    old_descriptions = item.descriptions.get_json()
    old_factgrid_values = claim_values(item, FACTGRID_ITEM_ID_PROPERTY)

    print(f"Repair target: {args.qid}")
    print(f"Current labels: {old_labels}")
    print(f"Current descriptions: {old_descriptions}")
    print(f"Current {FACTGRID_ITEM_ID_PROPERTY} values: {old_factgrid_values}")
    print(f"New label: {args.label}")
    print(f"New aliases: {args.aliases}")
    print(f"New {FACTGRID_ITEM_ID_PROPERTY}: {NEW_FACTGRID_QID}")

    if args.dry_run:
        print("DRY_RUN: no changes written.")
        return

    item.labels.set(language="en", value=args.label)
    item.descriptions.set(language="en", value=args.description)
    aliases = [part.strip() for part in args.aliases.split("|") if part.strip()]
    if aliases:
        item.aliases.set(language="en", values=aliases, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)

    if args.replace_factgrid_id:
        item.claims.remove(FACTGRID_ITEM_ID_PROPERTY)
        item.claims.add(
            datatypes.ExternalID(prop_nr=FACTGRID_ITEM_ID_PROPERTY, value=NEW_FACTGRID_QID),
            action_if_exists=ActionIfExists.APPEND_OR_REPLACE,
        )

    robust_write(item, f"Repair Mari finding-spot authority item {args.qid}")
    print(f"Repaired {args.qid} as {args.label}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qid", default=DEFAULT_QID)
    parser.add_argument("--label", default="Mari (mod. Tell Hariri)")
    parser.add_argument(
        "--description",
        default="CDLI provenience / finding spot authority value for Mari (mod. Tell Hariri), CDLI provenience 161; aligned with FactGrid Q389896.",
    )
    parser.add_argument("--aliases", default="Mari|Tell Hariri|Tall Hariri|Tall Ḥarīrī")
    parser.add_argument("--replace-factgrid-id", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    repair(args)


if __name__ == "__main__":
    main()
