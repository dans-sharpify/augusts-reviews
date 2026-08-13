# -*- coding: utf-8 -*-
"""Assemble the seven shipped pages from three templates + the SVG partials.

    build/index.template.html    ->  site/index.html      (EN, the main page)
                                     site/lv.html         (LV)
    build/reviews.template.html  ->  site/reviews.html    (EN)
                                     site/atsauksmes.html (LV)
    build/thankyou.template.html ->  site/thank-you.html
                                     site/paldies.html
    build/404.template.html      ->  site/404.html        (English only)

English is the main language, Latvian the second variant. The Latvian copy is
the source of truth (it is the salon's own wording), so the English page is
produced from it by the string table in i18n.py rather than maintained by hand —
which keeps every non-text byte (the SVG blobs, the film's data-* beat timings,
srcset, class names) identical between the two.

The header and the footer are partials shared by the front page and the review
page: two hand-kept copies is how a nav item ends up on one page and not the
other.

Asserts, because all of these ship silently broken:
  * every @include placeholder was substituted
  * every translation pair's source actually occurs in the template
  * no {{TOKEN}} survives into a shipped page
  * the EN pages carry no leftover Latvian (diacritic sweep, allowlisted)
  * each EN/LV pair has the identical tag sequence — a pair that ate a <span> shows
  * no Latvian letter was written as a combining mark instead of precomposed
  * the traced-logo viewBoxes in the markup still match the symbols in logo.svg
  * every assets/... URL the pages ask for exists on disk
"""
import hashlib, pathlib, re, sys

import google_reviews
import i18n

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = ROOT / "site"

LV_DIACRITICS = "āĀēĒīĪūŪčČģĢķĶļĻņŅšŠžŽ"
COMBINING = re.compile(r"[̀-ͯ]")

# Dropping this file into site/assets/img/ is the whole switch from the drawn
# birch forest to a photographed one — see "The film's forest" in the README.
# `build/make-forest-photo.py` emits it.
FOREST_PHOTO = "assets/img/mezs-fons.webp"

fails = []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg):
    print(f"  ok    {msg}")


# --------------------------------------------------------------------- helpers
def apply_pairs(text, pairs, label):
    """Longest source first — otherwise a short fragment is replaced inside a
    longer phrase that contains it, leaving half-translated text behind."""
    missing = [src for src, _ in pairs if src not in text]
    if missing:
        for src in missing:
            fail(f"[{label}] pair source not found in template: {src[:90]!r}")
    for src, dst in sorted(pairs, key=lambda p: len(p[0]), reverse=True):
        text = text.replace(src, dst)
    return text


def substitute(text, values):
    for token in re.findall(r"\{\{(\w+)\}\}", text):
        if token not in values:
            fail(f"unknown placeholder {{{{{token}}}}} in template")
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", str(val))
    left = re.findall(r"\{\{\w+\}\}", text)
    if left:
        fail(f"unsubstituted placeholders {sorted(set(left))}")
    return text


_HASHES = {}


def asset_digest(path):
    """Content hash of a text asset, with line endings normalised out.

    NORMALISING IS THE WHOLE POINT. `.gitattributes` stores these files as LF and
    un-normalises on checkout, so `app.css` is CRLF in a Windows working tree and
    LF on the ubuntu-latest runner — and hashing the raw bytes therefore produced a
    DIFFERENT cache-buster on each platform (1e0652bf vs 4da4f8a4 for the same
    file). Every build on the other platform then rewrote all four pages, so the
    weekly Action would have committed a "refresh Google reviews" that changed
    nothing but a query string, forever.

    Line endings are not content for a stylesheet, and this value is only a cache
    key — it has to change when the CSS changes and stay put when it does not. It
    does not have to match the bytes actually served."""
    return hashlib.sha1(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:8]


def _digest(rel):
    if rel not in _HASHES:
        _HASHES[rel] = asset_digest(SITE / rel)
    return _HASHES[rel]


