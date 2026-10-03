"""Check for a new BDUK release and rebuild data + site if there is one.

    python -m broadband.update                # normal run (used by the Action)
    python -m broadband.update --force        # rebuild even if the release is unchanged
    python -m broadband.update --zip FILE     # use a local/alternative zip for the latest release
    python -m broadband.update --backfill     # also add earlier releases to history.csv
"""
import argparse
import json
import sys

from . import config as C
from .build import build_outputs, history_row, upsert_history, map_rows
from .fetch import parish_rows
from .release import latest_release, list_releases, resolve_release
from .site import build_site, write_last_check
from .status import summarise


def stored_release():
    if C.RELEASE_JSON.exists():
        return json.loads(C.RELEASE_JSON.read_text(encoding="utf-8"))
    return {}


def backfill(cfg, skip_id):
    for doc in sorted(list_releases(cfg), key=lambda d: d["public_updated_at"]):
        if doc["content_id"] == skip_id:
            continue
        try:
            rel = resolve_release(doc, cfg)
            rows = parish_rows(rel["zip_url"], cfg)
            summary = summarise(map_rows(rows), cfg["postcodes"])
            upsert_history(history_row(rel, summary))
            print(f"backfilled {rel['data_month']}: {summary['total_premises']} premises")
        except Exception as e:  # older releases may use a different layout
            print(f"skipped {doc['title']}: {e}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--zip", help="override the zip location (URL or local path)")
    ap.add_argument("--backfill", action="store_true")
    args = ap.parse_args(argv)

    cfg = C.load_config()
    release = latest_release(cfg)
    fetch_url = args.zip or release["zip_url"]
    if not args.force and not args.zip and stored_release().get("content_id") == release["content_id"]:
        write_last_check(release["content_id"])
        print(f"No new release: {release['title']} is already built. Recorded the check date.")
        return 0

    print(f"Building from {release['title']} ({release['published']})")
    rows = parish_rows(fetch_url, cfg)
    if not rows:
        raise SystemExit("No rows matched the configured postcodes; refusing to overwrite data.")
    present = {r["postcode"].strip() for r in rows}
    for pc in cfg["postcodes"]:
        if pc not in present:
            print(f"WARNING: no premises returned for {pc}", file=sys.stderr)
    _, summary = build_outputs(rows, release, cfg)
    if args.backfill:
        backfill(cfg, release["content_id"])
    n = build_site()
    write_last_check(release["content_id"])
    print(f"{summary['total_premises']} premises, {n} with map coordinates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
