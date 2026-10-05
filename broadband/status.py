"""Status mapping from a raw BDUK UPRN row, plus summary counting."""

NOT_COUNTED = "Not counted by BDUK"
AVAILABLE = "Available now"
PLANNED_GIS = "Planned – Project Gigabit"
PLANNED_COMMERCIAL = "Planned – commercial"
NOT_PLANNED = "Not planned"

# Display order; slugs are used as column names in history.csv.
STATUSES = [
    (AVAILABLE, "available_now"),
    (PLANNED_GIS, "planned_project_gigabit"),
    (PLANNED_COMMERCIAL, "planned_commercial"),
    (NOT_PLANNED, "not_planned"),
    (NOT_COUNTED, "not_counted"),
]
SLUG = dict(STATUSES)

UNDER_REVIEW = "Gigabit Under Review"
WHITE = "Gigabit White"

PREMISES_COLUMNS = [
    "uprn", "postcode", "status", "bduk_recognised_premises",
    "subsidy_control_status", "current_gigabit", "future_gigabit",
    "bduk_vouchers", "voucher_supplier",
    "bduk_gis", "gis_supplier", "gis_final_coverage_date",
    "gis_contract_scope", "gis_contract_name",
    "subsidy_note",
]


def truthy(v):
    return str(v).strip().lower() == "true"


def map_status(row):
    """Return the output record for one raw BDUK row (rules applied in order)."""
    subsidy = (row.get("subsidy_control_status") or "").strip()
    out = {
        "uprn": row["uprn"].strip(),
        "postcode": row["postcode"].strip(),
        "bduk_recognised_premises": truthy(row["bduk_recognised_premises"]),
        "subsidy_control_status": subsidy,
        "current_gigabit": truthy(row["current_gigabit"]),
        "future_gigabit": truthy(row["future_gigabit"]),
        "bduk_vouchers": truthy(row["bduk_vouchers"]),
        "voucher_supplier": "",
        "bduk_gis": truthy(row["bduk_gis"]),
        "gis_supplier": "",
        "gis_final_coverage_date": "",
        "gis_contract_scope": "",
        "gis_contract_name": "",
        "subsidy_note": "",
    }
    if not out["bduk_recognised_premises"]:
        out["status"] = NOT_COUNTED
    elif out["current_gigabit"]:
        out["status"] = AVAILABLE
        if out["bduk_vouchers"]:
            out["voucher_supplier"] = (row.get("bduk_vouchers_supplier") or "").strip()
    elif out["bduk_gis"]:
        out["status"] = PLANNED_GIS
        out["gis_supplier"] = (row.get("bduk_gis_supplier") or "").strip()
        out["gis_final_coverage_date"] = (row.get("bduk_gis_final_coverage_date") or "").strip()
        out["gis_contract_scope"] = (row.get("bduk_gis_contract_scope") or "").strip()
        out["gis_contract_name"] = (row.get("bduk_gis_contract_name") or "").strip()
    elif out["future_gigabit"]:
        out["status"] = PLANNED_COMMERCIAL
    else:
        out["status"] = NOT_PLANNED
        if subsidy == WHITE:
            out["subsidy_note"] = "eligible for public subsidy"
    return out


def csv_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def summarise(records, postcodes):
    """Counts by status / subsidy / postcode for a list of mapped records."""
    by_status = {s: 0 for s, _ in STATUSES}
    by_subsidy = {}
    by_postcode = {pc: {s: 0 for s, _ in STATUSES} for pc in postcodes}
    gis = {"premises": 0, "under_review": 0, "suppliers": set(),
           "final_coverage_dates": set(), "contract_scopes": set()}
    vouchers = []
    for r in records:
        by_status[r["status"]] += 1
        by_subsidy[r["subsidy_control_status"]] = by_subsidy.get(r["subsidy_control_status"], 0) + 1
        by_postcode.setdefault(r["postcode"], {s: 0 for s, _ in STATUSES})[r["status"]] += 1
        if r["status"] == PLANNED_GIS:
            gis["premises"] += 1
            gis["under_review"] += r["subsidy_control_status"] == UNDER_REVIEW
            gis["suppliers"].add(r["gis_supplier"])
            gis["final_coverage_dates"].add(r["gis_final_coverage_date"])
            gis["contract_scopes"].add(r["gis_contract_scope"])
        if r["voucher_supplier"]:
            vouchers.append({"postcode": r["postcode"], "supplier": r["voucher_supplier"]})
    gis = {k: sorted(v) if isinstance(v, set) else v for k, v in gis.items()}
    total = len(records)
    not_counted = by_status[NOT_COUNTED]
    return {
        "total_premises": total,
        "recognised_premises": total - not_counted,
        "by_status": by_status,
        "by_subsidy_status": dict(sorted(by_subsidy.items())),
        "by_postcode": dict(sorted(by_postcode.items())),
        "project_gigabit": gis,
        "vouchers": vouchers,
    }
