# -*- coding: utf-8 -*-
"""Render build/google-reviews.json into the review page's Google wall.

Two sections' worth of markup come out of here:

  summary(lang)  the score block — the live 4.9 out of 83, the "write one on
                 Google" button and the link to read all of them on Google. It
                 sits in the review page's hero.
  render(lang)   the wall itself.

BUILD TIME, NOT FETCH TIME
--------------------------
The reviews are baked into the HTML rather than fetched by the browser: this is
the one page whose entire content is words, and a client-side fetch into an empty
<div> is invisible to a crawler. It also means no third-party widget script on the
page and nothing to lay out after first paint. `build/fetch-google-reviews.py`
refreshes the JSON; a GitHub Action runs it weekly and commits the result.

This is now the ONLY source of reviews on the site. The page used to also carry a
form that collected reviews with photographs into a moderation queue; the client
dropped it rather than keep a manual publish step, so everything now points at
Google, where a review is worth more to them anyway (it shows on Maps and feeds
local search).

THE TEXT IS VERBATIM AND NOT TRANSLATED
---------------------------------------
Every other string on this site exists twice, LV and EN, and the English page is
generated from the Latvian. These do not: a review is a named person's own
words, and running them through a string table would be inventing a quote. So
the same review text appears on both language pages, in whatever language it was
written in, with a `lang=` attribute on the paragraph so a screen reader
pronounces it correctly and the browser can offer its own translation. Only the
chrome around the cards — the heading, the score label, the button — is
translated, which is why it lives in STRINGS here rather than in i18n.py.

That is also why the section carries `data-verbatim`: assemble.py's sweep for
untranslated Latvian on the English pages skips it deliberately.

WHICH REVIEWS APPEAR
--------------------
Rating >= MIN_RATING (4, set in fetch-google-reviews.py), review has text, and
its id is not in HIDDEN. Rating-only reviews are never even stored — there is
nothing to show. The filtered-out ones are still in the 4.9 average and the "83
reviews" count in the summary, and the summary links straight to Google's own
list, which is complete and always current. Say that plainly to the client
rather than implying the page is every review they have.
"""
import html
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "google-reviews.json"

MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(iso, lang):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d:02d}.{m:02d}.{y}." if lang == "lv" else f"{d} {MONTHS_EN[m - 1]} {y}"


def stars_markup(n, label):
    """★★★★★ with the empty ones dimmed. The glyphs are aria-hidden and the real
    rating is an sr-only sentence — five separate star characters otherwise read
    out as "black star black star black star…"."""
    filled = "".join('<span class="star star--on">★</span>' for _ in range(n))
    empty = "".join('<span class="star">★</span>' for _ in range(5 - n))
    return (f'<span class="stars__out" aria-hidden="true">{filled}{empty}</span>'
            f'<span class="sr-only">{html.escape(label)}</span>')

# How many cards are open on arrival. The rest go inside a <details>, which
# keeps them in the HTML (so they are indexed and reachable with JS off) without
# making the page a 46-card scroll. A CSS `columns` container cannot be split
# across a <details> boundary, so each group gets its own.
LEAD = 12


STRINGS = {
    "lv": {
        "eyebrow": "Google atsauksmes",
        "title": "Ko saka klienti",
        "note": ("Šīs ir atsauksmes, ko klienti atstājuši mūsu Google profilā. "
                 "Tās nav rediģētas — katra ir tādā valodā un tādos vārdos, kā "
                 "uzrakstīta."),
        "score_label": "Vidējais vērtējums {rating} no 5, pamatojoties uz {count} Google atsauksmēm",
        "count": "{count} atsauksmes Google",
        "write": "Rakstīt atsauksmi Google",
        "readall": "Lasīt visas Google",
        "more": "Rādīt vēl {n} atsauksmes",
        "stars": "Novērtējums: {n} no 5",
    },
    "en": {
        "eyebrow": "Google reviews",
        "title": "What clients say",
        "note": ("These are the reviews clients have left on our Google profile. "
                 "Nothing is edited — each one is in the language and the words it "
                 "was written in."),
        "score_label": "Average rating {rating} out of 5, based on {count} Google reviews",
        "count": "{count} reviews on Google",
        "write": "Write a review on Google",
        "readall": "Read them all on Google",
        "more": "Show {n} more reviews",
        "stars": "Rating: {n} out of 5",
    },
}


def load():
    if not DATA.exists():
        return {"place": {}, "reviews": []}
    return json.loads(DATA.read_text(encoding="utf-8"))


def _num(value, lang):
    """4.9 -> "4,9" in Latvian. A decimal point in a Latvian rating reads as
    wrong the way "4,9" would in English."""
    text = f"{value:.1f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    return text.replace(".", ",") if lang == "lv" else text


def published(min_rating=4, hidden=()):
    """The reviews that render, newest first. The JSON is already sorted, but a
    hand-merged file might not be, and the order is what the page shows."""
    data = load()
    rows = [r for r in data.get("reviews", [])
            if (r.get("text") or "").strip()
            and (r.get("rating") or 0) >= min_rating
            and r.get("id") not in hidden]
    rows.sort(key=lambda r: (r.get("date") or "", r.get("id") or ""), reverse=True)
    return data.get("place", {}), rows


