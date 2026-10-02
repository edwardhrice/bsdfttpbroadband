"""Stream the parish rows out of a regional BDUK zip."""
import csv
import io
import re
import zipfile

from .http import open_zip_source

REQUIRED_COLUMNS = {
    "uprn", "postcode", "bduk_recognised_premises", "subsidy_control_status",
    "current_gigabit", "future_gigabit", "bduk_gis", "bduk_gis_contract_scope",
    "bduk_gis_final_coverage_date", "bduk_gis_contract_name", "bduk_gis_supplier",
    "bduk_vouchers", "bduk_vouchers_supplier",
}


def parish_rows(zip_url, cfg):
    """Return raw BDUK rows whose postcode is in the configured list.

    Only the matching CSV member is read; other counties in the zip are
    never decompressed.
    """
    wanted = set(cfg["postcodes"])
    pattern = re.compile(cfg["source"]["csv_member_pattern"])
    src = open_zip_source(zip_url)
    try:
        with zipfile.ZipFile(src) as zf:
            members = [n for n in zf.namelist() if pattern.search(n)]
            if len(members) != 1:
                raise RuntimeError(f"Expected one CSV matching {pattern.pattern!r}, got {members}")
            with zf.open(members[0]) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                # Header case has varied between releases (e.g. "UPRN").
                reader.fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]
                missing = REQUIRED_COLUMNS - set(reader.fieldnames)
                if missing:
                    raise RuntimeError(f"BDUK file is missing expected columns: {sorted(missing)}")
                return [r for r in reader if r["postcode"].strip() in wanted]
    finally:
        src.close()
