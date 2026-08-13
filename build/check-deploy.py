# -*- coding: utf-8 -*-
"""Deployment readiness check for the AUGUSTS site.

Asserts the things that fail silently *after* a deploy: a form Netlify never
registered, a redirect target that doesn't exist, an asset referenced but not
shipped, a stale domain in the sitemap, a language variant that doesn't link
back. Run before every deploy.

    python build/check-deploy.py
"""
import hashlib, json, pathlib, re, sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DOMAIN = "augusts08.lv"
BOOKING = "calendly.com/kristine-augusts/30min"

# index.html is English (the main page); lv.html is the Latvian variant.
PAGES = {"index.html": "thank-you.html", "lv.html": "paldies.html"}
# The review page in each language. It carries NO form — the on-page review
# collector was dropped in favour of sending people to Google — so unlike PAGES
# these have no thank-you target and nothing for Netlify Forms to register.
REVIEW_PAGES = ["reviews.html", "atsauksmes.html"]
# Every page that ships.
ALL_PAGES = (list(PAGES) + REVIEW_PAGES
             + ["thank-you.html", "paldies.html", "404.html"])

fails, warns = [], []


def ok(msg):
    print(f"  PASS  {msg}")


def fail(msg):
    fails.append(msg); print(f"  FAIL  {msg}")


def warn(msg):
    warns.append(msg); print(f"  WARN  {msg}")


def read(name):
    return (SITE / name).read_text(encoding="utf-8")


