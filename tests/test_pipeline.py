"""Run with:  python -m unittest discover -s tests -v"""
import csv
import json
import subprocess
import unittest
from collections import Counter
from pathlib import Path

from broadband import config as C
from broadband.build import map_rows
from broadband.status import (AVAILABLE, NOT_COUNTED, NOT_PLANNED, PLANNED_COMMERCIAL,
                              PLANNED_GIS, PREMISES_COLUMNS, map_status, summarise)

FIXTURE = Path(__file__).parent / "fixtures" / "bduk_2026_05_parish_raw.csv"
CFG = C.load_config()


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def raw(**kw):
    base = {"uprn": "1", "postcode": "TA11 6DD", "bduk_recognised_premises": "true",
            "subsidy_control_status": "Gigabit White", "current_gigabit": "false",
            "future_gigabit": "false", "bduk_gis": "false", "bduk_gis_contract_scope": "",
            "bduk_gis_final_coverage_date": "", "bduk_gis_contract_name": "",
            "bduk_gis_supplier": "", "bduk_vouchers": "false", "bduk_vouchers_supplier": ""}
    base.update(kw)
    return base


class StatusMapping(unittest.TestCase):
    def test_not_recognised_wins_over_everything(self):
        r = map_status(raw(bduk_recognised_premises="false", current_gigabit="true", bduk_gis="true"))
        self.assertEqual(r["status"], NOT_COUNTED)

    def test_available_now_beats_planned_and_records_voucher_supplier(self):
        r = map_status(raw(current_gigabit="true", bduk_gis="true", bduk_vouchers="true",
                           bduk_vouchers_supplier="Openreach Limited"))
        self.assertEqual(r["status"], AVAILABLE)
        self.assertEqual(r["voucher_supplier"], "Openreach Limited")

    def test_available_without_voucher_has_no_supplier(self):
        r = map_status(raw(current_gigabit="true", bduk_vouchers_supplier="Ignored"))
        self.assertEqual(r["voucher_supplier"], "")

    def test_project_gigabit_details_keep_subsidy_classification(self):
        gis = dict(bduk_gis="true", bduk_gis_supplier="Wessex Internet Ltd",
                   bduk_gis_final_coverage_date="2029-09-30", bduk_gis_contract_scope="Initial",
                   future_gigabit="true")
        r = map_status(raw(subsidy_control_status="Gigabit Under Review", **gis))
        self.assertEqual(r["status"], PLANNED_GIS)
        self.assertEqual((r["gis_supplier"], r["gis_final_coverage_date"], r["gis_contract_scope"]),
                         ("Wessex Internet Ltd", "2029-09-30", "Initial"))
        self.assertNotIn("gis_confirmation", r)
        self.assertEqual(r["subsidy_control_status"], "Gigabit Under Review")

    def test_commercial_plan(self):
        self.assertEqual(map_status(raw(future_gigabit="true"))["status"], PLANNED_COMMERCIAL)

    def test_not_planned_notes_white_eligibility(self):
        r = map_status(raw())
        self.assertEqual(r["status"], NOT_PLANNED)
        self.assertEqual(r["subsidy_note"], "eligible for public subsidy")
        self.assertEqual(map_status(raw(subsidy_control_status="Gigabit Grey/Black"))["subsidy_note"], "")


class RegressionMay2026(unittest.TestCase):
    """Counts the pipeline must reproduce for the May 2026 release."""

    @classmethod
    def setUpClass(cls):
        cls.raw = [r for r in read(FIXTURE) if r["postcode"] in set(CFG["postcodes"])]
        cls.records = map_rows(cls.raw)
        cls.summary = summarise(cls.records, CFG["postcodes"])

    def test_totals(self):
        self.assertEqual(self.summary["total_premises"], 266)
        # The brief expected 263 recognised / 3 not recognised, but the release has
        # four unrecognised premises (two at TA11 6DB), so 262 / 4.
        self.assertEqual(self.summary["recognised_premises"], 262)

    def test_available_now(self):
        self.assertEqual(self.summary["by_status"][AVAILABLE], 9)
        self.assertEqual(self.summary["vouchers"], [{"postcode": "TA11 6BJ", "supplier": "Openreach Limited"}])

    def test_project_gigabit_wessex(self):
        gis = [r for r in self.records if r["status"] == PLANNED_GIS]
        self.assertEqual(len(gis), 29)
        self.assertEqual({r["gis_supplier"] for r in gis}, {"Wessex Internet Ltd"})
        self.assertEqual({r["gis_final_coverage_date"] for r in gis}, {"2029-09-30"})
        self.assertEqual({r["gis_contract_scope"] for r in gis}, {"Initial"})
        self.assertEqual(Counter(r["postcode"] for r in gis),
                         {"TA11 6DD": 12, "TA11 6DF": 10, "TA11 6GS": 5, "TA11 6DB": 2})

    def test_not_counted(self):
        nc = [r["postcode"] for r in self.records if r["status"] == NOT_COUNTED]
        self.assertEqual(self.summary["by_status"][NOT_COUNTED], 4)
        self.assertEqual(Counter(nc), {"TA11 6DA": 1, "TA11 6DB": 2, "TA11 6DF": 1})

    def test_subsidy_status_counts(self):
        self.assertEqual(self.summary["by_subsidy_status"],
                         {"Gigabit Grey/Black": 9, "Gigabit Under Review": 29, "Gigabit White": 228})

    def test_every_premises_has_exactly_one_status(self):
        self.assertEqual(sum(self.summary["by_status"].values()), 266)