def version_assets(text):
    """Append `?v=<content hash>` to every CSS/JS reference.

    Asset filenames are stable on purpose (a photo can be swapped in place), so
    without this the URL does not change when the bytes do — and a browser holding
    a cached stylesheet renders the NEW markup against the OLD CSS. That is not a
    graceful degradation here: the language switch loses its pill and the hero
    mark's rings land below the wordmark instead of around it. Verified that a
    query string still resolves over `file://`, which this page is previewed on.

    Fonts are left alone deliberately — they are subset once and never re-emitted,
    which is what earns them their immutable year. If the subset is ever
    regenerated, rename the files or drop that header."""
    return re.sub(r'(?P<attr>href|src)="(?P<url>assets/(?:css|js)/[^"?]+)"',
                  lambda m: f'{m.group("attr")}="{m.group("url")}?v={_digest(m.group("url"))}"',
                  text)


def tag_sequence(html):
    """Tag names in document order. Two language variants of the same template
    must produce the same sequence; if a replacement swallowed markup (a `<span>`
    inside a button label is the classic), this is what catches it."""
    return re.findall(r"</?([a-zA-Z][\w-]*)", html)


def leftover_latvian(html):
    """Words still carrying Latvian diacritics on the English page.

    Comments are English prose about the markup, and `value="..."` attributes
    hold the deliberately-Latvian <option> values, so both are excluded. So is
    any element marked `data-verbatim`: the Google reviews are named people's
    own words and are published untranslated on purpose, in whatever language
    they were written in — see build/google_reviews.py."""
    t = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    t = re.sub(r"<(\w+)[^>]*\bdata-verbatim\b.*?</\1>", "", t, flags=re.S)
    t = re.sub(r'value="[^"]*"', 'value=""', t)
    words = re.findall(r"[\w’'-]*[" + LV_DIACRITICS + r"][\w’'-]*", t)
    return sorted({w for w in words if w not in i18n.EN_DIACRITIC_ALLOWLIST})


def emit(name, text):
    out = SITE / name
    out.write_text(text, encoding="utf-8")
    print(f"        wrote site/{name}  {out.stat().st_size // 1024} KB")
    return text


def build(template, langs, pairs, extra=None):
    """One template -> one page per language, translated, tokens filled, CSS/JS
    versioned. `extra(code)` supplies per-language values the config cannot hold
    as a constant — the rendered review list is the only one."""
    out = {}
    for code, cfg in langs.items():
        text = apply_pairs(template, pairs, code) if cfg["translate"] else template
        values = {k: v for k, v in cfg.items() if k not in ("file", "translate")}
        if extra:
            values.update(extra(code))
        out[code] = emit(cfg["file"], version_assets(substitute(text, values)))
    return out


# ------------------------------------------------------------------- the parts
print("\nINCLUDES")

forest_photo_ready = (SITE / FOREST_PHOTO).exists()
if forest_photo_ready:
    # Two layers off ONE file so the parallax survives the swap: film.js already
    # drives `.forest--near` and `.forest--far` at different rates, and it does
    # not care what is inside them. One download serves both.
    #
    # NO SRCSET, DELIBERATELY. The obvious optimisation is a small variant for
    # phones, and it is wrong here: these layers are `object-fit: cover`, so on a
    # PORTRAIT viewport the fit is driven by height, not width — a 16:9 frame
    # covering a 9:16 screen shows the middle third of its width, magnified. A
    # phone therefore needs MORE image width than a desktop, not less, and
    # `sizes="100vw"` states the exact opposite. Measured it saying so: at 500x860
    # the browser picked the 1100px file and stretched it 2.4x.
    #
    # `sizes` cannot express "height x aspect" against a container it does not
    # know, so the choice was one honest file or a lie that silently ships the
    # blurry variant to every phone. If the weight ever needs to come down, the
    # answer is an art-directed PORTRAIT frame behind <source media="(orientation:
    # portrait)">, where the selection is unambiguous — not a width-based srcset.
    def layer(cls, extra=""):
        return [f'<div class="forest {cls}" aria-hidden="true">',
                f'  <img src="{FOREST_PHOTO}" alt="" '
                f'width="2000" height="1143" decoding="async"{extra}>',
                "</div>"]

    forest = "\n".join([
        "<!-- Photographed forest. Emitted by assemble.py because",
        f"     site/{FOREST_PHOTO} exists; delete it and the drawn birch SVG comes back.",
        "     Graded at build time by build/make-forest-photo.py — film.css puts no",
        "     filter on these layers on purpose. -->",
        *layer("forest--far forest--photo", ' fetchpriority="high"'),
        *layer("forest--near forest--photo forest--photoNear"),
    ])