def _config():
    """MIN_RATING and HIDDEN live next to the fetch so there is ONE place that
    decides what is publishable, rather than a threshold here and a different
    one there. Imported lazily because that module parses argv at import time in
    older revisions and this one only needs two constants."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_fetch_google_reviews", HERE / "fetch-google-reviews.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.MIN_RATING, set(mod.HIDDEN)


def _card(r, s, lang):
    """One review. Everything from the JSON is escaped — it is a stranger's
    typing, and it arrived over the network. A blank line becomes a new
    paragraph and that is the whole markup vocabulary."""
    body = "".join(f"<p>{html.escape(p.strip())}</p>"
                   for p in re.split(r"\n\s*\n", r["text"].strip()) if p.strip())
    # A review written in Latvian shows on the English page too. Without lang=
    # a screen reader reads it with English phonemes and Chrome will not offer
    # to translate it.
    attr = f' lang="{html.escape(r["lang"])}"' if r.get("lang") else ""
    date = (f'<time class="rvcard__date num" datetime="{r["date"]}">'
            f'{fmt_date(r["date"], lang)}</time>') if r.get("date") else ""
    return "\n".join([
        '      <article class="rvcard">',
        f'        <div class="rvcard__top">'
        f'{stars_markup(int(r["rating"]), s["stars"].format(n=int(r["rating"])))}{date}</div>',
        f'        <div class="rvcard__body"{attr}>{body}</div>',
        # No "from Google" badge per card: the section heading already says so 46
        # times over, and `.rvcard__svc` is uppercased — which turned the Latvian
        # "No Google" ("from Google") into a card that read NO GOOGLE.
        f'        <p class="rvcard__who"><b>{html.escape(r.get("name") or "")}</b></p>',
        '      </article>',
    ])


def summary(lang):
    """The score block for the hero. Empty string if there is no data at all, so
    a missing JSON file degrades to the page as it was rather than to a 0.0."""
    place, rows = published(*_config())
    rating, count = place.get("rating"), place.get("count")
    if not rating or not count:
        return ""
    s = STRINGS[lang]
    label = s["score_label"].format(rating=_num(rating, lang), count=count)
    return "\n".join([
        '    <div class="gscore">',
        '      <svg class="gscore__g" viewBox="0 0 24 24" aria-hidden="true" focusable="false">',
        # Google's four-colour G, as paths rather than a hosted image: no
        # third-party request, no layout shift, and it stays crisp at any size.
        '        <path fill="#4285F4" d="M23.5 12.3c0-.9-.1-1.5-.2-2.2H12v4.2h6.6c-.1 1.1-.8 2.8-2.5 3.9l-.1.1 3.6 2.8.2.1c2.3-2.1 3.7-5.2 3.7-8.9z"/>',
        '        <path fill="#34A853" d="M12 24c3.2 0 5.9-1.1 7.9-2.9l-3.8-2.9c-1 .7-2.4 1.2-4.1 1.2-3.2 0-5.9-2.1-6.9-5l-.1.1-3.7 2.9-.1.1C3.2 21.3 7.3 24 12 24z"/>',
        '        <path fill="#FBBC05" d="M5.1 14.4c-.3-.8-.4-1.6-.4-2.4s.2-1.7.4-2.4V9.5L1.3 6.6l-.1.1C.4 8.3 0 10.1 0 12s.4 3.7 1.2 5.3l3.9-2.9z"/>',
        '        <path fill="#EA4335" d="M12 4.7c2.3 0 3.8 1 4.7 1.8l3.4-3.3C18 1.2 15.2 0 12 0 7.3 0 3.2 2.7 1.2 6.7l3.9 3c1-2.9 3.7-5 6.9-5z"/>',
        '      </svg>',
        f'      <p class="gscore__num num" aria-hidden="true">{_num(rating, lang)}</p>',
        f'      <div class="gscore__of">{stars_markup(round(rating), label)}',
        f'        <p class="gscore__count num" aria-hidden="true">{s["count"].format(count=count)}</p>',
        '      </div>',
        '    </div>',
    ])


def cta(lang):
    """The two Google links, for the hero's button row. Rendered here so the URL
    and the label can never drift apart: both come out of the same JSON."""
    place, _ = published(*_config())
    write, readall = place.get("write_review_url"), place.get("all_reviews_url")
    if not write:
        return ""
    s = STRINGS[lang]
    return "\n".join([
        f'      <a class="btn" href="{write}" target="_blank" rel="noopener">{s["write"]}</a>',
        f'      <a class="btn btn--ghost" href="{readall}" target="_blank" rel="noopener">{s["readall"]}</a>',
    ])


def render(lang):
    """The whole Google wall, or "" when the file holds nothing publishable."""
    place, rows = published(*_config())
    if not rows:
        return ""
    s = STRINGS[lang]

    def grid(items, extra=""):
        out = [f'    <div class="rvgrid{extra}">']
        out += [_card(r, s, lang) for r in items]
        out.append("    </div>")
        return out

    out = [
        # data-verbatim: the review text is deliberately NOT translated, so
        # assemble.py's "no Latvian on the English page" sweep skips this block.
        '<section class="section rvlist gwall" id="google-atsauksmes" data-verbatim>',
        '  <div class="wrap">',
        '    <div class="svc__head reveal">',
        '      <div>',
        f'        <p class="eyebrow">{s["eyebrow"]}</p>',
        f'        <h2 class="h-lg">{s["title"]}</h2>',
        '      </div>',
        f'      <p class="svc__note">{s["note"]}</p>',
        '    </div>',
    ]
    out += grid(rows[:LEAD], " reveal")
    rest = rows[LEAD:]
    if rest:
        # <details> and not a JS toggle: with the script gone the rest still
        # opens, and the markup is in the page either way.
        out += [
            '    <details class="gmore">',
            f'      <summary class="gmore__btn">{s["more"].format(n=len(rest))}'
            '<span aria-hidden="true">↓</span></summary>',
        ]
        out += grid(rest)
        out.append("    </details>")
    out += ["  </div>", "</section>"]
    return "\n".join(out)
