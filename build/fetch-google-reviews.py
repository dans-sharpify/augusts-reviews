# -*- coding: utf-8 -*-
"""Refresh build/google-reviews.json — the salon's Google reviews.

    python build/fetch-google-reviews.py                  # full harvest via Apify
    python build/fetch-google-reviews.py --dry-run        # show what would change
    python build/fetch-google-reviews.py --source places  # Google's own API (needs a card)
    python build/fetch-google-reviews.py --dataset <id>   # re-read a past run, free

Stdlib only, on purpose: this runs inside the Netlify build container, where a
`pip install` is one more thing that can fail on a Tuesday.


WHY THERE ARE TWO SOURCES, AND WHY apify IS THE DEFAULT
-------------------------------------------------------
`apify` (default) — the `compass/Google-Maps-Reviews-Scraper` actor. Walks the
WHOLE list and returns every review, which is why it seeded this file and why it
is now also the scheduled source. Apify's free plan needs **no credit card** and
includes $5 of platform credit a month; the actor bills PAY_PER_EVENT at $0.0006
per review, so ~85 reviews is about **$0.05 a run** — a weekly refresh spends
roughly $0.22 of that $5. `maxTotalChargeUsd` caps each run regardless.
The honest caveat: this is scraping, which Google's Maps terms do not invite.

`places` — Google's own Places API (New). Official and free at this cadence
(1,000 free calls a month on the `reviews` SKU, and a weekly refresh is four),
but **Google requires a billing account on every Maps Platform key even inside
the free tier**, which ruled it out here. It also only returns a handful of
reviews (five, in practice) with no pagination, so it can keep the page current
but cannot rebuild the archive.

If a card is ever acceptable, `--source places` is the cleaner long-term answer.
The fully-official card-free alternative is the **Google Business Profile API**,
which returns everything and lets the salon reply — but it needs an access-request
form approved by Google plus OAuth refresh-token plumbing, so it is a project
rather than a setting.

Either way the JSON in this directory is the durable archive and the merge below
NEVER deletes, so a refresh can only ever add.


THE ONE RULE ABOUT THE TEXT
---------------------------
We store `originalText` — the reviewer's own words in the language they wrote
them. The Places API will happily hand back `text` machine-translated into
whatever `languageCode` we asked for, and publishing that under a real person's
name on the salon's own site is putting words in their mouth. The renderer tags
each card with its `lang` instead. Rating-only reviews (no text at all) are not
stored: there is nothing to render, and they are already counted in the average.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "google-reviews.json"

# Frizierdarbnīca AUGUSTS, Miera iela 19, Rīga.
# place_id is the stable, documented identifier and the only one both the API and
# Google's own review URLs accept. cid/fid are what Maps URLs carry; kept because
# the Apify actor takes a cid URL and because they are how you find the place
# again if the place_id is ever lost.
PLACE_ID = "ChIJR-MLMsHP7kYRfQuq0DiyK4M"
CID = "9451844200055835517"
FID = "0x46eecfc1320be347:0x832bb238d0aa0b7d"

APIFY_ACTOR = "compass~Google-Maps-Reviews-Scraper"

# Reviews below this never render. See "MODERATION" in the README: the page is a
# testimonial wall, and the live 4.9/83 stat plus the "read them all on Google"
# link next to it is what keeps that honest — the full picture is one click away
# and always current, because it is Google's page, not ours.
MIN_RATING = 4

# Individual reviews to keep off the page regardless of rating (spam, a name the
# person asked us to remove, a review Google has since taken down). Review ids,
# one per line, with a note.
HIDDEN = {
    # "Ci9DQUlRQUNvZENo…": "asked us by email on 2026-xx-xx",
}


def log(msg):
    print(f"  {msg}")


# --------------------------------------------------------------------- the file
def load():
    if not OUT.exists():
        return {"place": {}, "reviews": []}
    return json.loads(OUT.read_text(encoding="utf-8"))


def iso_day(ts):
    """'2026-08-03T14:28:57.236Z' -> '2026-08-03'. Google gives sub-second
    precision on a haircut; the page shows a date."""
    return (ts or "")[:10] or None


def norm_lang(code):
    """'lv-LV' -> 'lv'. The renderer puts this in a lang="" attribute, and a
    region subtag there is noise at best and wrong at worst ('en-GB' on a review
    written by a Latvian typing English)."""
    return (code or "").split("-")[0].lower() or None


def clean(text):
    """Collapse the runs of blank lines people leave in a review box, and strip
    trailing space. Paragraph breaks survive — they are the only formatting the
    renderer understands."""
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", t)


# ------------------------------------------------------------------ places API
def from_places(key, language="lv"):
    """Place Details (New). `languageCode` only affects Google's own translated
    `text`, which we throw away — but it is required to be something, and asking
    for Latvian keeps the discarded field small for a mostly-Latvian place."""
    fields = ",".join([
        "id", "displayName", "rating", "userRatingCount",
        "googleMapsUri", "reviews",
    ])
    url = (f"https://places.googleapis.com/v1/places/{PLACE_ID}"
           f"?fields={urllib.parse.quote(fields)}&languageCode={language}")
    req = urllib.request.Request(url, headers={"X-Goog-Api-Key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))

    place = {
        "name": (data.get("displayName") or {}).get("text"),
        "rating": data.get("rating"),
        "count": data.get("userRatingCount"),
    }
    out = []
    for rv in data.get("reviews", []):
        # `originalText` is the reviewer's own words; `text` may be Google's
        # translation of them. Fall back to `text` only when Google gives no
        # original, which happens when the review was already in `language`.
        body = rv.get("originalText") or rv.get("text") or {}
        author = rv.get("authorAttribution") or {}
        out.append({
            # "places/<place>/reviews/<id>" — the last segment is the same id
            # the Apify harvest reports, so the two sources merge cleanly.
            "id": (rv.get("name") or "").rsplit("/", 1)[-1],
            "name": author.get("displayName"),
            "rating": rv.get("rating"),
            "date": iso_day(rv.get("publishTime")),
            "lang": norm_lang(body.get("languageCode")),
            "text": clean(body.get("text")),
        })
    return place, out, "places-api"


# ------------------------------------------------------------------ apify path
def _apify_get(path, token, **params):
    if token:
        params["token"] = token
    url = f"https://api.apify.com/v2/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def _apify_run(token):
    """Start the actor, wait for it, return its dataset items.

    ASYNC, NOT `run-sync-get-dataset-items`. The sync endpoint holds the HTTP
    connection open for the whole scrape and gives up at 300 s; walking ~85
    reviews takes a couple of minutes and would sit uncomfortably close to that
    ceiling, with nothing to show for it if it tripped — the run keeps going and
    bills, the caller just never sees the data. Start / poll / fetch instead.

    `maxTotalChargeUsd` is a real safety net, not decoration: the actor bills
    PAY_PER_EVENT at $0.0006 per review, so a normal run is about $0.05. The cap
    means a runaway (a search URL that matched a thousand places, say) stops
    instead of eating the month's free credit."""
    payload = json.dumps({
        # cid, not a search URL: it pins the run to exactly one place, which is
        # also what keeps the bill predictable.
        "startUrls": [{"url": f"https://www.google.com/maps?cid={CID}"}],
        "maxReviews": 500,
        "reviewsSort": "newest",
        "language": "lv",
        "reviewsOrigin": "google",
        "personalData": True,
    }).encode()
    opts = urllib.parse.urlencode({
        "token": token,
        "timeout": 900,
        "maxTotalChargeUsd": "0.50",
    })
    req = urllib.request.Request(
        f"https://api.apify.com/v2/acts/{APIFY_ACTOR}/runs?{opts}",
        data=payload, headers={"Content-Type": "application/json"})
    run = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())["data"]
    run_id, dataset_id = run["id"], run["defaultDatasetId"]
    log(f"apify run {run_id} started — walking the review list, ~1-2 min")

    # Poll rather than sleep-and-hope. Terminal states per the Apify API.
    for attempt in range(120):
        time.sleep(5)
        status = _apify_get(f"actor-runs/{run_id}", token)["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT", "TIMING-OUT"):
            raise RuntimeError(
                f"apify run {run_id} ended {status} — see "
                f"https://console.apify.com/actors/runs/{run_id}")
        if attempt and attempt % 12 == 0:
            log(f"  still {status}…")
    else:
        raise RuntimeError(f"apify run {run_id} did not finish in 10 minutes")

    return _apify_get(f"datasets/{dataset_id}/items", token,
                      clean="true", format="json")


