"""Find the latest BDUK release via the GOV.UK Content API (no hard-coded URLs)."""
import re
from urllib.parse import urljoin

from .http import get_json

GOVUK = "https://www.gov.uk"


def list_releases(cfg):
    """All matching publications in the collection, newest first."""
    src = cfg["source"]
    coll = get_json(src["collection_api"])
    pat = re.compile(src["publication_title_pattern"], re.I)
    docs = [d for d in coll["links"].get("documents", []) if pat.search(d.get("title", ""))
            and not d.get("withdrawn")]
    docs.sort(key=lambda d: d["public_updated_at"], reverse=True)
    return docs


def resolve_release(doc, cfg):
    """Fetch a publication and pick the regional zip for this parish."""
    src = cfg["source"]
    pub = get_json(urljoin(GOVUK, doc["api_path"]))
    pat = re.compile(src["attachment_title_pattern"], re.I)
    zips = [a for a in pub["details"].get("attachments", [])
            if pat.search(a.get("title", "")) and a.get("url", "").lower().endswith(".zip")]
    if len(zips) != 1:
        raise RuntimeError(
            f"Expected exactly one '{src['attachment_title_pattern']}' zip in "
            f"{pub['title']!r}, found {len(zips)}")
    m = re.match(r"\s*(\w+ \d{4})\b", pub["title"])
    return {
        "content_id": pub["content_id"],
        "base_path": pub["base_path"],
        "page_url": urljoin(GOVUK, pub["base_path"]),
        "title": pub["title"],
        "data_month": m.group(1) if m else pub["title"],
        "published": pub["public_updated_at"][:10],
        "zip_url": zips[0]["url"],
        "user_guide_url": next(
            (urljoin(GOVUK, a["url"]) for a in pub["details"]["attachments"]
             if "user guide" in a.get("title", "").lower()), ""),
    }


def latest_release(cfg):
    docs = list_releases(cfg)
    if not docs:
        raise RuntimeError("No matching publication found in the collection")
    return resolve_release(docs[0], cfg)
