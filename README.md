# AUGUSTS /08/ — frizierdarbnīca, Miera iela 19, Rīga

A bilingual site — **English is the main language**, Latvian is the second
variant — built from the client's own assets in a "dirty hippy" style: a front
page (scroll-film, six service cards, the full price list, gallery, team, the
salon's **own Calendly** embedded, contact) and a **reviews page** that mirrors
their Google reviews and refreshes itself weekly.

Deploy: `site/` (Netlify `publish = "site"`). Preview: open `site/index.html`
straight off disk — all asset paths are page-relative and the script is not an
ES module, so `file://` works.

**The Google wall refreshes itself weekly** via a GitHub Action that commits the
new reviews; Netlify's continuous deployment does the rest. `site/` stays fully
built in the repo, and the deploy gate runs before the commit, so a bad render
keeps the last good deploy live rather than shipping a broken page. See "Google
reviews".

```
augusts/                    ← this folder IS the git repo root
├── .gitignore              excludes _qa/ (204 screenshots, 82 MB, regenerable)
├── .gitattributes          text=auto — load-bearing, see "Line endings" below
├── .github/workflows/
│   └── augusts-google-reviews.yml   weekly: fetch → assemble → gate → COMMIT
├── netlify.toml            publish = site, caching + security headers
├── build/                  ← generators (not deployed)
│   ├── index.template.html the front page in Latvian, with @include + {{TOKEN}}
│   ├── reviews.template.html   the reviews page source
│   ├── thankyou.template.html   lead form target
│   ├── 404.template.html
│   ├── header.html · footer.html   partials SHARED by the two real pages
│   ├── i18n.py             LV→EN string tables + per-language token values
│   ├── google-reviews.json the salon's Google reviews (generated archive)
│   ├── fetch-google-reviews.py  refreshes that file — Places API or Apify
│   ├── google_reviews.py   renders the Google wall + the score block
│   ├── assemble.py         templates → the nine shipped pages, with asserts
│   ├── gen-logo.py         traces the client's print PDF → logo.svg
│   ├── logo.svg            the traced lockup as <symbol>s (generated)
│   ├── logo-hero.svg       the same lockup inline, per-letter (generated)
│   ├── icons.svg           14 hand-drawn engraving glyphs (inlined)
│   ├── make-forest.py      → forest.svg, the birch layers (seeded, inlined)
│   ├── gen-forest.py       KIE → the film's forest photograph (raw/)
│   ├── make-forest-photo.py    grades raw/ → site/assets/img/mezs-fons.webp
│   ├── raw/                the ungraded generated frames — back up before re-rolling
│   └── gen-icons.py        KIE engraving plates — READY, NOT YET RUN (no credits)
├── site/                   ← the deployable
│   ├── index.html          EN front page — generated
│   ├── lv.html             LV front page — generated
│   ├── reviews.html        EN reviews — generated
│   ├── atsauksmes.html     LV reviews — generated
│   ├── thank-you.html · paldies.html   lead form target (noindex)
│   ├── 404.html            EN with a plain-text link to the Latvian page
│   ├── robots.txt · sitemap.xml · favicon.ico · icon-*.png
│   └── assets/{css,js,fonts,img}
└── _qa/                    screenshots + probe output (git-ignored, not deployed)
```

**All seven HTML pages are generated.** Edit `build/index.template.html` or
`build/reviews.template.html` (and `build/i18n.py` for the English wording), then:

```
python build/assemble.py      # → the seven pages, with assertions
python build/check-deploy.py  # must print "DEPLOY READY — 0 failures"
```

The header and the footer are `build/header.html` / `build/footer.html`, included
into both real pages. Do not copy them into a template — a second hand-kept copy
is how a nav item ends up on one page and not the other. `{{HOME}}` is `""` on the
front page and the other page's filename on a sub-page, so `{{HOME}}#kontakti`
is an in-page anchor where that section exists and a cross-page link where it
does not.

---

## Two languages, one template

English is the main page (`/`), Latvian is `/lv.html`, and an `EN | LV` pill in
the header switches between them with relative hrefs (so the switch works off
disk too). Each page carries `hreflang` alternates for both plus `x-default` → EN.

**The Latvian template is the source of truth**, because the copy is the salon's
own wording; the English page is *generated* from it by the string table in
`build/i18n.py`. That means every non-text byte — the SVG blobs, the film's
`data-*` beat timings, `srcset`, class names — is identical between the two and
can only ever diverge on purpose.

Two rules keep that reliable, and both are enforced in `assemble.py`:

- **Longest source first.** Otherwise a short fragment (`Griezums`) is replaced
  inside a longer phrase containing it (`Matu griezums`), leaving half-translated
  text behind.
- **Sources are anchored with their surrounding markup** (`>Cenrādis</a>`, not
  `Cenrādis`) wherever a word appears in two roles — nav link *and* section
  heading, form label *and* `<option>` value.

`assemble.py` fails the build on:

| assertion | what it catches |
|---|---|
| every pair's source occurs in the template | a reworded template silently skipping a translation |
| **leftover-diacritic sweep on the EN pages** | any missed string — Latvian text almost always carries a macron or caron. Comments and `value="…"` are excluded; the only allowlisted words are `Kristīne`, `Rīga`, and the footer's own `Latviešu valodā` link |
| **EN and LV have an identical tag sequence** | a replacement that ate markup — e.g. a pair swallowing the `<span>` holding a button's arrow |
| no combining diacritics | `ģ` written as g + COMBINING CEDILLA, which renders but breaks search and sorting |
| every `{{TOKEN}}` substituted, every `assets/…` present | the usual silent-404 class |

Deliberately **not** translated: `<option value="…">` keeps its Latvian service
names (only the visible labels change), and `utm_content` stays an ASCII slug —
both so the salon's form inbox and Calendly records read one consistent set of
names whichever language the visitor used. A hidden `language` field (EN/LV)
tags each lead so replies go out in the right one.

What else is per-language: `<html lang>`, canonical, `og:locale`, the form's
redirect target, the active pill item, and the film's chapter names — those come
from `data-chapters` on the film section, so one `film.js` serves both pages
instead of carrying a translated string table.

---

## Booking — the salon's own Calendly

The GoHighLevel calendar groups the previous version embedded are **gone**. All
booking now goes to the salon's own Calendly, `calendly.com/kristine-augusts/30min`
(event *Griezums*, owner *Kristīne Kazoka*).

Three ways in, all to the same calendar:

- **Every service row** carries its own `Rezervēt / Book →` link — 16 of them, so
  nobody has to scroll to the calendar section first. This was the point of the
  change.
- **Each team member** has a booking link on their card.
- **The `Rezervē laiku` section** embeds the calendar inline, plus the header CTA.

Each link's `href` is the real Calendly URL, so booking still works with JS off
or if `app.js` 404s; the script only *upgrades* the link into an in-page modal.
Per-service `utm_content` slugs mean the salon can see which service a booking
came from. `data-svc` puts the service name in the modal's title bar.

### Three parameters that matter

Framed Calendly gets `embed_domain` + `embed_type=Inline` + `hide_gdpr_banner=1`;
the plain links do not. `embed_type=Inline` earns its place twice:

1. **It suppresses Calendly's cookie dialog.** Without it, a large blue consent
   panel opens straight across the calendar. `hide_gdpr_banner=1` alone does not
   do this — that flag is for a different banner.
2. It makes Calendly's page background transparent, so our paper and grain show
   through around the card.

That transparency is *why the "open in a new window" line sits below the frame
rather than behind it*: the previous version layered the fallback behind the
iframe and relied on an opaque embed to cover it. Behind a transparent iframe it
reads straight through the calendar.

`primary_color` / `background_color` / `text_color` are honoured, so the widget
renders in `--rust` on `--paper` rather than Calendly's default blue-on-white.
`embed_domain` does not have to match the host — verified from a different
origin, not assumed.

### Frame heights are measured, not guessed

No resize script is loaded, so the CSS height is the contract — nothing grows
after boot, so nothing below the calendar shifts down on load. These are the
heights Calendly's month step actually needs at each frame **width**, and note
the widest band is *not* the tallest, because Calendly stacks its event pane
above the calendar in the middle range:

| frame width | needs | CSS |
|---|---|---|
| ~1060 px (desktop, two panes) | 700 px | 730 px |
| ~700 px (tablet, stacked) | 940 px | 970 px |
| ~308 px (mobile) | 860 px | 900 px |

Deeper steps (the time list, the details form) can exceed these; Calendly scrolls
them internally, which is correct behaviour for a framed widget.

### ⚠ Two things to settle before this goes live

1. **The Calendly account currently has exactly one event type** — *Griezums*,
   **1 hour** (the `30min` slug is historical). So a 3-hour bleaching appointment
   reserves one hour. The page works around it with a line above the calendar
   asking which service you want in the notes. The client has said more event
   types are coming; the page is already built for that — each service row has its
   own link, so it is one `href` per row to point at a dedicated event type.
2. **The old GoHighLevel calendars are still live** at `fortic.io` and
   `api.leadconnectorhq.com`. Nothing on this site points at them any more, but
   if anyone still has those links, bookings can land in a calendar Calendly
   cannot see — i.e. double bookings. Close the old funnel, or point it here.

---

## The team section

Three people, three real portraits — all sourced, none invented:

- **Kristīne Kazoka** — meistare and owner. Bookable for women's, men's and
  children's services.
- **Adele Axelle** — jaunā meistare, with the 50%-off haircut. Bookable for
  women's services only. Her bio and languages ("Latvian — learning · English and
  Russian — fluent") are the salon's own words, verbatim from the service
  description live in their booking system. Worth confirming the discount stands.
- **Maija Goldberga** — meistare, **also with a 50%-off haircut** (added at the
  client's request; the `−50%` badge and the booking link's
  `data-svc="Griezums ar Maiju (−50%)"` follow Adele's pattern exactly). Languages
  are the only detail the client sent ("Latvian and English — fluent · Russian — a
  little") and are quoted as given; her bio is written to the same shape as the
  other two and should be checked with her.

  Her portrait arrived as a 3024 × 4032 HEIC over Google Drive (`pillow_heif`
  decodes it). Crop chosen off a three-candidate contact sheet against the other
  two portraits: the head has to fill the frame to the same degree or the card
  reads as a different set. The tight head-and-shoulders crop that keeps her
  raised hand won — 1200 px square out of the original, down to 512 + 256.

**The monogram placeholder is gone**, because all three now have real photos and
`check-deploy.py` warns about CSS nothing uses. If a fourth stylist joins before
their photo does, put this back inside `.team__photo` in place of the `<img>`, plus
`.team__mono { width: 78%; height: 78%; }`:

```html
<svg class="team__mono" viewBox="0 0 120 120" role="img" aria-label="Name Surname">
  <circle cx="60" cy="60" r="47" fill="none" stroke="currentColor" stroke-width=".9" opacity=".38"/>
  <text x="60" y="79" text-anchor="middle" fill="currentColor"
        font-family="Fraunces, Georgia, serif" font-size="58" letter-spacing="1">N</text>
</svg>
```

Portraits are **rounded squares** (`border-radius: 27%` on a square frame with
`overflow: hidden`) as requested. The badge lives in a `.team__pic` wrapper
*outside* that frame — as a child of the clipped element, the corner radius cut
the corner off it. Both photos carry the gallery's grade
(`saturate(.9) contrast(1.03)`); the two come from different shoots, one
forest-green and one hot pink, and matching the gallery settles them against the
paper.

### Where the portraits came from — worth knowing for next time

They are **not** anywhere on the public site, the link-in-bio page, or the service
lists. The chain is:

```
fortic.io/onlinebooking-augusts   link-in-bio, 4 buttons, no images
  → fortic.io/procedura           service-group chooser, no images
    → fortic.io/augusts-sievietem embeds the GHL group widget
      → the widget's service list 16 cards, 180×180 — all MODEL/WORK photos
        → click a service        ← "Select staff for …": name + 512×512 portrait
```

Only the **staff-selection step** attaches a face to a name, and you only reach it
by clicking a service card inside the widget. It also confirms who does what
(Adele appears only under women's services). The names there read
`Kristīne AUGUSTS` and `Adele Axelle Haircut 50 percent OFF` — brand suffix and
promo text respectively.

512×512 is the stored size, so nothing is upscaled: the frame is at most 164 px
CSS, which 512 covers past 3× DPR. Shipped as `team-{kristine,adele}.webp` plus
`-sm` at 256 for the mobile frame. The regeneration script is in the scratchpad,
not the deployable; if better portraits arrive, overwrite those four files at the
same sizes.

Adding a third stylist before their photo arrives: `.team__photo` also accepts the
monogram plate the first build shipped —

```html
<svg class="team__mono" viewBox="0 0 120 120" role="img" aria-label="Name">
  <circle cx="60" cy="60" r="47" fill="none" stroke="currentColor" stroke-width=".9" opacity=".38"/>
  <text x="60" y="79" text-anchor="middle" fill="currentColor"
        font-family="Fraunces, Georgia, serif" font-size="58" letter-spacing="1">N</text>
</svg>
```

— the frame, the crop and the radius are identical either way.

---

## The logo — the client's real artwork, traced

The mark used to be *reconstructed*: `AUGUSTS` set in Fraunces (the page's wonky
serif) with a `/08/` badge beside it, tinted gold. The salon's actual logo is a
wide **geometric sans** in **process yellow `#FFF200`**, and they sent the print
PDF for it. So the mark is now the artwork itself.

`build/gen-logo.py` reads `August Front.pdf`, pulls the 26 filled vector paths
out and writes two files:

| file | what it is | used by |
|---|---|---|
| `build/logo.svg` | 4 `<symbol>`s — `lg-full`, `lg-word`, `lg-no`, `lg-sub` | header, footer, thank-you × 2, 404 |
| `build/logo-hero.svg` | the same lockup **inline**, one `<path>` per letter | the hero only |

The hero needs its own copy because `<use>` puts the symbol's contents in a
**shadow tree**, and a stylesheet outside it cannot reach the individual letters —
which is what the opening per-letter stagger animates. Both come from one trace,
so they cannot drift. Re-run `python build/gen-logo.py` if the artwork changes;
it prints the viewBoxes, and `assemble.py` fails the build if the markup's no
longer agree.

Four things this got wrong, three of them silent:

- **PyMuPDF returns each contour as a LIST OF SEGMENTS, not a path.** Emitting one
  `M…L…` per segment draws the outline correctly but fills every counter solid —
  the holes in A, U, G, 8, R, B need to be their own closed subpaths for nonzero
  winding. `chain()` starts a new subpath whenever a segment does not begin where
  the previous one ended.
- **`fill="currentColor"` has to be on each `<path>`, not the parent `<svg>`.**
  Inside a `<use>` shadow tree the paths do not inherit it and fall back to the
  SVG default fill — black, on a near-black header.
- **A `<use>`'s shadow `<svg>` sits at origin (0,0) whatever the viewBox says.**
  The outer `<svg>`'s viewBox must be `0 0 <symbol width> <symbol height>`, NOT a
  copy of the symbol's own box. `#lg-word`'s box starts at y = 13.18, so copying it
  drew the wordmark 13 units above the window: a correctly sized, correctly
  coloured, **completely empty rectangle** in the header on every screen under
  420 px. Layout and computed style both looked perfect — only a screenshot caught
  it. `assemble.py` now asserts the relationship.
- **The lockup is one object, so it needs a legibility floor, not just a scale.**
  `FRIZIERDARBNĪCA` is 4.1% of the logo's width in height. Under ~120 px of logo
  that is five pixels of tracked caps, i.e. a smudge — so below 420 px the header
  switches to `#lg-word`, the wordmark alone.

Yellow is the **logo's** colour and nothing else's. `--brand: #FFF200` is 19.2:1
against `--ink` and **1.13:1 against `--paper`** — invisible. The mark therefore
appears in `--brand` only where the ground is dark (header, film, footer, 404,
thank-you); every other accent keeps the earthy `--gold`.

### The rings around the hero mark

Two concentric rings still enclose the lockup — the client asked for them in the
previous round and only asked for a colour change in this one. What went away with
the traced logo is all the font-derived geometry: `.mark` is now a square of
**1.30 × the logo's width**, full stop. There is no `--k` multiplier and no 900 px
breakpoint, because the artwork has a fixed aspect ratio where Fraunces did not
(variable optical size made `AUGUSTS` relatively *wider* as it shrank — 5.05× its
font size at 86 px, 5.46× at 42 px).

Three constraints still bind, and all three have bitten:

- **`svg { max-width: 100% }` in the reset clamps the rings** back to the grid's
  content width instead of the square. First thing to check if a ring looks
  squashed.
- **`vector-effect: non-scaling-stroke` resolves `stroke-dasharray` in DEVICE
  space, not user units.** The ring was originally drawn on with a dash, and a
  dasharray sized to the circle's 309-unit circumference tiled ~2.5 times around
  the 1589 px *rendered* circumference — leaving the finished ring with two gaps in
  it at `stroke-dashoffset: 0`. Any fixed dasharray is wrong at some width. The
  ring arrives on **opacity + transform** instead, which is what the film's own
  architecture note demands. `non-scaling-stroke` stays: it holds the line to an
  even hairline at every size.
- The reveal is armed **only under `.js`**, keyed off `.wordmark.is-in ~
  .mark__ring` — a sibling combinator, deliberately not `:has()`, because where
  `:has()` is unsupported the whole rule is dropped and the rings stay invisible
  forever. The size of `.mark` is capped three ways (`clamp` for the type scale,
  `74vw` so the ring fits a narrow screen, `46svh` so the square fits the film's
  stage); a width-only rule runs the ring off the bottom of a laptop.

The letters' start state is four classes deep (`html.js .wordmark:not(.is-in)
.lg__l`). **Anything overriding it needs at least that specificity** — a plain
`.film--static .lg__l` is (0,2,0) and loses silently. That is why the static and
reduced-motion overrides repeat the whole selector.

## The header CTA

`.btn--hdr`, and it is deliberately not `.btn--sm`. Worth knowing why it took a
CSS fix and not just a bigger number:

**`.nav a` is (0,1,1) and outranks `.btn` (0,1,0).** The header button had been
taking a *nav link's* `font-size` and `padding: .3rem 0` all along — a pill with
no horizontal padding, immune to `btn--sm` and to anything added after it. The
link rule is now `.nav a:not(.btn)`, which is what makes the button component
apply inside the header at all. Same class of bug as `.beat h1` (0,1,1) silently
beating `.wordmark` (0,1,0) in the film, where the wordmark's own `9.5rem` clamp
has never once applied.

Sizes are 139×53 in Latvian / 96×53 in English, stepping down twice for narrow
screens. Fixing the specificity exposed a real overflow the broken version had
been hiding: a properly-padded "REZERVĒT" no longer fits a phone header beside a
full logo and the EN|LV switch. The space comes back from the logo, not the
button — at ≤480 px the badge and wordmark shrink, at ≤420 px once more, and at
≤374 px the lockup becomes mark-only. Measured slack at every step, per language;
Latvian is always the binding case, and its tightest point is **+21 px at 375 px**.

---

## The reviews page

`reviews.html` (EN) / `atsauksmes.html` (LV). One job: **mirror the salon's Google
reviews** and send anyone who wants to add one to Google.

Two sections, and that is the whole page — hero (live Google score + "write one on
Google" + "read them all") then the wall of 46 cards. It used to collect reviews
with photographs too; see "The on-page review form was removed" below.

### Google reviews

**46 real reviews are on the page today**, out of the 83 the profile has. The
score block reads **4.9 from 83** — the live figure, covering all of them.

| | |
|---|---|
| Data file | `build/google-reviews.json` (49 reviews with text + the place stats) |
| Refresh | `python build/fetch-google-reviews.py` |
| Renderer | `build/google_reviews.py` → `{{GOOGLE_SCORE}}`, `{{GOOGLE_CTA}}`, `{{GOOGLE_REVIEWS}}` |
| place_id | `ChIJR-MLMsHP7kYRfQuq0DiyK4M` (cid `9451844200055835517`) |
| Write-review link | `search.google.com/local/writereview?placeid=<place_id>` |
| Read-them-all link | `search.google.com/local/reviews?placeid=<place_id>` |

Those two Google URL forms take a place_id and nothing else, which is why the
place_id is the identifier worth keeping. Both were checked to resolve to *this*
salon — the write-review one 302s to a Google sign-in that continues into the
review composer, which is correct: you cannot leave a Google review anonymously.

**Rendered at build time, not fetched in the browser.** Same reason as the
salon's own list: this is the one page whose entire content is words, and a
client-side fetch into an empty container is invisible to a crawler. It also
means no third-party widget script and nothing to lay out after first paint.

**The text is verbatim and never translated.** Every other string on the site
exists twice and the English page is generated from the Latvian — these do not.
A review is a named person's own words; running them through a string table
would be inventing a quote. So the same review text appears on both language
pages, in whatever language it was written in (21 LV, 23 EN, 4 RU), with a
`lang=` attribute per card so a screen reader pronounces it right and the browser
can offer its own translation. Only the chrome around the cards is translated.
That is what `data-verbatim` on the section is for: `assemble.py`'s "no
untranslated Latvian on the English page" sweep skips it deliberately.

**No `Review` / `aggregateRating` structured data, anywhere.** Google's own
guidelines forbid a site marking up reviews *of itself* — "self-serving reviews"
— and it earns a manual action rather than stars in the SERP. The 4.9 is shown to
the visitor and left unmarked for the crawler. `check-deploy.py` fails if anyone
adds it later.

#### Moderation — say this to the client in one sentence

The wall shows reviews rated **4 or 5 with text** (`MIN_RATING` in
`fetch-google-reviews.py`). That currently hides three: a 2★ about being charged
30 € instead of 25 € for a child's cut, a 1★, and a 3★. Reviews with no text are
never stored — there is nothing to render and they are already in the average.

It is a testimonial wall, so that is the normal choice, but it is a choice: the
page does **not** show every review. What keeps it honest is that the live 4.9 /
83 sits directly above it next to a link to Google's own list, which is complete,
always current, and not ours to edit. To take one specific review down, add its
id to `HIDDEN` in `fetch-google-reviews.py` and rebuild.

#### How the refresh works, and what to switch on

`fetch-google-reviews.py` has two sources and **only ever adds** — a merge that
could delete would wipe the archive down to five reviews the first time it ran,
and it would look like it had worked.

| source | what it gets | cost | card? |
|---|---|---|---|
| **`apify`** *(default, in use)* | **all 83** | **$0.05/run**, ~$0.22/mo weekly, out of a **$5/mo free credit** | **no** |
| `places` | rating, count, newest ~5 | free (1,000 calls/mo) | **yes — this is why it is not used** |

**Google Maps Platform requires a billing account on every key, even inside the
free tier.** That ruled `places` out. `apify` is the
`compass/Google-Maps-Reviews-Scraper` actor on Apify's free plan, which needs no
card; it bills PAY_PER_EVENT at **$0.0006 per review**, so ~85 reviews is about
five cents, and every run also carries `maxTotalChargeUsd=0.50` as a hard stop in
case a misconfigured input ever tried to scrape a thousand places.

The honest caveat: `apify` is scraping, which Google's Maps terms do not invite.
`--source places` is the cleaner answer the day a card is acceptable, and it is a
one-word change. The fully-official *card-free* route is the **Google Business
Profile API** — it returns everything, lets the salon reply, and costs nothing —
but it needs a verified GBP 60+ days old, an access-request form approved by
Google, and OAuth refresh-token plumbing. That is a project, not a setting.

`--dataset <id>` / `--file <path>` re-read a harvest that already happened, for
free. The archive was seeded that way.

#### The refresh runs in GitHub Actions

`.github/workflows/augusts-google-reviews.yml`:

> weekly cron → `fetch-google-reviews.py` → `assemble.py` → `check-deploy.py` →
> **commits `build/google-reviews.json` + `site/`** → Netlify's continuous
> deployment picks up the push and deploys.

Running the deploy gate *before* the commit is deliberate: a bad render fails the
job instead of shipping.

**The Netlify build does NOT fetch**, and that is worth naming as a decision. It
used to. But the fetch needs a credential, so having it in both places would mean
the same secret stored twice, a scraper firing on every unrelated deploy, and two
writers racing over what the archive says. Netlify's build command is now just
`python3 build/assemble.py` — it renders what is in the repo. One fetcher, one
place.

**A Netlify scheduled function did this first** and was deleted: it pinged a build
hook, so the merged file died with the build container. `check-deploy.py` fails if
a `[functions."refresh-reviews"]` block reappears while the workflow exists.

##### Connecting it up

**This folder is its own git repository** — `github.com/dans-sharpify/augusts-reviews`,
on `main`. It is deliberately NOT the whole `meta-ad-generator` tree: that is
~10,000 files and about 1 GB, 978 MB of which is other clients' projects, and
connecting it to Netlify would hand a third party read access to all of them. This
repo is 83 files and 8.5 MB. (`meta-ad-generator/.git` also exists, from an old
`git init` with zero commits and no remote — inert.)

Netlify is connected with **base directory empty** (the repo root *is* the site).
Two things left, both in the GitHub repo:

1. *Settings → Secrets and variables → Actions → New repository secret* →
   **`APIFY_TOKEN`**, from `console.apify.com` → *Settings → API & Integrations*.
   No card, no billing account. Sign-up gives the $5/month credit.
2. *Settings → Actions → General → Workflow permissions* → **Read and write**
   (the job pushes a commit).

Then *Actions → AUGUSTS — refresh Google reviews → Run workflow* to test it now
instead of waiting for Monday.

**Test the token locally first** — it is only exercised once a week, so a bad one
would sit silent:

```powershell
$env:APIFY_TOKEN = "apify_api_..."
python build/fetch-google-reviews.py --dry-run
```

`--dry-run` starts a real run and writes nothing. What the answers mean:

| output | meaning |
|---|---|
| `place: Frizierdarbnīca AUGUSTS — 4.9 from 83` | working |
| `401: User was not found or authentication token is not valid` | wrong token |
| `APIFY_TOKEN is not set` | the env var did not reach the process |
| `apify run … ended FAILED` | the actor itself broke; the run URL is in the message |
| `the harvest came back empty` | it ran but scraped nothing — treated as an error, not as "no reviews" |

Every one of those is a **warning, not a failure**: the fetch exits 0 and leaves
the committed archive alone, so a bad token can never break a build or a deploy.
It only means the reviews stop moving — which is why `check-deploy.py` warns once
the archive is 45 days old.

##### Line endings — `.gitattributes` is not cosmetic

The pages are generated on two platforms: by hand on Windows, where Python's
`write_text` emits CRLF, and by the weekly Action on `ubuntu-latest`, where it
emits LF. Without `* text=auto` the repo stores whichever the last writer used, so
the Action's "did anything change?" test —

```
git diff --quiet -- build/google-reviews.json site/
```

— sees **all 54 files in `site/` as modified on every run**, and commits and
deploys a "refresh Google reviews" every week whether or not a single review
changed. A real change would then be invisible in a diff that rewrites every line
of every page.

Verified rather than assumed: all 39 text blobs in the repo contain zero CR bytes,
and rewriting a page with LF (what the runner does) produces no diff. Careful with
how you check this — `git show :path` applies the checkout filter and shows CRLF
even when the stored blob is LF; use `git cat-file blob <hash>`.

With no key set the fetch warns and exits 0, so both the Action and the Netlify
build stay green and simply change nothing. That is deliberate — it must not look
like a failure before it is set up.

`fetch-google-reviews.py` also stays in the Netlify build command, which is
harmless and occasionally useful: it tops the archive up on any manual deploy too,
and no-ops without a key. `check-deploy.py` warns once the file is 45 days old, so
a cron that quietly stopped shows up instead of going unnoticed for a year.

### The on-page review form was removed — deliberately

The page used to also **collect** reviews: a form with a star rating and three
photo slots, posting to Netlify Forms as `atsauksme`, with its own two thank-you
pages and browser-side image compression. It is gone, and this is the record of
why so nobody rebuilds it by accident.

It could not publish itself. A submission landed in the Netlify Forms inbox and
stayed there until a person copied it into a source file and rebuilt — deliberate,
because unmoderated stranger-written text and photographs on a client's own domain
with no fast take-down path is not a feature. The client did not want a recurring
manual step, so rather than keep a queue nobody would drain, **everything now
points at Google**, which was already the better destination: a Google review
shows on Maps, feeds local search, and refreshes onto this page by itself.

**It was possible to automate.** Netlify Forms fires a `submission-created` event;
a function on that event can commit the review through the GitHub API and trigger
exactly the rebuild the Google wall already uses. That was offered and declined —
auto-publish means stranger text plus up to three uploaded photographs are live on
the salon's domain within about a minute with nobody in the loop, and the client
preferred not to carry that risk for a channel Google already covers.

What went with it: `build/reviews.py`, `build/thankyou-review.template.html`,
`site/thank-you-review.html`, `site/paldies-atsauksme.html`,
`site/assets/js/reviews.js`, `i18n.py`'s `TY_REVIEW_*` tables, two `robots.txt`
disallows, and **20 orphaned CSS rules** — the star-rating radios, the three photo
slots and the form's own surface. Nine pages became seven; `app.css` lost 11 %.

The one thing genuinely lost is **customer photos**, which the Places API does not
return. Their Instagram gallery still carries work photos, and at least one client
(Zane Viksne) attached photos to her *Google* review, which are visible on Google.

Three guards now keep this decision from rotting, all proven to fire:

- `assemble.py` fails if a review page grows a `<form>` at all.
- `check-deploy.py` fails on any reference to `thank-you-review.html`,
  `paldies-atsauksme.html`, `assets/js/reviews.js`, `name="atsauksme"` or
  `name="bilde<n>"`, anywhere on the site.
- `check-deploy.py` warns on **any** class selector in the CSS that no page uses.
  Removing a feature is exactly when dead CSS accumulates, and guessing which
  star rules to delete would have either shipped 5 KB of nothing or broken the
  Google cards — `.stars__out` / `.star--on` are shared, `.stars` / `.stars__row`
  were not.

## Photo slots — what to drop in when the shoot arrives

Every one of these is a **file swap plus `python build/assemble.py`**. No markup
changes. `assemble.py` fails the build if a referenced file is not on disk, so a
typo cannot ship as a broken image.

| slot | file | size | today |
|---|---|---|---|
| Maija's portrait | `assets/img/team-maija.webp` + `-sm` | 512 / 256 square | ✅ **in place** |
| The film's forest | `assets/img/mezs-fons.webp` | ≥ 2000 px wide, landscape | ✅ **in place** (generated — see below) |
| Service card ×6 | `isie-mati`, `krasu-palete`, `garie-vilni`, `zils-mati`, `studio-portret`, `viriesu-griezums` | ≥ 1000 px, 4:5 or square | in place, see below |

### The film's forest

`assemble.py` emits **either** the drawn birch `forest.svg` **or** two photo
layers, depending on whether `site/assets/img/mezs-fons.webp` exists. Delete the
file and the drawing comes back. Both layers are the same file — one download —
and `film.js` already scrubs `.forest--near` and `.forest--far` at different
rates, so the parallax is free.

**Today it is a generated frame, matched to their own photoshoot.** The client
asked for "a forest like in this photoshoot but without a person" and sent the
birch photo. That photo is already in the library as `mezs-logo.webp` — and it is
360 × 640, portrait, with a person and the old ring lockup burned into the middle
of it. There was nothing to upscale from, so `build/gen-forest.py` generates a
landscape birch stand in the same look (KIE `google/nano-banana`, 4 credits each,
3 candidates kept in `build/raw/`), and `build/make-forest-photo.py` grades it:

- **2000 px wide, 298 KB.** A stand of a hundred thin high-contrast trunks is
  near worst-case for WebP, so the file grows fast with width — 2400 px costs
  404 KB for detail no scrimmed background layer can show.
- **No sharpening pass.** The obvious move after a 1.8× upscale is an unsharp
  mask, and it works — at +30 % file size, fighting the one quality the frame is
  meant to have. Upscale softness in a fog photograph reads as fog.
- **No srcset, deliberately.** These layers are `object-fit: cover`, so on a
  portrait viewport the fit is driven by **height** — a 16:9 frame covering a 9:16
  screen shows the middle third of its width, magnified. A phone needs *more*
  image width than a desktop, and `sizes="100vw"` says the opposite; measured, it
  picked the small file at 500 × 860 and stretched it 2.4×. If the weight ever
  needs to come down, the answer is an art-directed **portrait** frame behind
  `<source media="(orientation: portrait)">`, not a width-based srcset.
- **The grade is baked in**, because the CSS applies no filter and no blur on
  purpose: a runtime filter over a full-viewport surface is exactly the
  total-surface repaint this film was rebuilt to avoid.

To swap in a real frame from the shoot when it arrives: drop it at
`build/raw/mezs-fons-src.png` and rerun `make-forest-photo.py`. Ask for landscape,
≥ 2000 px, light and open, nothing important in the middle (the mark sits there),
no logo burned in.

#### The scrim had to be re-tuned for a photograph

The drawn SVG was near-black, so the existing scrim was gentle. Over a bright
fog it left the yellow wordmark at **2.96 : 1** median and **1.86 : 1** against
the brightest patches — measured by shooting the hero with the mark hidden and
computing contrast against the background pixels inside the mark's own box, not
judged by eye. Three changes, re-measured to **4.99 : 1** median / **3.49 : 1**
worst:

1. `.forest--photo::after` mid stop `.34` → `.42`.
2. A radial pool of shade on **`.forest--photoNear::after`**, not the far layer.
   Two reasons: `--near` is z-index 3 and `--far` is 1, so a scrim on the far
   layer is painted *under* the near layer's own bright trunks; and `film.js`
   drives that layer's opacity, so the pool arrives and leaves with the forest
   instead of darkening the five chapters after it. Radial, so the forest stays a
   bright misty forest at the edges — the whole reason to use a photograph.
3. A `text-shadow` on the address kicker only, scoped by
   `.forest--photo ~ .beats .beat--hero .kicker`. It sits below the pool where the
   fog is brightest and was at 2.8 : 1 where small text wants 4.5 : 1; widening
   the pool that far flattens the frame. A text-shadow on a handful of static
   glyphs is not the thing the no-filter rule is about.

Scroll jank after the swap: **p50 16.7 / p95 16.8 ms**, identical to the v2/v3
baseline. The photograph is free.

### The six service cards

`#pakalpojumi` opens with six photo cards (Griezums, Matu krāsošana, Balināšana,
Spilgtie toņi, Veidošana, Bārdas formēšana) above the price list. The whole card
is the booking link, so the photograph is clickable rather than decoration beside
one.

They currently reuse six frames from the gallery below, cropped square at a
tighter `object-position`. **That is the honest constraint, not a choice:** the
whole library is eleven hair photographs, capped at 640 px by Instagram. Six
service photographs from the new shoot would fix it, and the filenames above are
where they go.

### Square crops

`#darbi` is now rounded squares (the 70s arch crop is gone, at the client's
request), and so are the service cards. **Every source is 4:5**, so a square crop
throws away a fifth of the frame and the browser's default `50% 50%` takes it off
the top — which is where the heads are. Four of the eight gallery images were
beheaded by it. Each `<img>` therefore carries its own `object-position`, chosen
against a contact sheet of that photo cropped at 0 / 20 / 35 / 50 / 70 / 100 %.
Re-derive them if a photo is swapped; do not assume the old number transfers.

---

## The scroll-film

Unchanged from v2 — one continuous shot in six chapters (Mežs → Ogas → Krāsa →
Miera 19 → Spogulis → Draugs) that scrubs as you scroll and melts into the price
list, driven by ~9 KB of vanilla JS (`assets/js/film.js`). No GSAP, no
ScrollTrigger, no Lenis. Every stage is `position: sticky` and nothing is ever
pinned.

Two consequences worth knowing before editing:

- **`overflow-x` on `body` is `clip`, not `hidden`.** `hidden` makes body a
  scroll container, which silently kills every sticky stage — and the failure is
  invisible to assertions, because the beats still measure correct opacity while
  the stage renders as an empty background.
- **No CSS `scroll-behavior: smooth`.** Anchors get a per-call smooth scroll from
  JS instead. The `html:not(.js)` path keeps the CSS glide.

Copy changes: the address beat no longer says *"Otrais stāvs"* (there is no second
floor), and the hero's kicker is now just the address — `FRIZIERDARBNĪCA` moved
inside the mark.

### Performance

Measured headful at 1440 with a warm cache, the boot window discarded, and the
walk split so the film can be told apart from the content below it. Each variant
was run against the same page with `.mark__ring { display: none }` to isolate the
cost of the hero mark.

**p50 is 16.7 ms in every band of every run, rings shown or hidden** — the median
frame is a clean 60 Hz and the mark does not move it.

p95, max and the over-50 ms count are *noisy run to run in both variants*, and
they do not order consistently: in one pass the rings-hidden film band logged 4
and 7 frames over 50 ms while rings-shown logged 1 and 8. That is measurement
noise on a busy desktop, not a signal — so the honest statement is that the mark
is **not distinguishable from noise**, not that the page is uniformly 0-over-50.
The spikes track the lazy-loaded gallery/team images decoding and the third-party
Calendly iframe booting as they scroll in; they appear with the mark removed too.

An earlier version of this section carried a tidy four-row table claiming a clean
0/0 for the film and a precise A/B split. It did not survive being re-run, and is
gone. Three harness rules, each of which produced a wrong number here:

- **Warm the cache and discard the boot window explicitly.** Cold first paint
  lands in the first sample and reads as scroll jank.
- **Measure with `--disable-frame-rate-limit` OFF.** With it on, rAF fires
  ~1000×/s and the meter reports p50 0.9 ms, comparable to nothing.
- **Do not print only the last N windows.** The original "0 frames over 50 ms for
  the whole page" was exactly that artefact — the window containing the
  lazy-decode band fell off the end of the report.

Getting the median to a solid 16.7 ms in the first place took one real fix, still
in place: the grain
is a background **layer** on each section, not a `position: fixed` full-viewport
overlay. As an overlay it has to be re-composited on every scrolled frame across
the whole page — bisecting showed the grain **and** the berry canvas each costing
~16 ms of p95 *independently*, the signature of a total-surface problem rather
than one bad element. Moving it took p95 from 49.7 ms to 16.9 ms.

### Fallbacks

- **`prefers-reduced-motion`** — the film collapses to a static 100vh hero; the
  mark's rings are already at full opacity.
- **No JavaScript** — same static hero via `html:not(.js)`; every booking link is
  a real URL.
- **Reveals default to VISIBLE.** `.js` is set in `<head>` for the film, so a
  `.no-js` guard cannot protect the content sections; `app.js` adds
  `reveal-ready` immediately before wiring the observer. If it 404s or throws,
  the page is simply all there.

### Dev contract

`?jump=<scrollY>` lands pre-scrolled with all scroll state force-settled, and
`window.__ready = true` fires only when the page is genuinely ready. `?jank=1`
logs p50/p95/max/over-50 ms to the console.

---

## Icons

14 hand-drawn engraving-style glyphs, inline SVG (`build/icons.svg`), single ink
on a 48 grid with light crosshatch. They inherit `currentColor`, so one set
serves rust-on-paper in the price list and gold-on-ink in the contact block, and
they cost no requests.

**KIE was not used: the account is at 0.9 credits and `createTask` returns
`402 Credits insufficient`.** `build/gen-icons.py` is written and ready —
`python build/gen-icons.py --generate` then `--fetch` (~8 credits) produces two
2×2 engraving plates and slices them into alpha masks. It encodes the traps that
matter: one grid per set (style drift), prompt a printing process not a look,
isolated objects not scenes, alpha zero-point from the histogram **mode** (a
percentile floor leaves a visible square halo on dark grounds), and separate
generate/fetch steps because the result CDN 403s without a browser UA and a
download failure would otherwise lose paid generations.

---

## Where the content came from

**Services and prices** — scraped from the three live GHL booking widgets
(rendered headlessly; the price list is client-side, so the raw HTML has none of
it). All 16 services are reproduced with their exact prices and durations.

**Staff names and portraits** — from the staff-selection step inside those same
widgets, one click deeper than the service list; see *The team section* above for
the full path and why nothing above that step is usable.

**Photography** — 12 images from `@augusts08`. The public profile API is hard
rate-limited (429) and the profile is login-walled past the first grid, so these
were captured by rendering the profile in headless Chrome. Instagram serves feed
images at **640 px** on the long edge and the 1080 px variants 403.

**Palette** — `--gold #B5A56B` and `--taupe #8E8A7B` are lifted verbatim from the
CSS custom properties on the client's own fortic.io pages. `--rust`, `--sage`,
`--tan` and the forest greens are sampled from the Instagram photography.

**Copy** — the headline *"Ienāc kā svešinieks, aizej kā draugs"* is their own
Instagram bio. Service descriptions are the client's own wording; the English is
a translation of it, not a rewrite.

---

## Deploying

`netlify.toml` sets `publish = "site"`, so `build/` and `_qa/` never ship. There
is no build command — the site is static.

`check-deploy.py` asserts the things that fail *silently after* a deploy:

- **Netlify Forms**, on both language pages: the form is named, carries
  `data-netlify="true"`, contains the hidden `form-name` input (without it
  Netlify rejects the POST with a 404), declares a honeypot that exists, has a
  name on every control, and redirects to a page that exists. The visible form
  and the static detection copy must declare **identical** field names.
- **Both pages must declare the same field set**, because they post to the same
  form name and Netlify registers one schema for it. If they drift, one
  language's submissions arrive against a schema that does not describe them.
- **No leftover GoHighLevel**: `leadconnectorhq.com`, `msgsndr.com` and
  `fortic.io` must not appear, and every Calendly URL must be the expected one.
- **Every service row carries a booking link** — row count == link count.
- **Languages**: each page declares its `lang`, links to the other, marks exactly
  one active switch item, has all three `hreflang` alternates, and the two have
  distinct canonicals.
- every `assets/…` reference exists (including inside `srcset`, and **including
  CSS `url()`** — the fonts and the grain tile are referenced only from the
  stylesheets, so an orphan sweep that reads markup alone flags them wrongly)
- all seven routing files present, both thank-you pages `noindex` and disallowed
- no build artefacts, no `localhost`/`file://` URLs, no root-absolute paths
- **the CSS and JS revalidate on every request.** See below — this one has already
  produced a broken page once.

### The cache header that breaks the page

`must-revalidate` does **not** mean "check every time". It only forbids serving a
response once it has gone *stale*; inside `max-age` the browser uses its copy
without asking. This file used to set `max-age=604800, must-revalidate` on the CSS
while the HTML was always revalidated — which is seven days of blind caching, so a
deploy that touched a stylesheet shipped **new markup against a week-old
stylesheet** to every returning visitor.

This page fails hard that way rather than gracefully, because the affected
selectors only exist in the newer CSS:

- the header language switch loses its pill and renders as bare `ENLV`
- the logo's ring drops out of position — a loose empty circle under the wordmark
- the hero mark's two rings fall *below* `/08/ AUGUSTS FRIZIERDARBNĪCA` instead of
  around them
- the header CTA collapses back to a nav link's padding

Reproduced deliberately (`_qa/repro-stale-css.png` vs `repro-fresh-css.png`) by
rendering the current markup with this session's selectors neutralised — it is
pixel-for-pixel the failure a client reported as "works different on different
browsers", which is what a per-browser cache state looks like from the outside.

Fixed twice over, because a header is one config edit away from regressing:

1. **`assemble.py` appends `?v=<content hash>` to every CSS/JS reference.** The URL
   now changes when the bytes change, which is the actual requirement. Filenames
   stay stable so a photo can still be swapped in place. Verified that a query
   string resolves over `file://` — tested on the real page, not assumed, since the
   off-disk preview is a hard requirement here.
2. CSS and JS are `max-age=0, must-revalidate`; images get an hour; fonts keep
   their immutable year because they are subset once and never re-emitted. This
   also covers `404.html`, which is hand-maintained and therefore unhashed.

`check-deploy.py` guards both: it fails if a CSS/JS TTL grows, if a reference
loses its `?v=`, **or if a `?v=` no longer matches the hash of the file on disk** —
that last one catches editing a stylesheet and forgetting to rerun `assemble.py`,
which would otherwise ship a stale-but-plausible version string that caches
forever. Confirmed by touching `app.css` and watching the check fail with the
expected hash, then pass after a rebuild.

Two gaps worth stating: assets referenced from *inside* a stylesheet by bare
filename (the `.woff2` in the `@font-face` blocks) are not hashed — stable by
construction, but if the subset is ever regenerated, rename them or drop the
immutable font header. And `404.html` relies on the header alone.

It has already earned its keep twice: it caught a `_control.html` left in the
deploy directory by a crashed performance harness, and — with the assertions
above — a doc comment in the team section whose example `src=` was being scanned
as a real asset reference.

### The form

`pieteikums` — Vārds, Telefons, Pakalpojums, Ziņa, plus hidden `language`. Plain
static HTML posting to Netlify Forms, no JS, honeypot on `bot-field`, redirecting
to `thank-you.html` (EN) or `paldies.html` (LV). Submissions land in **Netlify →
Forms**.

This form is **not** the booking — it is the "no suitable time, call me back"
fallback. Bookings go through Calendly and never touch Netlify.

### Two settings that assume a domain

`augusts08.lv` is hard-coded in the canonical URLs, the `hreflang` block,
`sitemap.xml`, `robots.txt`, the JSON-LD, and the inline calendar's
`embed_domain`. Change those if the domain differs.

---

## Please confirm with the client

1. **English as the main language.** As asked — `/` is English and Latvian is a
   click away. Worth knowing that Latvian-speaking visitors from Google now land
   on English first; if local search matters more than walk-in tourists, the two
   can be swapped by exchanging the `file` values in `i18n.py`.
2. **Adele's 50% discount** — live in their old booking system today; still on?
   And is `Adele Axelle` how she should be named on the site?
3. **The still-live GHL calendars** — see the warning above. The client has said
   more Calendly event types are coming later, which resolves the one-hour issue;
   the old calendars staying reachable is the remaining booking risk.
5. **Opening hours.** Sources disagree — directories list Mon–Fri **10:00–20:00**,
   one aggregator says 10:00–19:00. The page and the `HairSalon` structured data
   say **10:00–20:00**. Weekends shown as closed; no source listed weekend hours.
6. **Email is now `mieraaugusts@gmail.com`** everywhere on the site (page copy,
   `mailto:`, JSON-LD, the review page's take-it-down line).
   `check-deploy.py` fails if any other address reappears. **Calendly still sends
   from `kristine-augusts`** — that account moves to the new address once the
   client hands over the login, and the booking URL changes with it.
7. **Second phone number.** `+371 29 943 399` appears in directories but not on
   their own site, so it is not shown.
8. One typo was corrected in their copy: *"diez gan noturīgas"* → *"diezgan
   noturīgas"*.
9. **Maija Goldberga's bio.** Only her languages came from the client; the two
   sentences of bio were written to match the other cards. Have her read them.
10. **There is no way to leave a review on the site any more** — the form was
   removed and every route now goes to Google. Worth confirming Kristīne is happy
   with that, since it also means no customer photos.
11. **The Google wall shows 46 of their 83 reviews** — the ones rated 4–5 with
   text. Three real reviews are filtered out, one of them a 2★ about a child's
   haircut being charged at 30 € instead of the quoted 25 €. That is worth a
   conversation on its own terms, and worth confirming they are happy with a
   testimonial wall rather than a complete mirror. See "Moderation" above.
12. **Four stylists appear in the reviews who are not on the site**: *Melita*
   (three reviews, all 2026), *Raivo* (three, 2026), *Jānis* and *Elīna*. The team
   section has Kristīne, Adele and Maija. Either the section is out of date or
   those people have left — ask, because a visitor who reads "Hairdresser Melita
   was amazing" and then finds no Melita has been told two different things.
13. **The Google refresh is built but not switched on.** It needs a
   `GOOGLE_MAPS_API_KEY`, and the repo needs to exist on GitHub — there is no git
   remote today and no commits. Until then the page shows the committed archive,
   complete as of the date in `build/google-reviews.json`. See "Two ways to run
   it".
14. **The "we'll take it down if you change your mind" promise is gone** with the
   form. Nothing on the site now publishes anything a visitor wrote, so there is
   nothing to promise. A Google review can only be removed by its author or by
   Google.

## Known limits

- **Instagram images are 640 px.** Fine for the gallery and the six service cards
  as laid out, but they cannot carry a full-bleed hero. That is why the film's
  forest is a generated frame in their look rather than their own photograph — see
  "The film's forest". For a real one, ask for originals.
- **The six service cards reuse gallery frames.** Eleven hair photographs is the
  entire library; six of them appear twice on the front page, cropped differently.
- `mezs-logo.webp` has the **old white ring lockup** burned into it, so the
  gallery still shows a version of the mark in the previous colour. Only a new
  export of that photograph fixes it.
- The gallery deliberately omits their "JOIN OUR TEAM" recruitment graphic.
- Calendly's time-slot buttons keep their own blue focus ring; that colour is not
  exposed as an embed parameter.
- **Netlify Forms free tier: 100 submissions/month**, shared across the callback
  form and the review form, and review photos meter against storage.

## Rebuilding assets

Fonts are Fraunces + Work Sans + Courier Prime, subset to a Latvian+English
charset and merged across `latin`/`latin-ext` into one file per family — 124 KB
total instead of 535 KB, and Latvian text costs one download per family instead
of two. All Latvian glyphs (`ĀāČčĒēĢģĪīĶķĻļŅņŠšŪūŽž`) are asserted present after
subsetting.

## QA

`_qa/` holds the film contact sheets, per-beat captures, fallback screenshots and
probe output. `v4-*` are the current bilingual captures; `v2`/`v3` are from this
same pass and `film-*` predate it.

Asserted at 1440 / 820 / 390 px, **on both language pages**, all passing:

- zero horizontal overflow, zero clipped labels (buttons, nav links and the
  language pill are probed individually — a flex button clips its own text
  *inside* a box that still fits the viewport, so a document-width probe never
  sees it), zero stuck reveals, zero broken images, zero console errors
- the sticky stage actually pins; `?jump` lands exactly
- scroll jank at the v2 baseline, headful (table above)

Interaction-tested: service tabs; the per-service modal (correct per-service
title, correct URL with its `utm_content`, calendar renders *inside* the frame
with 18 bookable days, body-scroll lock, focus to the close button, Esc closes,
the iframe is torn down, focus returns to the trigger); the language switch both
ways — including that the film's HUD chapter name flips Mežs ↔ Forest, the form's
redirect target, and the hidden language field; both thank-you pages linking back
to their own language's home.

Fallbacks captured for `prefers-reduced-motion`, JS-disabled and `file://`.

Three harness lessons, all of which produced false failures in this pass:

- **`captureBeyondViewport` does not paint cross-origin iframes.** A full-element
  screenshot of the booking section showed the Calendly card with an empty space
  where the month grid should be — while a probe inside the frame confirmed 18
  bookable days were rendered. It also catches reveals mid-transition. Use
  viewport screenshots after scrolling, not element screenshots, for anything
  containing a third-party frame.
- **`--disable-frame-rate-limit` invalidates the jank meter** (see above).
- **`display: contents` elements report a zero-size bounding box**, so summing
  `nav.children` widths to check the header's width budget silently undercounts —
  `.nav__links` is `display: contents`. Trust the overflow and per-element
  clipping probes instead.
- **Disable the page cache in the probe** (`page.setCacheEnabled(false)`). A CSS
  edit measured across pages in one browser session reported the *old* box for
  the header button three runs in a row, which read exactly like "the rule isn't
  applying".
- **Probe the logo for clipping too, not just buttons and links.** `.hdr__logo` is
  a flex item with `min-width: auto`, so when the header runs out of room it
  squeezes its own wordmark rather than overflowing the document — a
  document-width probe stays at 0 while the lockup is visibly crushed.
- Scroll probes must **await between steps**: a synchronous `scrollTo` loop never
  yields, so IntersectionObserver never fires and every reveal looks broken.
