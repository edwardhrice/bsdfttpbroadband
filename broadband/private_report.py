"""Local-only: join a private address list to the public status data.

Reads  private/address_lookup.csv  (columns: address, UPRN)
Writes private/address_report.csv  (nothing is written to data/ or docs/)

    python -m broadband.private_report
"""
import csv
import sys
from collections import Counter

from . import config as C

LOOKUP = C.PRIVATE / "address_lookup.csv"
REPORT = C.PRIVATE / "address_report.csv"
COLUMNS = ["address", "uprn", "postcode", "status", "detail"]


def detail(r):
    bits = []
    if r["voucher_supplier"]:
        bits.append(f"voucher supplier: {r['voucher_supplier']}")
    if r["gis_supplier"]:
        bits.append(f"{r['gis_supplier']}, final coverage {r['gis_final_coverage_date']}, "
                    f"{r['gis_contract_scope']} scope, {r['gis_confirmation']}")
    if r["subsidy_note"]:
        bits.append(r["subsidy_note"])
    return "; ".join(bits)


def main():
    if not LOOKUP.exists():
        print(f"{LOOKUP.relative_to(C.ROOT)} not found; nothing to do.")
        return 0
    with open(C.PREMISES_CSV, newline="", encoding="utf-8") as f:
        premises = {r["uprn"]: r for r in csv.DictReader(f)}
    with open(LOOKUP, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cols = {h.strip().lower(): h for h in reader.fieldnames or []}
        if not {"address", "uprn"} <= cols.keys():
            raise SystemExit("private/address_lookup.csv needs columns: address, UPRN")
        entries = [(r[cols["address"]].strip(), r[cols["uprn"]].strip()) for r in reader]

    out, unmatched = [], []
    for address, uprn in entries:
        p = premises.get(uprn)
        if p is None:
            unmatched.append((address, uprn))
            out.append({"address": address, "uprn": uprn, "postcode": "", "status": "UPRN not in parish data", "detail": ""})
        else:
            out.append({"address": address, "uprn": uprn, "postcode": p["postcode"],
                        "status": p["status"], "detail": detail(p)})
    with open(REPORT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)

    print(f"Wrote {REPORT.relative_to(C.ROOT)} ({len(out)} addresses)")
    for status, n in Counter(r["status"] for r in out).most_common():
        print(f"  {n:4d}  {status}")
    for address, uprn in unmatched:
        print(f"  check: UPRN {uprn!r} ({address}) is not in the parish data", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
