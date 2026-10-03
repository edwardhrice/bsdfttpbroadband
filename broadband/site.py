"""Write the data files the static site reads (docs/data/). Public data only."""
import csv
import json
import shutil
from datetime import datetime, timezone

from . import config as C


def load_coords(path=C.COORDS_CSV):
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["uprn"]: r for r in csv.DictReader(f) if r["latitude"] and r["longitude"]}


def write_last_check(release_id, now=None):
    """Record that the release was checked. Written on every run, so the weekly job always has a change to commit."""
    now = now or datetime.now(timezone.utc)
    C.DOCS_DATA.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"last_checked": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "release_id": release_id}, indent=2) + "\n"
    C.LAST_CHECK_JSON.write_text(text, encoding="utf-8")
    (C.DOCS_DATA / "last_check.json").write_text(text, encoding="utf-8")


def build_site():
    C.DOCS_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(C.SUMMARY_JSON, C.DOCS_DATA / "summary.json")
    shutil.copyfile(C.HISTORY_CSV, C.DOCS_DATA / "history.csv")
    coords = load_coords()
    points = []
    with open(C.PREMISES_CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            c = coords.get(r["uprn"])
            if c:
                points.append({
                    "uprn": r["uprn"], "postcode": r["postcode"], "status": r["status"],
                    "lat": round(float(c["latitude"]), 6), "lon": round(float(c["longitude"]), 6),
                })
    with open(C.DOCS_DATA / "points.json", "w", encoding="utf-8") as f:
        json.dump(points, f, separators=(",", ":"), ensure_ascii=False)
    return len(points)
