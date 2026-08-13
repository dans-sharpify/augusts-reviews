#!/usr/bin/env python
"""AUGUSTS — KIE icon plates. READY TO RUN, NOT YET RUN.

Blocked on 2026-08-04: the account was at 0.9 credits and createTask returned
    402 "Credits insufficient".
The site currently ships hand-drawn inline SVG (build/icons.svg) instead, which
looks good and costs no requests. This script exists so swapping in generated
engraving plates is one command once credits are back.

    python build/gen-icons.py --generate     # create the 2x2 grid tasks
    python build/gen-icons.py --fetch        # download + slice + alpha-mask

Cost: 2 grids x ~4 credits = ~8 credits.

Why it is built this way (all learned the hard way, see memory
feedback_kie_engraving_icon_grids):
  * ONE 2x2 grid per set, never 4 separate calls — a grid guarantees the four
    plates share a style; separate calls drift.
  * Name a PRINTING PROCESS ("engraving", "etching", "crosshatch"), not a look
    ("flat", "minimal") — process words steer nano-banana far harder.
  * Prompt ISOLATED OBJECTS. Scene prompts produce pretty little landscapes that
    turn to grey smudges at a 64px tinted mask.
  * Say NO text / faces / borders explicitly — it adds all of them otherwise.
  * Alpha zero-point comes from the histogram MODE, not a low percentile. A
    percentile floor leaves grain alive as low alpha and every icon renders with
    a visible square halo on dark grounds.
  * The result CDN 403s without a browser User-Agent, and URLs expire — hence
    --generate and --fetch are separate, keyed by a saved taskId, so a download
    failure never loses paid generations.
"""
import argparse, json, os, pathlib, sys, time, urllib.request

BASE = "https://api.kie.ai"
KEY = os.environ.get("KIE_API_KEY", "")
HERE = pathlib.Path(__file__).resolve().parent
TASKS = HERE / "kie-tasks.json"
RAW = HERE / "kie-raw"
OUT = HERE.parent / "site" / "assets" / "img" / "icons"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

STYLE = (
    "Vintage botanical field-guide ENGRAVING plate. Fine black crosshatch line-art "
    "etching, single ink colour, off-white paper, no halftone dots. "
    "Four separate subjects arranged in a clean 2x2 grid, generous white space "
    "between them. Each subject is an ISOLATED OBJECT floating on plain paper with "
    "nothing around it: no landscape, no horizon line, no ground plane, no scenery, "
    "no cast shadow, no frame, no panel divider. "
    "NO text, NO letters, NO numbers, NO labels, NO borders, NO faces, NO people, "
    "NO hands, NO watermarks, NO signature."
)

GRIDS = {
    # the four services the price list is organised around
    "services": "Top-left: a pair of open barber scissors. Top-right: a ceramic tint "
                "bowl with a tinting brush resting in it. Bottom-left: a folded sheet "
                "of foil wrapped around a lock of hair. Bottom-right: a single "
                "falling droplet of liquid.",
    # the brand / contact set
    "brand":    "Top-left: a sprig of rowan berries with three berries and two leaves. "
                "Top-right: an oval hand-mirror standing on a small foot. Bottom-left: "
                "a closed straight razor. Bottom-right: a simple panelled wooden door, "
                "closed, seen straight on.",
}


def api(path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"},
        method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def credits():
    return api("/api/v1/chat/credit").get("data")


def generate():
    bal = credits()
    need = len(GRIDS) * 4
    print(f"balance {bal} credits; this run needs ~{need}")
    if isinstance(bal, (int, float)) and bal < need:
        sys.exit(f"ABORT: need ~{need} credits, have {bal}. Top up and re-run.")
    tasks = json.loads(TASKS.read_text()) if TASKS.exists() else {}
    for name, subjects in GRIDS.items():
        if tasks.get(name):
            print(f"{name}: already has task {tasks[name]}, skipping"); continue
        r = api("/api/v1/jobs/createTask", {
            "model": "google/nano-banana",
            "input": {"prompt": f"{STYLE} {subjects}",
                      "output_format": "png", "image_size": "1:1"}})
        if r.get("code") != 200:
            print(f"{name}: FAILED {r.get('code')} {r.get('msg')}"); continue
        tasks[name] = r["data"]["taskId"]
        print(f"{name}: task {tasks[name]}")
        TASKS.write_text(json.dumps(tasks, indent=1))   # persist immediately
    print(f"\nsaved -> {TASKS}\nnow run:  python build/gen-icons.py --fetch")


def fetch():
    from PIL import Image
    import numpy as np
    tasks = json.loads(TASKS.read_text())
    RAW.mkdir(exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    NAMES = {"services": ["scissors", "colour", "foil", "drop"],
             "brand": ["rowan", "mirror", "razor", "door"]}
    for name, tid in tasks.items():
        grid = RAW / f"{name}.png"
        if not grid.exists():
            url = None
            for _ in range(60):
                d = api(f"/api/v1/jobs/recordInfo?taskId={tid}").get("data", {})
                st = d.get("state")
                if st == "success":
                    url = json.loads(d["resultJson"])["resultUrls"][0]; break
                if st == "fail":
                    print(f"{name}: FAILED server-side"); break
                time.sleep(5)
            if not url:
                continue
            req = urllib.request.Request(url, headers={"User-Agent": UA})  # 403s without this
            grid.write_bytes(urllib.request.urlopen(req, timeout=120).read())
            print(f"{name}: downloaded {grid.stat().st_size // 1024} KB")

        im = Image.open(grid).convert("L")
        w, h = im.size
        for i, sub in enumerate(NAMES[name]):
            q = im.crop(((i % 2) * w // 2, (i // 2) * h // 2,
                         (i % 2 + 1) * w // 2, (i // 2 + 1) * h // 2))
            a = 255 - np.asarray(q, dtype=np.int16)          # invert: ink -> high
            hist = np.bincount(a.clip(0, 255).ravel(), minlength=256)
            paper = int(hist[:128].argmax())                 # MODE, not a percentile
            ink = float(np.percentile(a, 99.4))
            m = ((a - (paper + 15)) / max(1.0, ink - paper - 15) * 255).clip(0, 255)
            out = Image.merge("RGBA", [Image.new("L", q.size, 0)] * 3 +
                              [Image.fromarray(m.astype("uint8"))])
            bb = out.getbbox()
            if bb:
                out = out.crop(bb)
            out.thumbnail((160, 160), Image.LANCZOS)         # size to display, not source
            p = OUT / f"{sub}.webp"
            out.save(p, "WEBP", quality=72, alpha_quality=90, method=6)
            print(f"  {sub}.webp {p.stat().st_size // 1024} KB {out.size}")
    print("\nProof the masks at real display size on BOTH grounds before adopting.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--balance", action="store_true")
    a = ap.parse_args()
    if not KEY:
        sys.exit("KIE_API_KEY not set")
    if a.balance:
        print(credits())
    elif a.generate:
        generate()
    elif a.fetch:
        fetch()
    else:
        ap.print_help()