def from_apify(token, dataset=None, local=None):
    """Whole-list harvest. `--dataset` reads a run that already happened (the
    seed came in this way, and re-reading a dataset costs nothing); `--file`
    reads a dump off disk; otherwise a fresh run is started and waited on."""
    if local:
        items = json.loads(pathlib.Path(local).read_text(encoding="utf-8"))
        origin = f"apify-dump:{pathlib.Path(local).name}"
    elif dataset:
        items = _apify_get(f"datasets/{dataset}/items", token, clean="true", format="json")
        origin = f"apify-dataset:{dataset}"
    else:
        if not token:
            raise RuntimeError("APIFY_TOKEN is not set")
        items = _apify_run(token)
        origin = f"apify-run:{APIFY_ACTOR}"
    if not items:
        raise RuntimeError("the harvest came back empty — refusing to treat that as "
                           "'no reviews'; the archive is left alone")

    place, out = {}, []
    for rv in items:
        place = {
            "name": rv.get("title") or place.get("name"),
            "rating": rv.get("totalScore", place.get("rating")),
            "count": rv.get("reviewsCount", place.get("count")),
        }
        out.append({
            "id": rv.get("reviewId"),
            "name": rv.get("name"),
            "rating": rv.get("stars"),
            "date": iso_day(rv.get("publishedAtDate")),
            # the actor reports the detected language of the review itself
            "lang": norm_lang(rv.get("originalLanguage")),
            "text": clean(rv.get("text")),
        })
    return place, out, origin