class PostcodeCoverage(unittest.TestCase):
    def assert_all_postcodes_present(self, rows, label):
        counts = Counter(r["postcode"] for r in rows)
        empty = [pc for pc in CFG["postcodes"] if counts[pc] == 0]
        self.assertEqual(empty, [], f"configured postcodes with zero rows in {label}")

    def test_config_has_20_distinct_postcodes(self):
        self.assertEqual(len(CFG["postcodes"]), 20)
        self.assertEqual(len(set(CFG["postcodes"])), 20)

    def test_fixture_covers_every_postcode(self):
        self.assert_all_postcodes_present(read(FIXTURE), "May 2026 fixture")

    def test_current_data_covers_every_postcode(self):
        self.assert_all_postcodes_present(read(C.PREMISES_CSV), "data/premises.csv")


class OutputsAndPrivacy(unittest.TestCase):
    def test_premises_csv_columns_and_unique_uprns(self):
        rows = read(C.PREMISES_CSV)
        self.assertEqual(list(rows[0].keys()), PREMISES_COLUMNS)
        self.assertFalse([c for c in rows[0] if "address" in c.lower()])
        self.assertEqual(len({r["uprn"] for r in rows}), len(rows))

    def test_summary_matches_premises(self):
        summary = json.loads(C.SUMMARY_JSON.read_text(encoding="utf-8"))
        rows = read(C.PREMISES_CSV)
        self.assertEqual(summary["total_premises"], len(rows))
        self.assertEqual(sum(summary["by_status"].values()), len(rows))

    def test_history_has_row_for_current_release(self):
        summary = json.loads(C.SUMMARY_JSON.read_text(encoding="utf-8"))
        ids = [r["release_id"] for r in read(C.HISTORY_CSV)]
        self.assertEqual(ids.count(summary["release"]["content_id"]), 1)

    def test_every_premises_has_a_coordinate_lookup_row(self):
        looked_up = {r["uprn"] for r in read(C.COORDS_CSV)}
        missing = {r["uprn"] for r in read(C.PREMISES_CSV)} - looked_up
        self.assertEqual(missing, set(), "run: python -m broadband.coords")

    def test_private_folder_is_gitignored_and_untracked(self):
        self.assertIn("private/", (C.ROOT / ".gitignore").read_text().splitlines())
        tracked = subprocess.run(["git", "ls-files", "private"], cwd=C.ROOT, capture_output=True,
                                 text=True).stdout.strip()
        self.assertEqual(tracked, "")

    def test_last_check_is_written_and_mirrored_to_site(self):
        from datetime import datetime, timezone
        from broadband import site
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            old = (C.LAST_CHECK_JSON, C.DOCS_DATA)
            C.LAST_CHECK_JSON, C.DOCS_DATA = Path(d) / "last_check.json", Path(d) / "docs"
            try:
                site.write_last_check("abc", datetime(2026, 10, 5, 6, 17, tzinfo=timezone.utc))
                a = json.loads(C.LAST_CHECK_JSON.read_text())
                b = json.loads((C.DOCS_DATA / "last_check.json").read_text())
            finally:
                C.LAST_CHECK_JSON, C.DOCS_DATA = old
        self.assertEqual(a, b)
        self.assertEqual(a, {"last_checked": "2026-10-05T06:17:00Z", "release_id": "abc"})


if __name__ == "__main__":
    unittest.main()