else:
    forest = (HERE / "forest.svg").read_text(encoding="utf-8")

PARTS = {
    "icons":    (HERE / "icons.svg").read_text(encoding="utf-8"),
    "logo":     (HERE / "logo.svg").read_text(encoding="utf-8"),
    "logohero": (HERE / "logo-hero.svg").read_text(encoding="utf-8"),
    "header":   (HERE / "header.html").read_text(encoding="utf-8"),
    "footer":   (HERE / "footer.html").read_text(encoding="utf-8"),
    "forest":   forest,
}

TEMPLATES = {
    "index":     (HERE / "index.template.html").read_text(encoding="utf-8"),
    "reviews":   (HERE / "reviews.template.html").read_text(encoding="utf-8"),
    "ty":        (HERE / "thankyou.template.html").read_text(encoding="utf-8"),
    # English only — a 404 is reached from any URL, and it carries its own
    # Latvian line rather than a second file nobody would ever land on.
    "nf":        (HERE / "404.template.html").read_text(encoding="utf-8"),
}

for name, tpl in TEMPLATES.items():
    for part, body in PARTS.items():
        tpl = tpl.replace(f"<!--@include {part}-->", body)
    left = re.findall(r"<!--@include (\w+)-->", tpl)
    if left:
        fail(f"[{name}] unsubstituted includes {left}")
    TEMPLATES[name] = tpl
if not any("unsubstituted includes" in f for f in fails):
    ok(f"{len(PARTS)} partials inlined into {len(TEMPLATES)} templates")
ok("forest layer: " + ("PHOTO — " + FOREST_PHOTO if forest_photo_ready
                       else "drawn birch SVG (no " + FOREST_PHOTO + " on disk)"))

# `<use href="#symbol">` builds a shadow <svg> at x=0, y=0 sized 100% x 100% of
# the current viewport. "100%" resolves in the outer viewBox's user units — but
# the ORIGIN does not: it is literally (0,0), not the viewBox's min-x / min-y.
# Copying the symbol's own viewBox onto the outer <svg> therefore draws the
# artwork at (0,0) while the window looks somewhere else entirely. #lg-word's
# min-y is 13.18, so the wordmark-only header lockup rendered a correctly-sized,
# correctly-coloured, completely EMPTY box on every screen under 420px — layout
# and computed style both looked perfect. Caught by a screenshot, not a probe.
#
# The outer viewBox must be "0 0 <width> <height>" of the symbol it uses.
print("\nLOGO")
symbol_boxes = dict(re.findall(r'id="(lg-[a-z]+)" viewBox="([^"]+)"', PARTS["logo"]))
want_outer = {sid: "0 0 %s %s" % tuple(vb.split()[2:]) for sid, vb in symbol_boxes.items()}
used = set()
for name, tpl in TEMPLATES.items():
    for vb, sid in re.findall(r'viewBox="([^"]+)"[^>]*>\s*<use href="#(lg-[a-z]+)"', tpl):
        used.add(sid)
        if sid not in symbol_boxes:
            fail(f"[{name}] <use> points at #{sid}, which logo.svg does not define")
        elif want_outer[sid] != vb:
            fail(f"[{name}] outer viewBox for #{sid} is \"{vb}\", must be "
                 f"\"{want_outer[sid]}\" (symbol box is \"{symbol_boxes[sid]}\"; the outer one "
                 "takes its SIZE and origin 0 0, or the artwork lands outside the window)")