def strip_comments(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


html = {name: read(name) for name in ALL_PAGES}

# ---------------------------------------------------------------- NETLIFY FORMS
print("\nNETLIFY FORMS")


def fields(form):
    return sorted(set(re.findall(r'<(?:input|textarea|select)[^>]*\bname="([^"]+)"', form)))


def audit_forms(page, ty, form_name, copies):
    """One Netlify form on one page. `copies` is how many <form> elements with
    this name the page is supposed to carry — `pieteikums` is 2: the visible form
    plus the static detection twin the callback form has shipped with since it was
    built.

    EVERY copy must declare the same fields, or Netlify registers a schema that
    does not describe what actually gets posted.

    There is only one form on the site now. The review page used to carry an
    `atsauksme` form with three photo slots; it was removed rather than kept as a
    manual moderation queue, and the checks below assert it has not crept back."""
    doc = html[page]
    forms = re.findall(r"<form\b[^>]*>.*?</form>", doc, re.S)
    named = [f for f in forms if re.search(r'name="%s"' % form_name, f)]
    if len(named) != copies:
        fail(f"[{page}] expected {copies} form(s) named '{form_name}', found {len(named)}")
        return None
    ok(f"[{page}] form '{form_name}': {len(named)} copy/copies, as expected")

    posting = [f for f in named if re.search(r'method="POST"', f, re.I)]
    if len(posting) != 1:
        fail(f"[{page}] expected exactly 1 form named '{form_name}' with method=POST, "
             f"found {len(posting)}")

    for f in named:
        tag = re.match(r"<form\b[^>]*>", f, re.S).group(0)
        kind = 'visible' if 'method="POST"' in tag else 'detection'
        label = f"{page}/{form_name}/{kind}"

        if 'data-netlify="true"' not in tag:
            fail(f"[{label}] missing data-netlify=\"true\"")

        # Netlify needs this hidden input or the POST is rejected with a 404
        m = re.search(r'<input[^>]+name="form-name"[^>]*>', f)
        if not m or f'value="{form_name}"' not in m.group(0):
            fail(f"[{label}] missing <input type=hidden name=form-name value={form_name}>")

        hp = re.search(r'netlify-honeypot="([^"]+)"', tag)
        if not hp:
            warn(f"[{label}] no netlify-honeypot declared")
        elif f'name="{hp.group(1)}"' not in f:
            fail(f"[{label}] honeypot '{hp.group(1)}' declared but no such field exists")

    schema = fields(named[0])
    for other in named[1:]:
        if fields(other) != schema:
            fail(f"[{page}] '{form_name}' copies declare different fields:"
                 f"\n          {schema}\n          {fields(other)}")
            break
    else:
        ok(f"[{page}] '{form_name}' declares: {', '.join(schema)}")

    vis = posting[0] if posting else ""

    # A file field only arrives at all if the form says so — a multipart POST
    # sent as urlencoded silently drops every attachment.
    if vis and re.search(r'type="file"', vis):
        if 'enctype="multipart/form-data"' not in re.match(r"<form\b[^>]*>", vis, re.S).group(0):
            fail(f"[{page}] '{form_name}' has file inputs but no enctype=multipart/form-data")
        else:
            ok(f"[{page}] '{form_name}' has file inputs and declares multipart/form-data")
        # Netlify keeps exactly ONE file per field, so `multiple` loses every
        # photo but the first — and does it without an error anywhere.
        if re.findall(r'<input[^>]*type="file"[^>]*\bmultiple\b[^>]*>', vis):
            fail(f"[{page}] '{form_name}' uses <input type=file multiple>, which Netlify "
                 "truncates to one file — use discrete fields instead")

    unnamed = [c for c in re.findall(r"<(?:input|textarea|select)\b[^>]*>", vis) if 'name="' not in c]
    if unnamed:
        fail(f"[{page}] {len(unnamed)} control(s) in the visible '{form_name}' form have no name")

    act = re.search(r'<form\b[^>]*action="([^"]+)"', vis)
    if not act:
        warn(f"[{page}] visible form has no action — Netlify shows its generic success page")
    elif act.group(1) != ty:
        fail(f"[{page}] '{form_name}' redirects to '{act.group(1)}', expected '{ty}'")
    elif not (SITE / ty).exists():
        fail(f"[{page}] redirect target '{ty}' does not exist in site/")
    else:
        ok(f"[{page}] '{form_name}' redirects to '{ty}', which exists")
    return schema


schemas = {}
for page, ty in PAGES.items():
    s = audit_forms(page, ty, "pieteikums", 2)
    if s:
        schemas[page] = s
# Both language pages post to the SAME Netlify form name, so one schema is
# registered for both. If the field sets drift, one language's submissions arrive
# against a schema that doesn't describe them.
if len(schemas) == 2 and len(set(map(tuple, schemas.values()))) != 1:
    fail(f"the two language pages declare different fields for form 'pieteikums': {schemas}")
elif len(schemas) == 2:
    ok("both language pages declare the same field set for form 'pieteikums'")

untagged = [p for p, code in (("index.html", "EN"), ("lv.html", "LV"))
            if f'value="{code}"' not in html[p]]
if untagged:
    fail("hidden language field missing on: " + ", ".join(untagged))
else:
    ok("both form pages tag their submissions with the language they came from")

# The review pages must carry no form at all. A leftover one would be registered
# by Netlify as a form with no handler and no thank-you page, and would look fine.
stray_forms = [p for p in REVIEW_PAGES if "<form" in strip_comments(html[p])]
if stray_forms:
    fail("review page(s) still contain a <form>: " + ", ".join(stray_forms))
else:
    ok("neither review page carries a form — reviews go to Google")

# ...and nothing anywhere should still point at the deleted review flow.
for page, doc in html.items():
    dead = sorted(set(re.findall(
        r'(?:thank-you-review|paldies-atsauksme)\.html|assets/js/reviews\.js'
        r'|name="atsauksme"|name="bilde\d"', strip_comments(doc))))
    if dead:
        fail(f"[{page}] references the removed review form: {dead}")
if not any("removed review form" in f for f in fails):
    ok("no page references the removed review form, its script or its thank-you pages")

# -------------------------------------------------------------------- BOOKING
print("\nBOOKING")
for page in PAGES:
    doc = strip_comments(html[page])
    stale = re.findall(r"leadconnectorhq\.com|msgsndr\.com|fortic\.io", doc)
    if stale:
        fail(f"[{page}] old GoHighLevel booking references still present: {sorted(set(stale))}")
    else:
        ok(f"[{page}] no leftover GoHighLevel / fortic.io references")

    links = re.findall(r'href="(https://calendly\.com/[^"]+)"', doc)
    frames = re.findall(r'<iframe[^>]+src="(https://calendly\.com/[^"]+)"', doc)
    wrong = [u for u in links + frames if BOOKING not in u]
    if wrong:
        fail(f"[{page}] booking URL(s) not pointing at {BOOKING}: {wrong}")
    elif not links or not frames:
        fail(f"[{page}] expected both booking links ({len(links)}) and an embedded calendar ({len(frames)})")
    else:
        ok(f"[{page}] {len(links)} booking links + {len(frames)} embedded calendar, all on {BOOKING}")

    # every service row must be bookable — that was the point of the change
    rows = len(re.findall(r'class="item"', doc))
    booked = len(re.findall(r'class="item__book"', doc))
    if rows != booked:
        fail(f"[{page}] {rows} service rows but {booked} booking links")
    else:
        ok(f"[{page}] all {rows} service rows carry a booking link")

# ------------------------------------------------------------------- LANGUAGES
print("\nLANGUAGES")
for page, lang, other in (("index.html", "en", "lv.html"), ("lv.html", "lv", "index.html"),
                          ("reviews.html", "en", "atsauksmes.html"),
                          ("atsauksmes.html", "lv", "reviews.html")):
    doc = html[page]
    if f'<html lang="{lang}"' not in doc:
        fail(f"[{page}] does not declare lang=\"{lang}\"")
    elif f'href="{other}"' not in doc:
        fail(f"[{page}] does not link to its other language variant ({other})")
    elif doc.count('aria-current="page"') != 1:
        fail(f"[{page}] language switch must mark exactly one active variant")
    else:
        ok(f"[{page}] lang=\"{lang}\", links to {other}, one active switch item")

    for tag in ('hreflang="en"', 'hreflang="lv"', 'hreflang="x-default"'):
        if f'<link rel="alternate" {tag}' not in doc:
            fail(f"[{page}] missing <link rel=alternate {tag}>")

canon = {p: re.search(r'<link rel="canonical" href="([^"]+)"', html[p]).group(1)
         for p in list(PAGES) + REVIEW_PAGES}
if len(set(canon.values())) != len(canon):
    fail(f"two pages share a canonical URL: {canon}")
else:
    ok(f"{len(canon)} distinct canonicals: " + ", ".join(sorted(canon.values())))

# A page that links to the OTHER language's review page drops an English reader
# into Latvian. The language switch and the hreflang alternates are the only two
# places a cross-language href belongs.
for page, wrong in (("index.html", "atsauksmes.html"), ("reviews.html", "atsauksmes.html"),
                    ("lv.html", "reviews.html"), ("atsauksmes.html", "reviews.html")):
    doc = strip_comments(html[page])
    crossed = len(re.findall(r'href="%s"' % wrong, doc))
    allowed = (len(re.findall(r'<a href="%s" hreflang=' % wrong, doc))
               + len(re.findall(r'rel="alternate" hreflang="[a-z-]+" href="[^"]*/%s"' % wrong, doc)))
    if crossed > allowed:
        fail(f"[{page}] links to {wrong} outside the language switch "
             f"({crossed} refs, {allowed} allowed)")
if not any("outside the language switch" in f for f in fails):
    ok("every page's review link stays in its own language")

# --------------------------------------------------------------- GOOGLE REVIEWS
print("\nGOOGLE REVIEWS")
gr_path = ROOT / "build" / "google-reviews.json"
if not gr_path.exists():
    warn("build/google-reviews.json is missing — the Google wall and the score block "
         "are simply absent from the page")
else:
    gr = json.loads(gr_path.read_text(encoding="utf-8"))
    place = gr.get("place", {})
    pid = place.get("place_id")

    # The whole point of the score block is that it agrees with Google. A number
    # typed into the markup by hand, or left behind by an older fetch, still
    # renders perfectly — so compare the markup against the file it came from.
    for page in REVIEW_PAGES:
        doc = strip_comments(html[page])

        shown = re.search(r'class="gscore__num num" aria-hidden="true">([\d,.]+)<', doc)
        want = str(place.get("rating") or "")
        got = (shown.group(1).replace(",", ".") if shown else None)
        if not shown:
            fail(f"[{page}] no Google score block — the hero lost its rating")
        elif got != want:
            fail(f"[{page}] score block shows {got}, google-reviews.json says {want}")
        else:
            ok(f"[{page}] score block shows {want}, matching google-reviews.json")

        cnt = re.search(r'class="gscore__count num" aria-hidden="true">(\d+)', doc)
        if not cnt or int(cnt.group(1)) != (place.get("count") or -1):
            fail(f"[{page}] review count in the score block does not match "
                 f"google-reviews.json ({place.get('count')})")

        # The primary CTA. A write-review URL carrying the wrong place id sends
        # the visitor to review somebody else's business, and looks fine.
        wr = re.findall(r'href="(https://search\.google\.com/local/writereview\?placeid=[^"]+)"', doc)
        if not wr:
            fail(f"[{page}] no 'write a review on Google' button")
        elif not all(u.endswith(pid) for u in wr):
            fail(f"[{page}] write-review URL(s) do not carry place_id {pid}: {wr}")
        else:
            ok(f"[{page}] {len(wr)} write-review link(s), all on place_id {pid}")

        if not re.search(r'href="https://search\.google\.com/local/reviews\?placeid=%s"' % pid, doc):
            fail(f"[{page}] no link out to the full Google review list")

        # Every card must name its language, or a Latvian review on the English
        # page is read out with English phonemes and Chrome will not offer to
        # translate it.
        bodies = re.findall(r'<div class="rvcard__body"([^>]*)>', doc)
        unlabelled = [b for b in bodies if "lang=" not in b]
        if unlabelled:
            warn(f"[{page}] {len(unlabelled)} of {len(bodies)} review card(s) carry no lang= "
                 "(Google reported no language for them)")

    # Both language pages must show the SAME reviews: the text is deliberately
    # not translated, so a difference means the render diverged, not that a
    # string was localised.
    counts = {p: len(re.findall(r'class="rvcard"', strip_comments(html[p]))) for p in REVIEW_PAGES}
    if len(set(counts.values())) != 1:
        fail(f"the two review pages render a different number of cards: {counts}")
    else:
        ok(f"both review pages render {list(counts.values())[0]} review card(s)")

    # Reviews of yourself, on your own site, marked up for rich results is
    # against Google's own structured-data guidelines ("self-serving reviews")
    # and earns a manual action rather than stars. Easy to add by accident later.
    for page, doc in html.items():
        for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            if re.search(r'"(aggregateRating|reviewRating)"|"@type"\s*:\s*"Review"', ld):
                fail(f"[{page}] structured data marks up reviews of this business — Google "
                     "forbids self-serving review markup")
    if not any("self-serving" in f for f in fails):
        ok("no self-serving review/aggregateRating structured data on any page")

    fetched = gr.get("fetched", "")
    if fetched:
        try:
            age = (datetime.now(timezone.utc)
                   - datetime.strptime(fetched, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).days
            (ok if age <= 45 else warn)(
                f"google-reviews.json fetched {age} day(s) ago ({fetched})"
                + ("" if age <= 45 else " — run build/fetch-google-reviews.py"))
        except ValueError:
            warn(f"google-reviews.json has an unparseable 'fetched' value: {fetched!r}")
    else:
        warn("google-reviews.json has no 'fetched' timestamp")

# ---------------------------------------------------------------------- ASSETS
print("\nASSETS")
allhtml = {p: read(p) for p in ALL_PAGES}
refs = set()
for doc in allhtml.values():
    body = strip_comments(doc)
    refs |= set(re.findall(r'(?:src|href)="(assets/[^"]+)"', body))
    for ss in re.findall(r'srcset="([^"]+)"', body):
        refs |= {p.strip().split()[0] for p in ss.split(",")}
# strip the ?v= cache-buster before touching disk, or every ref looks missing
missing = sorted(r for r in refs if not (SITE / r.split("?")[0]).exists())
if missing:
    fail("referenced but missing: " + ", ".join(missing))
else:
    ok(f"all {len(refs)} asset references exist on disk")

# The CSS/JS URLs must change when their bytes change — filenames here are stable,
# so the query string is the only thing carrying that. Verify the hash in the
# markup is actually the hash of the file on disk, not a stale one baked in by an
# older build: a wrong-but-present ?v= looks fine and caches forever.
for page, doc in html.items():
    for url, ver in re.findall(r'(?:href|src)="(assets/(?:css|js)/[^"?]+)\?v=([0-9a-f]+)"', doc):
        want = hashlib.sha1((SITE / url).read_bytes()).hexdigest()[:8]
        if ver != want:
            fail(f"[{page}] {url} is versioned ?v={ver} but its bytes hash to {want} "
                 "— rerun build/assemble.py")
        n_ver = 1
if not any("bytes hash to" in f for f in fails):
    ok("every CSS/JS ?v= matches the current bytes on disk")

# Fonts and the grain tile are referenced from the stylesheets, not the markup,
# so the orphan sweep has to read the CSS too — `url('../fonts/courier.woff2')`
# is a real reference even though no page mentions it.
css_refs = set()
for css in (SITE / "assets" / "css").glob("*.css"):
    sheet = css.read_text(encoding="utf-8")
    for url in re.findall(r"url\(['\"]?([^'\")]+)['\"]?\)", sheet):
        css_refs.add((css.parent / url).resolve().relative_to(SITE.resolve()).as_posix())

#     …and the markup refs carry a ?v= cache-buster, so compare bare paths
known = {r.split("?")[0] for r in refs} | css_refs
orphans = sorted(p.relative_to(SITE).as_posix() for p in (SITE / "assets").rglob("*")
                 if p.is_file() and p.relative_to(SITE).as_posix() not in known)
if orphans:
    warn(f"{len(orphans)} shipped asset(s) nothing references: {', '.join(orphans)}")
else:
    ok(f"every shipped asset is referenced ({len(refs)} from markup, {len(css_refs)} from CSS)")

# Dead CSS is weight every visitor downloads, and removing a feature is exactly
# when it accumulates: dropping the review form orphaned 20 rules — the star-rating
# radios, three photo slots, the form's own surface — while LEAVING the star glyph
# rules the Google cards still need. Guessing which is which is how you either
# ship 5 KB of nothing or break the cards. So: measure.
#
# Classes added at runtime are collected from the scripts too, or every `is-in` /
# `is-open` toggle would look unused.
css_classes, used_classes = {}, set()
for doc in allhtml.values():
    for attr in re.findall(r'class="([^"]*)"', doc):
        used_classes.update(attr.split())
for js in sorted((SITE / "assets" / "js").glob("*.js")):
    src = js.read_text(encoding="utf-8")
    for grp in re.findall(r"""(?:classList\.(?:add|remove|toggle|contains)|className\s*=)"""
                          r"""\s*\(?\s*['"]([\w\s-]+)['"]""", src):
        used_classes.update(grp.split())
    for sel in re.findall(r"""querySelector(?:All)?\(\s*['"]([^'"]+)['"]""", src):
        used_classes.update(re.findall(r"\.([\w-]+)", sel))

# `.png` / `.woff2` etc. are file extensions inside url(), not class selectors.
NOT_CLASSES = {"png", "woff2", "js", "svg", "webp", "ico", "jpg"}
for css in sorted((SITE / "assets" / "css").glob("*.css")):
    body = re.sub(r"/\*.*?\*/", "", css.read_text(encoding="utf-8"), flags=re.S)
    declared = set(re.findall(r"\.([A-Za-z][\w-]*)", body))
    orphans = sorted(c for c in declared
                     if c not in used_classes and c not in NOT_CLASSES)
    if orphans:
        warn(f"assets/css/{css.name}: {len(orphans)} class(es) no page uses — "
             + ", ".join("." + c for c in orphans))
    else:
        ok(f"assets/css/{css.name}: all {len(declared)} class selectors are used")

for icon in ["favicon.ico", "icon-32.png", "icon-180.png"]:
    if not (SITE / icon).exists():
        fail(f"{icon} missing")
if not any("icon" in f or "favicon" in f for f in fails):
    ok("favicon + apple-touch-icon present")

# --------------------------------------------------------------- ROUTING / SEO
print("\nROUTING & SEO")
for page in ALL_PAGES + ["robots.txt", "sitemap.xml"]:
    if (SITE / page).exists():
        ok(f"{page} present")
    else:
        (fail if page != "404.html" else warn)(f"{page} missing")

rb = read("robots.txt")
before = len(warns)
if DOMAIN not in rb:
    warn(f"robots.txt sitemap URL does not mention {DOMAIN}")
for ty in ["thank-you.html", "paldies.html"]:
    if f"Disallow: /{ty}" not in rb:
        warn(f"robots.txt does not disallow /{ty}")
    if "noindex" not in read(ty):
        warn(f"{ty} is not noindex")
if len(warns) == before:
    ok("robots.txt points at the sitemap, disallows both thank-you pages, both are noindex")

sm = read("sitemap.xml")
for loc in ["https://augusts08.lv/", "https://augusts08.lv/lv.html",
            "https://augusts08.lv/reviews.html", "https://augusts08.lv/atsauksmes.html"]:
    if f"<loc>{loc}</loc>" not in sm:
        fail(f"sitemap.xml does not list {loc}")
if not any("sitemap" in f for f in fails):
    ok("sitemap.xml lists all four indexable pages with hreflang alternates")

# The old address still works, which is the problem: a stale one left on a page
# looks live and quietly delivers to an inbox nobody is watching any more.
print()
EMAIL = "mieraaugusts@gmail.com"
stale_mail = sorted(p for p, doc in allhtml.items()
                    if set(re.findall(r"[\w.+-]+@[\w.-]+\.\w+", strip_comments(doc)))
                    - {EMAIL} - {"augusts08.lv"})
if stale_mail:
    fail(f"an email address other than {EMAIL} appears on: " + ", ".join(stale_mail))
else:
    ok(f"every email address on the site is {EMAIL}")

# ------------------------------------------------------------------- HYGIENE
print("\nHYGIENE")
stray = [p for p in SITE.rglob("*")
         if p.is_file() and (p.suffix in {".py", ".log", ".orig", ".bak"}
                             or p.name in {".DS_Store", "Thumbs.db", "_control.html"})]
if stray:
    fail("stray files in the deploy dir: " + ", ".join(p.name for p in stray))
else:
    ok("no build artefacts in the deploy dir")

for page, doc in allhtml.items():
    leak = re.findall(r"127\.0\.0\.1|localhost:\d+|file:///", doc)
    if leak:
        fail(f"[{page}] local-only URL leaked into the markup: {set(leak)}")
    abs_refs = re.findall(r'(?:src|href)="/(?!/)[^"]*"', doc)
    if abs_refs:
        warn(f"[{page}] {len(abs_refs)} root-absolute path(s) — these break the file:// preview")
if not any("leaked" in f for f in fails):
    ok("no localhost/file:// URLs and no root-absolute paths in any page")

toml = (ROOT / "netlify.toml").read_text(encoding="utf-8")
if 'publish = "site"' not in toml:
    fail("netlify.toml does not publish site/")
else:
    ok("netlify.toml publishes site/")

# The weekly Google-review refresh is a GitHub Action at the REPO ROOT, which is
# above this project — it commits the fetched archive so nothing can scroll out of
# the Places API's 5-review window and vanish. Every part of it fails silently:
# a missing cron just stops updating, a missing secret name just commits nothing,
# and the page keeps rendering an archive that slowly goes stale.
wf = None
for up in (ROOT, ROOT.parent, ROOT.parent.parent):
    cand = up / ".github" / "workflows" / "augusts-google-reviews.yml"
    if cand.exists():
        wf = cand
        break

if wf is None:
    warn("no .github/workflows/augusts-google-reviews.yml found — the Google wall will "
         "only update on a manual deploy. See README 'Two ways to run it'.")
else:
    body = wf.read_text(encoding="utf-8")
    rel = wf.as_posix().split("/.github/")[-1]
    problems = []
    if not re.search(r"schedule:\s*\n\s*(#.*\n\s*)*- cron:", body):
        problems.append("no cron schedule")
    if "workflow_dispatch" not in body:
        problems.append("no workflow_dispatch (cannot be run by hand)")
    if "contents: write" not in body:
        problems.append("no `contents: write` permission — the commit step cannot push")
    if "GOOGLE_MAPS_API_KEY" not in body:
        problems.append("never passes GOOGLE_MAPS_API_KEY, so the fetch can only no-op")
    for script in ("fetch-google-reviews.py", "assemble.py", "check-deploy.py"):
        if script not in body:
            problems.append(f"does not run {script}")
    if "git commit" not in body:
        problems.append("does not commit — the archive would not persist, which is the "
                        "whole reason this runs in Actions and not on a build hook")
    # The workflow cds into the project; if that path is wrong every step fails on
    # the first run and not before.
    m = re.search(r"PROJECT:\s*(\S+)", body)
    if not m:
        problems.append("declares no PROJECT working directory")
    else:
        target = (wf.parent.parent.parent / m.group(1)).resolve()
        if target != ROOT.resolve():
            problems.append(f"PROJECT is '{m.group(1)}', which resolves to {target}, "
                            f"not this project ({ROOT.resolve()})")
    if problems:
        for pr in problems:
            fail(f"[.github/{rel}] {pr}")
    else:
        cron = re.search(r"- cron:\s*\"([^\"]+)\"", body).group(1)
        ok(f"weekly refresh wired: .github/{rel} cron '{cron}' -> fetch + assemble + "
           "gate -> commit -> Netlify continuous deployment")

# Belt and braces: the two mechanisms must not both be live, or they do the same
# work twice and race on the same commit. Comments are stripped first — netlify.toml
# names the deleted function in prose explaining why it is gone, and matching that
# is how this check failed the first time it ran.
toml_live = "\n".join(l for l in toml.splitlines() if not l.lstrip().startswith("#"))
if wf is not None and 'functions."refresh-reviews"' in toml_live:
    fail("netlify.toml still schedules the refresh-reviews function AND a GitHub Action "
         "exists — pick one (the Action is the one that persists the archive)")

# Netlify's Python is whatever the image ships unless pinned, and assemble.py
# needs 3.9+ for dict `|=`.
if "command =" in toml and "PYTHON_VERSION" not in toml:
    warn("netlify.toml runs a Python build command but does not pin PYTHON_VERSION")

# Asset filenames here are stable, so freshness has to come from the header — and
# `must-revalidate` does NOT mean "check every time", it only forbids serving a
# response after it goes stale. A long max-age on the CSS therefore ships new
# markup against an old stylesheet to every returning visitor, and this page fails
# hard that way: the language switch loses its pill, the hero mark's rings land
# below the wordmark instead of around it. Reproduced, not theorised.
print()
for kind in ("css", "js"):
    block = re.search(r'for = "/assets/%s/\*".*?Cache-Control = "([^"]+)"' % kind, toml, re.S)
    if not block:
        warn(f"netlify.toml sets no Cache-Control for /assets/{kind}/")
        continue
    cc = block.group(1)
    age = re.search(r"max-age=(\d+)", cc)
    if "no-store" in cc or "no-cache" in cc or (age and int(age.group(1)) == 0):
        ok(f"/assets/{kind}/ revalidates every request ({cc})")
    else:
        fail(f"/assets/{kind}/ is cached for {age.group(1) if age else '?'}s ({cc}) — "
             "a stylesheet/script change will ship against stale markup. Use max-age=0.")

# ------------------------------------------------------------------- VERDICT
print()
if fails:
    print(f"NOT DEPLOY READY — {len(fails)} failure(s), {len(warns)} warning(s)")
    sys.exit(1)
print(f"DEPLOY READY — 0 failures, {len(warns)} warning(s)")