# ---------------------------------------------------------------------- merge
def merge(old, place, fresh, origin, prune=False):
    """Fold `fresh` into `old`, keyed on review id.

    Additive by default. `places` can only ever see the newest handful, so a
    subtractive merge would delete the archive down to five reviews the first
    time it ran — and it would look like it had worked."""
    by_id = {r["id"]: r for r in old.get("reviews", []) if r.get("id")}
    before = set(by_id)

    kept, skipped_empty, bad = 0, 0, 0
    for r in fresh:
        if not r.get("id"):
            bad += 1
            continue
        if not r.get("text"):
            # A rating with no words. Counted in the average, nothing to show.
            skipped_empty += 1
            continue
        by_id[r["id"]] = r
        kept += 1

    if prune:
        seen = {r["id"] for r in fresh if r.get("id")}
        for gone in before - seen:
            by_id.pop(gone)

    reviews = sorted(by_id.values(), key=lambda r: (r.get("date") or "", r.get("id")),
                     reverse=True)
    added = sorted(set(by_id) - before)
    removed = sorted(before - set(by_id))

    doc = {
        "_comment": ("Generated by build/fetch-google-reviews.py — do not hand-edit "
                     "the reviews. To take one down, add its id to HIDDEN in that "
                     "script and rerun build/assemble.py."),
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": origin,
        "place": {
            "name": place.get("name") or old.get("place", {}).get("name"),
            "place_id": PLACE_ID,
            "cid": CID,
            "fid": FID,
            # The live figures — these cover ALL the reviews, including the
            # rating-only ones and the ones the page does not show.
            "rating": place.get("rating") or old.get("place", {}).get("rating"),
            "count": place.get("count") or old.get("place", {}).get("count"),
            # Google's own short URL forms. Both take a place_id and nothing
            # else, which is why the place_id is the identifier worth keeping.
            "write_review_url": f"https://search.google.com/local/writereview?placeid={PLACE_ID}",
            "all_reviews_url": f"https://search.google.com/local/reviews?placeid={PLACE_ID}",
            "maps_url": f"https://www.google.com/maps?cid={CID}",
        },
        "reviews": reviews,
    }
    stats = dict(seen=kept, empty=skipped_empty, unusable=bad,
                 added=added, removed=removed, total=len(reviews))
    return doc, stats


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", choices=("apify", "places"), default="apify")
    ap.add_argument("--dataset", help="apify: read an existing dataset id instead of running the actor")
    ap.add_argument("--file", help="apify: read a dataset dump off disk")
    ap.add_argument("--language", default="lv", help="places: languageCode to request")
    ap.add_argument("--prune", action="store_true",
                    help="drop reviews the source no longer reports (only safe with --source apify)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if the refresh could not run (default is to warn and keep the file)")
    args = ap.parse_args()

    if args.prune and args.source != "apify":
        sys.exit("--prune with --source places would delete the archive down to the "
                 "five reviews the API returns. Refusing.")

    old = load()
    print(f"\nGOOGLE REVIEWS  ({args.source})")
    log(f"archive on disk: {len(old.get('reviews', []))} review(s)"
        + (f", last fetched {old.get('fetched')}" if old.get("fetched") else ""))

    try:
        if args.source == "places":
            key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
            if not key:
                raise RuntimeError("GOOGLE_MAPS_API_KEY is not set")
            place, fresh, origin = from_places(key, args.language)
        else:
            place, fresh, origin = from_apify(
                os.environ.get("APIFY_TOKEN", "").strip(), args.dataset, args.file)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, ValueError) as e:
        detail = ""
        if isinstance(e, urllib.error.HTTPError):
            # Pull Google's own `error.message` out rather than dumping the first
            # 400 characters of the body: the useful sentence ("API key not valid",
            # "Places API (New) has not been used in project N before or it is
            # disabled") sits AFTER a wall of @type/domain/metadata boilerplate, so
            # a naive truncation shows you everything except the reason.
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
                err = json.loads(body).get("error", {})
                if err.get("message"):
                    detail = f" — {err.get('status', e.code)}: {err['message']}"
            except Exception:
                pass
            if not detail and body:
                detail = " — " + body[:400]
        msg = f"could not refresh from {args.source}: {e}{detail}"
        # A build must not fail because Google had a bad minute. The committed
        # archive is a complete, valid dataset on its own.
        if args.strict:
            sys.exit(f"  ERROR {msg}")
        log(f"WARN  {msg}")
        log("keeping the archive as it is — the page still renders every review in it")
        return 0

    doc, st = merge(old, place, fresh, origin, args.prune)
    log(f"source returned {len(fresh)} review(s): {st['seen']} with text, "
        f"{st['empty']} rating-only (not stored)"
        + (f", {st['unusable']} with no id (dropped)" if st["unusable"] else ""))
    log(f"place: {doc['place']['name']} — {doc['place']['rating']} from "
        f"{doc['place']['count']} Google review(s)")
    for rid in st["added"]:
        r = next(x for x in doc["reviews"] if x["id"] == rid)
        log(f"  + {r['date']}  {r['rating']}*  {r['name']}: {(r['text'] or '')[:60]}…")
    for rid in st["removed"]:
        log(f"  - {rid}")
    if not st["added"] and not st["removed"]:
        log("no new reviews")
    log(f"archive now: {st['total']} review(s)")

    # Tell GitHub Actions whether anything REAL moved, so the commit message can
    # tell the truth. `fetched` and `source` change on every successful run, so the
    # file is always dirty and "did git see a diff?" cannot answer this.
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        changed = bool(st["added"] or st["removed"])
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"changed={'true' if changed else 'false'}\n")
            fh.write(f"added={len(st['added'])}\n")
            fh.write(f"removed={len(st['removed'])}\n")
            fh.write(f"total={st['total']}\n")
            fh.write(f"rating={doc['place'].get('rating')}\n")
            fh.write(f"count={doc['place'].get('count')}\n")

    if args.dry_run:
        log("--dry-run: nothing written")
        return 0
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"wrote build/{OUT.name}")
    log("now run: python build/assemble.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
