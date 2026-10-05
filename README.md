# Gigabit broadband in Barton St David

A community project supporting Barton St David Parish Council's campaign to bring full-fibre (FTTP) broadband to the village. It publishes, and automatically keeps up to date, the government's premises-level gigabit availability and plans for every premises in the parish.

- **Site:** published from `docs/` with GitHub Pages (see [Enabling Pages](#enabling-github-pages)).
- **Full-screen map:** `docs/map.html`, built for projectors: text size adjustable (A−/A+, or the `+`/`-`/`0` keys; remembered per browser) and a full-screen button.
- **Data:** [`data/`](data/) – `premises.csv`, `summary.json`, `history.csv`, `uprn_coords.csv`.

## Source

[BDUK](https://www.gov.uk/government/collections/open-market-review-omr-determinations-and-bduk-plans) (Building Digital UK) publishes premises-level data about every four months under the Open Government Licence v3.0. Each release is a GOV.UK publication called like "May 2026 OMR and premises in BDUK plans (England and Wales)". See its [user guide](https://www.gov.uk/government/publications/may-2026-omr-and-premises-in-bduk-plans-england-and-wales/uprn-level-release-user-guide-and-technical-note-for-premises-in-bduk-plans) for column definitions and caveats.

This project uses only that data and Ordnance Survey's OS Open UPRN (for map coordinates). It does not use or scrape the government's address checker.

## Method

1. The GOV.UK Content API lists the collection; the newest publication matching "OMR and premises in BDUK plans" is the latest release. Zip file names are never hard-coded, because they change between releases.
2. The South West zip is read with HTTP Range requests, so only the Somerset CSV is fetched and decompressed (about 4 MB of a 43 MB zip, and none of the other counties).
3. Rows are kept where the postcode is one of the 20 listed in [`config/parish.json`](config/parish.json).
4. Each row is given a status (below) and written to `data/premises.csv`; counts go to `data/summary.json` and one row per release is added to `data/history.csv`.
5. `data/uprn_coords.csv` holds OS Open UPRN coordinates for the parish UPRNs. It is looked up once and only again when new UPRNs appear.

Earlier releases were back-filled into `history.csv` so the chart has context (`python -m broadband.update --backfill --force`).

## Status mapping

Applied in this order; the first rule that matches wins.

| # | Rule | Status |
|---|------|--------|
| 1 | `bduk_recognised_premises` is false | **Not counted by BDUK** |
| 2 | `current_gigabit` is true | **Available now** (voucher supplier recorded if `bduk_vouchers` is true) |
| 3 | `bduk_gis` is true | **Planned – Project Gigabit** (supplier, final coverage date, contract scope) |
| 4 | `future_gigabit` is true | **Planned – commercial** |
| 5 | otherwise | **Not planned** (`Gigabit White` is noted as eligible for public subsidy) |

`premises.csv` has no postal addresses: they come from OS AddressBase / Royal Mail PAF and are not covered by the OGL.

## Caveats

BDUK plans are provisional. Dates can change, and BDUK does not guarantee the accuracy of the data. The site says so, and links to the [official checker](https://www.check-gigabit-broadband-availability.service.gov.uk/) for individual addresses.

Every weekly run writes `data/last_check.json` (and a copy in `docs/data/`) with the time of the check, so the site's "Last checked" date is genuine and the run always makes a small commit. Data files only change when there is a new release.

## Automation

[`.github/workflows/update.yml`](.github/workflows/update.yml) runs every Monday and on manual dispatch. It finds the latest release and compares its publication ID with `data/release.json`. If unchanged, it exits without committing. If new, it rebuilds the data, looks up coordinates for any new UPRNs, runs the tests and commits. If the tests fail (for example a configured postcode returns no rows), nothing is committed and the run goes red.

## Running locally

Python 3.10+ and the standard library only; no packages to install.

```
python -m broadband.update --force              # rebuild from the latest release
python -m broadband.update --zip some.zip       # use a local zip instead
python -m broadband.coords                      # coordinates for new UPRNs (downloads ~600 MB if needed)
python -m unittest discover -s tests -v         # tests
python -m http.server -d docs                   # preview the site at http://localhost:8000
```

### Tests

`tests/test_pipeline.py` checks the status rules and a regression on the May 2026 release (fixture in `tests/fixtures/`): 266 premises, 9 available now (1 Openreach voucher at TA11 6BJ), 29 Wessex Internet Project Gigabit premises (12 at TA11 6DD, 10 at 6DF, 5 at 6GS, 2 at 6DB; initial scope, final coverage 2029-09-30), subsidy counts 228 White / 29 Under Review / 9 Grey/Black. It also fails if any configured postcode returns zero rows.

The release has **4** premises not counted by BDUK (TA11 6DA, 6DB ×2, 6DF), so **262** are recognised. An earlier draft of the requirements said 3 and 263.

### Private address list (optional, never committed)

To map house names to status for council use, put `private/address_lookup.csv` (columns `address`, `UPRN`) in place and run:

```
python -m broadband.private_report
```

This writes `private/address_report.csv`. The `private/` folder is in `.gitignore`, a test checks nothing in it is tracked, and nothing from it is written to `data/` or `docs/`.

## Enabling GitHub Pages

Repository **Settings → Pages → Build and deployment**: Source "Deploy from a branch", Branch `main`, folder `/docs`. Also under **Settings → Actions → General → Workflow permissions**, allow "Read and write permissions" so the scheduled job can commit.

## Licences

- Code: [MIT](LICENSE).
- Data in `data/` and `docs/data/`: [OGL v3.0](data/LICENCE.md).
- Leaflet (`docs/vendor/`): BSD-2-Clause. Map tiles © OpenStreetMap contributors.

Contains public sector information licensed under the Open Government Licence v3.0. Contains OS data © Crown copyright and database right 2026.
