# -*- coding: utf-8 -*-
"""Grade build/raw/mezs-fons-src.png into the film's forest background.

    python build/make-forest-photo.py            # writes both sizes
    python build/make-forest-photo.py --src raw/mezs-fons-alt-open.png

Emits `site/assets/img/mezs-fons.webp` (+ `-sm`), which is the switch: the
moment that file exists, assemble.py stops emitting the drawn birch SVG and
emits the two photographed forest layers instead. Delete it and the drawing
comes back. See "The film's forest" in the README.

WHY THE GRADE IS BAKED IN
-------------------------
film.css puts `object-fit: cover` on these layers and nothing else — no filter,
no blur, no blend mode. A CSS filter over a full-viewport surface is exactly the
total-surface repaint the film was rebuilt to avoid; it cost ~16 ms of p95 on its
own when the grain was a fixed overlay. So every colour decision happens here,
once, at build time.

WHY IT MUST STAY BRIGHT
-----------------------
`.forest--photo::after` already lays a 62% → 34% → 70% dark gradient over the
frame so the wordmark can be read. Darkening the file as well turns the forest
to mud and the mark floats on black. The target below is a mid-grey frame that
the scrim pulls down, not a dark frame the scrim buries.

ONE FILE, TWO LAYERS
--------------------
`--far` uses it at scale 1 and `--near` at scale 1.22 with object-position
50% 55%, so the SAME pixels have to work as both a distant backdrop and a
foreground plane. That is why the source was chosen with detail across the
bottom third: that band is all the near layer ever shows.
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageEnhance, ImageFilter

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE.parent / "site"
OUT = SITE / "assets" / "img" / "mezs-fons.webp"

# 2400px and q80, raised from 2000/q58 at the client's request for more quality.
#
# THE CEILING IS THE SOURCE, not these numbers. nano-banana returns 1344x768 for
# 16:9 and ignores every resolution parameter it accepts — `resolution: 2k`,
# `image_resolution: 2K` and an explicit `2400x1371` all came back 1344x768. So
# this is a 1.8x upscale however it is encoded; raising the target and the quality
# stops the ENCODER from being the limit, it does not add detail that was never
# generated. A genuinely sharper frame needs a real photograph from the shoot.
#
# ONE SIZE, no small variant. These layers are object-fit: cover, so on a portrait
# phone the fit is driven by HEIGHT — a 16:9 frame covering a 9:16 screen shows the
# middle third of its width, magnified. A phone needs MORE image width than a
# desktop, not less, which is the opposite of what a width-based srcset would
# serve it. See the note in assemble.py's forest emitter.
WIDE = 2400


def grade(im):
    """Muted, cool, and tied to the film's palette (--forest #17251C on --ink
    #12140E), without touching overall brightness.

    Split-toning by channel rather than a global colour cast: the shadows take a
    little green so the moss sits with --forest, the highlights take a little
    warmth so the mist reads next to --gold #B5A56B instead of going blue."""
    im = ImageEnhance.Color(im).enhance(0.90)      # the generated moss is a touch vivid
    im = ImageEnhance.Contrast(im).enhance(1.05)
    # DARKER, on purpose: the yellow wordmark (#FFF200) was blending into the fog.
    # The first cut LIFTED this to 1.08 to keep the photograph luminous; the mark
    # matters more than the photograph does. 0.90 lands the frame near 92/255 mean,
    # which measures ~7:1 behind the wordmark — bright enough to still read as a
    # misty forest, dark enough that yellow separates from it. Tuned against the
    # contrast measurement, not by eye.
    im = ImageEnhance.Brightness(im).enhance(0.90)

    r, g, b = im.split()
    # Gentle curves. Each lookup is 256 entries; the maths is per-channel and the
    # amounts are small on purpose — this should be invisible as an effect and
    # only felt as "belongs to this site".
    def curve(ch, shadow, high):
        return ch.point(lambda v: max(0, min(255, int(
            v + shadow * (1 - v / 255) ** 2 + high * (v / 255) ** 2))))
    r = curve(r, -4, +6)     # warmth in the mist, none in the shadows
    g = curve(g, +3, +3)     # a little green throughout
    b = curve(b, -2, -5)     # pull the blue out of the fog
    return Image.merge("RGB", (r, g, b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="raw/mezs-fons-src.png")
    ap.add_argument("--quality", type=int, default=80)
    args = ap.parse_args()

    src = (HERE / args.src) if not pathlib.Path(args.src).is_absolute() else pathlib.Path(args.src)
    if not src.exists():
        sys.exit(f"no source at {src}")

    im = Image.open(src).convert("RGB")
    print(f"source {src.name}  {im.width}x{im.height}")

    im = grade(im)
    h = round(WIDE * im.height / im.width)
    im = im.resize((WIDE, h), Image.LANCZOS)
    # A light pass, now that the encode is no longer the limiting factor: it puts
    # back some of the bark micro-contrast the upscale softened. Kept gentle
    # (threshold 3) so the flat fog stays flat rather than growing halos.
    im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=45, threshold=3))

    small = im.convert("L").resize((64, 64))
    lum = sum(small.getdata()) / (64 * 64)
    print(f"mean luminance {lum:.0f}/255 — the scrim takes this down by 34-70%")
    if lum < 78:
        print("  WARN  darker than intended; the wordmark will float on near-black")
    if lum > 190:
        print("  WARN  brighter than intended; the scrim may not be enough for the mark")

    im.save(OUT, "WEBP", quality=args.quality, method=6)
    kb = OUT.stat().st_size / 1024
    print(f"wrote site/assets/img/{OUT.name}  {im.width}x{im.height}  {kb:.0f} KB")
    # This is the film's first paint. A megabyte here is a stall, not a photo.
    # Raised from 340 KB with the quality bump. Still worth a word in the log: this
    # is the film's first paint, with fetchpriority="high" on it.
    if kb > 760:
        print("  WARN  over 760 KB for the opening frame — drop --quality")

    print("\nnow run: python build/assemble.py   (it will switch to the photo forest)")


if __name__ == "__main__":
    main()