if not any("outer viewBox for #" in f or "does not define" in f for f in fails):
    ok(f"{len(used)} <use> viewBox(es) correct for logo.svg ({', '.join(sorted(used))})")

# ------------------------------------------------------------------- the pages
print("\nPAGES")
pages = build(TEMPLATES["index"], i18n.LANGS, i18n.PAIRS)
rv_pages = build(TEMPLATES["reviews"], i18n.REVIEW_LANGS, i18n.REVIEW_PAIRS,
                 extra=lambda code: {
                     # The Google wall and its score block. Rendered per language
                     # but with the review TEXT verbatim in both — see
                     # build/google_reviews.py. This is the only source of
                     # reviews on the site now.
                     "GOOGLE_REVIEWS": google_reviews.render(code),
                     "GOOGLE_SCORE":   google_reviews.summary(code),
                     "GOOGLE_CTA":     google_reviews.cta(code),
                 })
ty_pages = build(TEMPLATES["ty"], i18n.TY_LANGS, i18n.TY_PAIRS)
nf_page = emit("404.html", version_assets(TEMPLATES["nf"]))

ALL = {i18n.LANGS[c]["file"]: p for c, p in pages.items()}
ALL |= {i18n.REVIEW_LANGS[c]["file"]: p for c, p in rv_pages.items()}
ALL |= {i18n.TY_LANGS[c]["file"]: p for c, p in ty_pages.items()}
ALL["404.html"] = nf_page

gplace, grows = google_reviews.published(*google_reviews._config())
gdata = google_reviews.load()
if grows:
    ok(f"{len(grows)} Google review(s) rendered ({google_reviews.LEAD} open, "
       f"{max(0, len(grows) - google_reviews.LEAD)} behind the 'show more' details); "
       f"score block reads {gplace.get('rating')} from {gplace.get('count')}")
    # The stat has to be the LIVE one or the page argues with Google. A fetch
    # that quietly failed leaves a plausible-looking older number, which is
    # exactly the kind of thing nobody notices for a year.
    stale = gdata.get("fetched")
    ok(f"google-reviews.json last fetched {stale} (source: {gdata.get('source')})"
       if stale else "google-reviews.json carries no fetch timestamp")
    if not gplace.get("write_review_url"):
        fail("google-reviews.json has no write_review_url — the hero's main CTA would be empty")
else:
    ok("no Google reviews on file — that section and the score block are not emitted")

# ------------------------------------------------------------------ assertions
print("\nTRANSLATION")
EN_PAGES = [(i18n.LANGS["en"]["file"], pages["en"]),
            (i18n.REVIEW_LANGS["en"]["file"], rv_pages["en"]),
            (i18n.TY_LANGS["en"]["file"], ty_pages["en"])]
LV_PAGES = [(i18n.LANGS["lv"]["file"], pages["lv"]),
            (i18n.REVIEW_LANGS["lv"]["file"], rv_pages["lv"]),
            (i18n.TY_LANGS["lv"]["file"], ty_pages["lv"])]

for label, html in EN_PAGES:
    stray = leftover_latvian(html)
    if stray:
        fail(f"{label} still contains Latvian: {stray}")
    else:
        ok(f"{label} carries no untranslated Latvian")

for label, html in LV_PAGES:
    if not re.search(r"[" + LV_DIACRITICS + r"]", html):
        fail(f"{label} has no Latvian diacritics at all — wrong variant written?")
    else:
        ok(f"{label} is the Latvian variant")

for label, html in EN_PAGES + LV_PAGES:
    if COMBINING.search(html):
        fail(f"{label} uses combining diacritics — Latvian must be precomposed")
if not any("combining" in f for f in fails):
    ok(f"all {len(ALL)} pages use precomposed Latvian letters")

