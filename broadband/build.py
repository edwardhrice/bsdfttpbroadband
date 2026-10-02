"""Turn raw BDUK rows into data/ outputs (premises, summary, history)."""
import csv
import json
from datetime import datetime, timezone

from . import config as C
from .status import PREMISES_COLUMNS, STATUSES, SLUG, csv_value, map_status, summarise

HISTORY_COLUMNS = (
    ["release_id", "data_month", "published", "total_premises", "recognised_premises"]
    + [slug for _, slug in STATUSES]
    + ["subsidy_white", "subsidy_under_review", "subsidy_grey_black"]
)


def map_rows(raw_rows):
    records = [map_status(r) for r in raw_rows]
    records.sort(key=lambda r: (r["postcode"], int(r["uprn"])))
    uprns = [r["uprn"] for r in records]
    if len(uprns) != len(set(uprns)):
        raise RuntimeError("Duplicate UPRNs in BDUK rows")
    return records


def history_row(release, summary):
    sub = summary["by_subsidy_status"]
    row = {
        "release_id": release["content_id"],
        "data_month": release["data_month"],
        "published": release["published"],
        "total_premises": summary["total_premises"],
        "recognised_premises": summary["recognised_premises"],
        "subsidy_white": sub.get("Gigabit White", 0),
        "subsidy_under_review": sub.get("Gigabit Under Review", 0),
        "subsidy_grey_black": sub.get("Gigabit Grey/Black", 0),
    }
    for status, slug in STATUSES:
        row[slug] = summary["by_status"][status]
    return row


def read_history(path=C.HISTORY_CSV):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def upsert_history(row, path=C.HISTORY_CSV):
    """Append a release's counts; re-running the same release replaces its row."""
    rows = [r for r in read_history(path) if r["release_id"] != row["release_id"]]
    rows.append({k: str(v) for k, v in row.items()})
    rows.sort(key=lambda r: r["published"])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, HISTORY_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_premises(records, path=C.PREMISES_CSV):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, PREMISES_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in records:
            w.writerow({k: csv_value(r[k]) for k in PREMISES_COLUMNS})


def build_outputs(raw_rows, release, cfg, checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc)
    records = map_rows(raw_rows)
    summary = summarise(records, cfg["postcodes"])
    summary = {
        "parish": cfg["parish"],
        "release": {k: release[k] for k in
                    ("content_id", "title", "data_month", "published", "page_url",
                     "zip_url", "user_guide_url")},
        "checked_at": checked_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        **summary,
    }
    C.DATA.mkdir(exist_ok=True)
    write_premises(records)
    with open(C.SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")
    upsert_history(history_row(release, summary))
    with open(C.RELEASE_JSON, "w", encoding="utf-8") as f:
        json.dump({k: release[k] for k in
                   ("content_id", "base_path", "title", "data_month", "published", "zip_url")},
                  f, indent=2)
        f.write("\n")
    return records, summary
