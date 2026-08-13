# -*- coding: utf-8 -*-
"""Generate the film's forest background: the client's own photoshoot location,
without the person and without the wordmark burnt in.

Their photo (site/assets/img/mezs-logo.webp) is 360x640 with the AUGUSTS ring
over it — too small for a full-viewport hero and not landscape, so this matches
the LOOK rather than reusing the pixels: young Latvian birch stand, misty
overcast light, autumn floor.

    python gen-forest.py            # 3 candidates
    python gen-forest.py --one      # 1
"""
import json, os, sys, time, urllib.request, urllib.error

KEY = os.environ["KIE_API_KEY"]
BASE = "https://api.kie.ai"

# What the reference photo actually looks like, written down: slim white birches
# with black lenticels, thin tops, fog swallowing the far trunks, a floor of moss
# and fallen leaves, and light that is bright but completely diffuse. The CSS
# lays a dark gradient over this, so it must be BRIGHT — a moody dark forest
# turns to mud under the scrim.
LOOK = (
    "Photograph of a young Latvian birch forest in early autumn. Many slim, "
    "closely spaced white birch trunks with fine black lenticel markings, "
    "receding in layers into pale grey mist so the far trunks dissolve. "
    "Thin bare upper branches, sparse yellowing leaves. Forest floor of deep "
    "green moss, low bilberry undergrowth and scattered fallen ochre leaves, "
    "a few mossy fallen branches. Bright but completely diffuse overcast light, "
    "no sun, no shadows, soft luminous haze between the trunks. "
    "Muted desaturated palette: cool grey-greens, birch white, rust and ochre "
    "accents. Shot on 35mm colour film, natural fine grain, gentle contrast, "
    "documentary and unstyled. Wide landscape composition, camera at eye level, "
    "trunks running to the top of the frame, floor visible across the bottom third."
)
NEG = (
    "Absolutely no people, no person, no figure, no silhouette, no face, no hands, "
    "no clothing, no animals. No text, no letters, no numbers, no logo, no "
    "watermark, no signature, no frame, no border, no dark vignette. No path, "
    "no road, no fence, no buildings, no signs. Not a dark night forest, not "
    "sunlit with hard shadows, not autumn-orange saturated, not HDR, not "
    "illustration, not painting, not 3D render."
)

VARIANTS = [
    ("a-dense", "Dense stand: the trunks fill the frame evenly with no single hero tree."),
    ("b-depth", "One birch a little closer on the left third, the rest falling away into "
                "mist behind it, giving the frame clear depth."),
    ("c-open",  "A slightly more open stand with visible gaps of pale mist between groups "
                "of trunks, and more of the mossy floor showing."),
]


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def get(path):
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def credits():
    return get("/api/v1/chat/credit")["data"]


def generate(tag, extra, size="16:9"):
    prompt = f"{LOOK} {extra} {NEG}"
    try:
        res = post("/api/v1/jobs/createTask", {
            "model": "google/nano-banana",
            "input": {"prompt": prompt, "output_format": "png", "image_size": size},
        })
    except urllib.error.HTTPError as e:
        print(f"  {tag}: createTask {e.code} — {e.read().decode()[:300]}")
        return None
    if res.get("code") != 200:
        print(f"  {tag}: {res}")
        return None
    tid = res["data"]["taskId"]
    print(f"  {tag}: task {tid}")
    for _ in range(90):
        time.sleep(4)
        info = get(f"/api/v1/jobs/recordInfo?taskId={tid}")["data"]
        state = info.get("state")
        if state == "success":
            url = json.loads(info["resultJson"])["resultUrls"][0]
            out = f"forest-{tag}.png"
            # The result host 403s a request with no User-Agent.
            dl = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(dl, timeout=180) as r, open(out, "wb") as f:
                f.write(r.read())
            print(f"  {tag}: -> {out}")
            return out
        if state == "fail":
            print(f"  {tag}: FAILED {info.get('failMsg')}")
            return None
    print(f"  {tag}: timed out")
    return None


if __name__ == "__main__":
    before = credits()
    print(f"credits before: {before}")
    todo = VARIANTS[:1] if "--one" in sys.argv else VARIANTS
    for tag, extra in todo:
        generate(tag, extra)
    after = credits()
    print(f"credits after: {after}  (spent {before - after:.2f})")