print("\nSTRUCTURE")
for (la, a), (lb, b) in zip(EN_PAGES, LV_PAGES):
    sa, sb = tag_sequence(a), tag_sequence(b)
    if sa != sb:
        where = next((i for i, (x, y) in enumerate(zip(sa, sb)) if x != y), min(len(sa), len(sb)))
        fail(f"{la} and {lb} differ in markup at tag #{where}: "
             f"{sa[where:where+4]} vs {sb[where:where+4]} (a replacement ate markup)")
    else:
        ok(f"{la} and {lb} have an identical tag sequence ({len(sa)} tags)")

# Every page declares its language; the page WITH A FORM redirects to a thank-you
# page that exists and tags its leads with the language they came from. Only the
# front page has one now — the review page's own form was dropped in favour of
# sending people to Google — and it carries two copies of `pieteikums` (the
# visible form plus the static detection twin).
FORM_PAGES = [(i18n.LANGS, pages, 2)]
for langs, built, copies in FORM_PAGES:
    for code, cfg in langs.items():
        html = built[code]
        if f'<html lang="{cfg["LANG"]}"' not in html:
            fail(f'{cfg["file"]} does not declare lang="{cfg["LANG"]}"')
        if f'action="{cfg["TY_PAGE"]}"' not in html:
            fail(f'{cfg["file"]} form does not post to {cfg["TY_PAGE"]}')
        got = html.count(f'value="{cfg["LANGCODE"]}"')
        if got != copies:
            fail(f'{cfg["file"]} carries the hidden language field {got}x, expected {copies}')
for langs in (i18n.TY_LANGS,):
    for code, cfg in langs.items():
        if f'<html lang="{cfg["LANG"]}"' not in ALL[cfg["file"]]:
            fail(f'{cfg["file"]} does not declare lang="{cfg["LANG"]}"')
# The review pages have no form, so they are checked for their language only.
for langs, built in ((i18n.REVIEW_LANGS, rv_pages),):
    for code, cfg in langs.items():
        if f'<html lang="{cfg["LANG"]}"' not in built[code]:
            fail(f'{cfg["file"]} does not declare lang="{cfg["LANG"]}"')
        if "<form" in built[code]:
            fail(f'{cfg["file"]} carries a <form> — the review form was removed; '
                 "a stray one would register an unhandled Netlify form")
if not any("lang=" in f or "form does not post" in f or "language field" in f
           or "carries a <form>" in f for f in fails):
    ok("every page declares its language; the lead form redirects and tags its leads; "
       "the review pages carry no form")

print("\nASSETS")
refs = set()
for html in ALL.values():
    # Comments fetch nothing, and the team section documents its drop-in photo
    # slot with a literal src="assets/img/team-<name>.webp" example.
    body = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    refs |= set(re.findall(r'(?:src|href)="(assets/[^"]+)"', body))
    for ss in re.findall(r'srcset="([^"]+)"', body):
        refs |= {p.strip().split()[0] for p in ss.split(",")}
# strip the cache-busting query before touching disk, or every ref looks missing
missing = sorted(r for r in refs if not (SITE / r.split("?")[0]).exists())
if missing:
    fail("referenced but missing on disk:\n          " + "\n          ".join(missing))
else:
    ok(f"all {len(refs)} asset references exist on disk")

# losing the version query fails completely silently, so assert it is there
unversioned = sorted(r for r in refs
                     if re.match(r"assets/(css|js)/", r) and "?v=" not in r)
if unversioned:
    fail("CSS/JS reference(s) with no ?v= cache-buster: " + ", ".join(unversioned))
else:
    n = len([r for r in refs if "?v=" in r])
    ok(f"all {n} CSS/JS references carry a content hash")

print()
if fails:
    print(f"ASSEMBLE FAILED — {len(fails)} problem(s)")
    sys.exit(1)
print(f"ASSEMBLED — {len(ALL)} pages, 0 problems")
