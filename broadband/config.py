"""Paths and configuration."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "parish.json"
DATA = ROOT / "data"
DOCS = ROOT / "docs"
DOCS_DATA = DOCS / "data"
PRIVATE = ROOT / "private"

PREMISES_CSV = DATA / "premises.csv"
SUMMARY_JSON = DATA / "summary.json"
LAST_CHECK_JSON = DATA / "last_check.json"
HISTORY_CSV = DATA / "history.csv"
RELEASE_JSON = DATA / "release.json"
COORDS_CSV = DATA / "uprn_coords.csv"


def load_config(path=CONFIG_FILE):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["postcodes"] = [normalise_postcode(p) for p in cfg["postcodes"]]
    return cfg


def normalise_postcode(pc):
    pc = "".join(str(pc).upper().split())
    return f"{pc[:-3]} {pc[-3:]}" if len(pc) > 3 else pc
