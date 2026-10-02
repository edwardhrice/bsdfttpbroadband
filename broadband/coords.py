"""One-off: extract coordinates for the parish UPRNs from OS Open UPRN (OGL).

The OS file is ~600 MB zipped, so this only runs when data/premises.csv
contains UPRNs that data/uprn_coords.csv has not looked up yet.

    python -m broadband.coords                 # download OS Open UPRN if needed
    python -m broadband.coords --zip FILE      # use an already-downloaded zip
    python -m broadband.coords --retry-missing # also retry UPRNs OS had no coordinates for
"""
import argparse
import csv
import io
import sys
import zipfile

from . import config as C
from .http import download_to_tempfile, get_json

COLUMNS = ["uprn", "latitude", "longitude", "easting", "northing"]


def read_existing(path=C.COORDS_CSV):
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["uprn"]: r for r in csv.DictReader(f)}


def premises_uprns(path=C.PREMISES_CSV):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["uprn"] for r in csv.DictReader(f)}


def os_csv_zip_url(cfg):
    """Ask the OS Downloads API for the current GB CSV file (name changes each release)."""
    for d in get_json(cfg["source"]["os_open_uprn_downloads"]):
        if d["format"] == "CSV" and d["area"] == "GB":
            return d["url"]
    raise RuntimeError("OS Downloads API lists no GB CSV for OpenUPRN")


def extract(zip_file, wanted):
    found = {}
    with zipfile.ZipFile(zip_file) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(name) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            for r in reader:
                if r["UPRN"] in wanted:
                    found[r["UPRN"]] = {
                        "uprn": r["UPRN"], "latitude": r["LATITUDE"], "longitude": r["LONGITUDE"],
                        "easting": r["X_COORDINATE"], "northing": r["Y_COORDINATE"],
                    }
                    if len(found) == len(wanted):
                        break
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--zip", help="local OS Open UPRN CSV zip")
    ap.add_argument("--retry-missing", action="store_true")
    args = ap.parse_args(argv)

    existing = read_existing()
    done = {u for u, r in existing.items() if r["latitude"] or not args.retry_missing}
    todo = premises_uprns() - done
    if not todo:
        print("All UPRNs already have coordinates; nothing to do.")
        return 0

    print(f"Looking up {len(todo)} UPRN(s) in OS Open UPRN")
    if args.zip:
        found = extract(args.zip, todo)
    else:
        cfg = C.load_config()
        with download_to_tempfile(os_csv_zip_url(cfg)) as tmp:
            found = extract(tmp, todo)
    for u in todo:  # blank row = looked up, not in OS Open UPRN (yet)
        existing[u] = found.get(u, {"uprn": u, "latitude": "", "longitude": "", "easting": "", "northing": ""})
    keep = premises_uprns()
    rows = [existing[u] for u in sorted(existing, key=int) if u in keep]
    with open(C.COORDS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Found {len(found)}/{len(todo)}; wrote {len(rows)} rows to {C.COORDS_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
