# -*- coding: utf-8 -*-
"""Trace the salon's real logo out of their print artwork into build/logo.svg.

    input   C:/Users/Dell/Downloads/August Front.pdf   (the file the client sent)
    output  build/logo.svg        an <svg> sprite of <symbol>s, for the header,
                                  the footer and the thank-you / 404 pages
            build/logo-hero.svg   the same lockup INLINE, one <path> per letter

The hero needs its own copy because `<use>` puts the symbol's contents in a shadow
tree: a stylesheet outside it cannot reach the individual letters, and the hero's
opening move is a per-letter stagger. Both are generated here from the same trace,
so they cannot drift.

Why trace instead of setting a font: the logo is a geometric sans set in a
typeface we do not have a licence for and cannot subset, and the page's own
display face is Fraunces — a wonky serif. Rebuilding the wordmark in Fraunces is
what the site did before this round, and it is not the salon's mark. The PDF
carries the letterforms as filled vector paths, so the mark itself can ship: 26
paths, ~4 KB, exact.

Two things about the extraction:

  * PyMuPDF hands back each contour as a LIST OF SEGMENTS, not a path. Emitting
    one `M…L…` per segment draws the outline but leaves every counter (the hole
    in A, U, G, 8, R, B) filled solid, because nonzero winding needs the counter
    to be its own closed subpath. Segments are chained instead, and a new subpath
    is started whenever a segment does not begin where the previous one ended.

  * Coordinates are kept in PDF user space, only translated so the lockup's own
    bounding box starts at 0,0. PDF y already grows downward here, which is also
    SVG's direction, so no flip.

The brand colour comes out of the file as well — rgb(1, 0.9487, 0) = #FFF200,
process yellow. It is written into the CSS as --brand-yellow, not hardcoded here:
the symbols paint in `currentColor` so one lockup can be gold on the thank-you
page and yellow in the header without a second copy.
"""
import pathlib
import sys

import fitz

HERE = pathlib.Path(__file__).resolve().parent
SRC = pathlib.Path(r"C:\Users\Dell\Downloads\August Front.pdf")
OUT = HERE / "logo.svg"
OUT_HERO = HERE / "logo-hero.svg"

# Which drawing indices make up which line of the lockup. Read off the y bands of
# the artwork: /08/ sits above the wordmark, FRIZIERDARBNĪCA below it.
BANDS = [("no", 93.0, 103.0), ("word", 104.0, 120.0), ("sub", 123.0, 129.0)]


def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s or "0"


def chain(items, dx, dy):
    """Segments -> a path with one closed subpath per contour."""
    out, cur = [], None

    def P(pt):
        return f"{fmt(pt.x - dx)} {fmt(pt.y - dy)}"

    def near(a, b):
        return abs(a.x - b.x) < 1e-3 and abs(a.y - b.y) < 1e-3

    for it in items:
        op = it[0]
        if op == "re":                      # the tiny FRIZIERDARBNĪCA stems
            r = it[1]
            if cur:
                out.append("Z")
            cur = None
            out.append(f"M{fmt(r.x0 - dx)} {fmt(r.y0 - dy)}"
                       f"H{fmt(r.x1 - dx)}V{fmt(r.y1 - dy)}H{fmt(r.x0 - dx)}Z")
            continue
        start, end = it[1], it[-1]
        if cur is None or not near(cur, start):
            if cur is not None:
                out.append("Z")
            out.append(f"M{P(start)}")
        if op == "l":
            out.append(f"L{P(end)}")
        elif op == "c":
            out.append(f"C{P(it[2])} {P(it[3])} {P(end)}")
        else:
            raise SystemExit(f"unhandled path op {op!r}")
        cur = end
    if cur is not None:
        out.append("Z")
    return "".join(out)


def main():
    if not SRC.exists():
        sys.exit(f"missing source artwork: {SRC}")
    page = fitz.open(SRC)[0]
    drawings = [d for d in page.get_drawings() if d.get("fill")]

    colours = {tuple(round(c, 4) for c in d["fill"]) for d in drawings}
    if len(colours) != 1:
        sys.exit(f"expected one fill colour in the artwork, found {colours}")
    r, g, b = colours.pop()
    brand = "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))

    x0 = min(d["rect"].x0 for d in drawings)
    y0 = min(d["rect"].y0 for d in drawings)
    x1 = max(d["rect"].x1 for d in drawings)
    y1 = max(d["rect"].y1 for d in drawings)

    lines = {}
    for name, top, bottom in BANDS:
        band = [d for d in drawings if top <= d["rect"].y0 <= bottom]
        band.sort(key=lambda d: d["rect"].x0)          # left to right
        lines[name] = [chain(d["items"], x0, y0) for d in band]

    missing = [n for n, paths in lines.items() if not paths]
    if missing:
        sys.exit(f"no glyphs landed in band(s) {missing} — the artwork moved")

    def box(name):
        top, bottom = next((t, b) for n, t, b in BANDS if n == name)
        band = [d for d in drawings if top <= d["rect"].y0 <= bottom]
        return (min(d["rect"].x0 for d in band) - x0, min(d["rect"].y0 for d in band) - y0,
                max(d["rect"].x1 for d in band) - x0, max(d["rect"].y1 for d in band) - y0)

    def viewbox(names):
        bx0 = min(box(n)[0] for n in names)
        by0 = min(box(n)[1] for n in names)
        bx1 = max(box(n)[2] for n in names)
        by1 = max(box(n)[3] for n in names)
        # A hairline of padding: the paths run right to the edge of their own box
        # and a viewBox flush against them clips the outermost pixel when the
        # symbol is scaled down and antialiased.
        pad = 0.15
        return (f"{fmt(bx0 - pad)} {fmt(by0 - pad)} "
                f"{fmt(bx1 - bx0 + pad * 2)} {fmt(by1 - by0 + pad * 2)}"), (bx1 - bx0), (by1 - by0)

    def groups(names, indent="  "):
        """The three lines of the lockup, each in its own <g> so the hero can
        bring them in one at a time. `fill="currentColor"` is per-path and not
        inherited from a parent <svg>: inside a <use> shadow tree the paths would
        otherwise fall back to the SVG default fill, which is black — invisible on
        this page's near-black header, which is exactly how it fails."""
        rows = []
        for n in names:
            rows.append(f'{indent}<g class="lg__{n}">')
            for i, d in enumerate(lines[n]):
                # AUGUSTS is per-letter so the hero can stagger the reveal the way
                # the old Fraunces wordmark did, one <span> per letter.
                attr = f' class="lg__l" style="--i:{i}"' if n == "word" else ""
                rows.append(f'{indent}  <path{attr} fill="currentColor" d="{d}"/>')
            rows.append(f"{indent}</g>")
        return rows

    def symbol(sid, names, note):
        vb, _, _ = viewbox(names)
        return "\n".join([f'<symbol id="{sid}" viewBox="{vb}">', f"<!-- {note} -->"]
                         + groups(names) + ["</symbol>"])

    head = [f"<!-- generated by build/gen-logo.py from {SRC.name} — do not hand-edit.",
            f"     The salon's own artwork, traced. Brand colour in the file: {brand}. -->"]

    OUT.write_text("\n".join(
        head
        + ['<svg class="lg-defs" width="0" height="0" aria-hidden="true" focusable="false">',
           "<defs>",
           symbol("lg-full", ["no", "word", "sub"],
                  "the full stacked lockup: /08/ over AUGUSTS over FRIZIERDARBNICA"),
           symbol("lg-word", ["word"], "AUGUSTS alone, one path per letter"),
           symbol("lg-no", ["no"], "the /08/ badge alone"),
           symbol("lg-sub", ["sub"], "FRIZIERDARBNICA alone"),
           "</defs>", "</svg>", ""]), encoding="utf-8")

    vb, w, h = viewbox(["no", "word", "sub"])
    OUT_HERO.write_text("\n".join(
        head
        + [f'<svg class="mark__logo" viewBox="{vb}" aria-hidden="true" focusable="false">']
        + groups(["no", "word", "sub"]) + ["</svg>", ""]), encoding="utf-8")

    print(f"brand colour   {brand}")
    print(f"artwork box    {fmt(x1 - x0)} x {fmt(y1 - y0)} pt  (aspect {w / h:.3f})")
    for name, paths in lines.items():
        bw, bh = box(name)[2] - box(name)[0], box(name)[3] - box(name)[1]
        print(f"  {name:5s} {len(paths):2d} glyph(s)   {fmt(bw)} x {fmt(bh)}  aspect {bw / bh:.2f}")
    for f in (OUT, OUT_HERO):
        print(f"wrote {f.relative_to(HERE.parent)}  {f.stat().st_size // 1024 or 1} KB")


if __name__ == "__main__":
    main()
