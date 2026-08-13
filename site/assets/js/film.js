/* ==========================================================================
   AUGUSTS — scroll-film engine

   No GSAP, no ScrollTrigger, no Lenis. One lerped playhead drives one
   render(p) that writes transform / opacity / one background-color and
   nothing else. Progress comes from a single getBoundingClientRect read.

   This is a deliberate choice over the library stack: a sticky-only film
   measured p95 16.8ms this way, and it sidesteps the pin-spacer ordering law,
   percentage-`end` resolution, refresh-vs-smooth-scroll corruption, and the
   lerped-wrapper "the page feels detached" complaint that comes with Lenis.

   Plain script, not a module — this page is previewed off file://.
   ========================================================================== */
(function () {
  'use strict';

  var film = document.getElementById('film');
  if (!film) return;

  var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var JUMP = new URLSearchParams(location.search).get('jump');

  /* ---------------------------------------------------------------- chapters
     Each chapter owns a slice of progress and a sky colour. The engine
     interpolates the sky between consecutive stops, so the whole film is one
     continuous colour journey: forest green → rowan rust → warm gold → ink →
     paper. `light` flips the HUD/chrome to ink over the pale frames. */
  var CHAPTERS = [
    { id: 'mezs',     name: 'Mežs',       sky: [16, 23, 15] },
    { id: 'ogas',     name: 'Ogas',       sky: [31, 26, 18] },
    { id: 'krasa',    name: 'Krāsa',      sky: [58, 32, 20] },
    { id: 'iela',     name: 'Miera 19',   sky: [18, 20, 16] },
    { id: 'spogulis', name: 'Spogulis',   sky: [26, 28, 24] },
    { id: 'draugs',   name: 'Draugs',     sky: [30, 34, 26] }
  ];

  /* The HUD's chapter names are the only localised strings the engine touches,
     so they come from `data-chapters` on the section instead of living here —
     one film.js then serves index.html (EN) and lv.html (LV) unchanged. The
     hard-coded names above stay as the fallback if the attribute is missing. */
  var labels = (film.dataset.chapters || '').split('|');
  if (labels.length === CHAPTERS.length) {
    CHAPTERS.forEach(function (c, i) { c.name = labels[i].trim() || c.name; });
  }

  var N = CHAPTERS.length;

  var stage    = film.querySelector('.film__stage');
  var sky      = film.querySelector('.sky');
  var forestN  = film.querySelector('.forest--near');
  var forestF  = film.querySelector('.forest--far');
  var berries  = film.querySelector('.berries');
  var door     = film.querySelector('.door');
  var doorlight= film.querySelector('.doorlight');
  var mirror   = film.querySelector('.mirror');
  var seam     = film.querySelector('.seam');
  var hudName  = film.querySelector('.hud__name');
  var hudNum   = film.querySelector('.hud__n');
  var hudFill  = film.querySelector('.hud__fill');
  var cue      = film.querySelector('.scrollcue');
  var wordmark = film.querySelector('.wordmark');
  var plates   = [].slice.call(film.querySelectorAll('.plate'));
  var beats    = [].slice.call(film.querySelectorAll('.beat')).map(function (el) {
    return {
      el: el,
      in:   parseFloat(el.dataset.in),
      peak: parseFloat(el.dataset.peak),
      out:  parseFloat(el.dataset.out),
      rise: parseFloat(el.dataset.rise || '26')
    };
  });

  /* --------------------------------------------------------------- helpers */
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function smooth(t) { return t * t * (3 - 2 * t); }

  /* Narrow screens have no room for copy beside an image, so the whole film
     re-stages: imagery moves to the upper half, copy to the lower. Plates
     carry `data-mx`/`data-my` for that layout; `mob` is re-read on resize. */
  var mob = innerWidth < 760;
  function plateX(d) { return mob && d.mx !== undefined ? +d.mx : +d.x || 0; }
  function plateY(d) { return mob && d.my !== undefined ? +d.my : +d.y || 0; }
  // door and mirror sit beside their copy on desktop, above it on mobile
  function stageX(deskVw) { return mob ? 0 : deskVw; }
  function stageY(deskPx, mobPx) { return mob ? mobPx : deskPx; }

  /* 0 → 1 → 0 envelope with a hold at the top. `out > 1.5` means "never fade"
     (the finale). */
  function envelope(b, p) {
    if (p <= b.in || p >= b.out) return 0;
    if (p < b.peak) return smooth((p - b.in) / Math.max(1e-4, b.peak - b.in));
    if (b.out > 1.5) return 1;
    return 1 - smooth((p - b.peak) / Math.max(1e-4, b.out - b.peak));
  }

  /* ------------------------------------------------------- static fallbacks */
  if (reduced) {
    film.classList.add('film--static');
    if (wordmark) wordmark.classList.add('is-in');
    window.__ready = true;
    return;
  }

  /* ------------------------------------------------------------ the driver */
  function layout() {
    // (100 + (n-1)*92)vh — one screen to read chapter one, then ~0.92 of a
    // screen of scroll per transition.
    film.style.height = (100 + (N - 1) * 92) + 'vh';
  }
  layout();

  var target = 0, playhead = 0, running = false, lastP = -1, lastSky = '';

  function progress() {
    var r = film.getBoundingClientRect();
    var span = r.height - innerHeight;
    if (span <= 0) return 0;
    return clamp(-r.top / span, 0, 1);
  }

  /* ---------------------------------------------------------------- berries
     Canvas particles, drawn from one pre-rendered radial sprite. Only ticks
     while the layer is actually visible. */
  var bctx = null, sprite = null, parts = [], bw = 0, bh = 0, bdpr = 1;

  function initBerries() {
    if (!berries) return;
    // These are soft out-of-focus blobs — there is nothing for extra device
    // pixels to resolve, and a full-viewport clearRect at DPR 2 is pure fill
    // cost on every frame of chapter two.
    bdpr = 1;
    bw = berries.clientWidth; bh = berries.clientHeight;
    berries.width = Math.round(bw * bdpr);
    berries.height = Math.round(bh * bdpr);
    bctx = berries.getContext('2d');
    bctx.scale(bdpr, bdpr);

    var s = document.createElement('canvas');
    s.width = s.height = 32;
    var sc = s.getContext('2d');
    var g = sc.createRadialGradient(16, 16, 0, 16, 16, 16);
    g.addColorStop(0, 'rgba(214,92,52,1)');
    g.addColorStop(0.45, 'rgba(180,64,34,.85)');
    g.addColorStop(1, 'rgba(150,50,28,0)');
    sc.fillStyle = g; sc.fillRect(0, 0, 32, 32);
    sprite = s;

    parts = [];
    for (var i = 0; i < 46; i++) {
      parts.push({
        x: Math.random(), y: Math.random(),
        d: 0.35 + Math.random() * 0.65,          // depth → size + speed
        ph: Math.random() * Math.PI * 2,
        sw: 0.4 + Math.random() * 1.2
      });
    }
  }

  var berriesPainted = false;

  function drawBerries(alpha, p) {
    if (!bctx) return;
    if (alpha <= 0.004) {
      // Clear once on the way out, then leave the canvas alone. Clearing a
      // full-viewport canvas every frame for the ~80% of the film where the
      // berries are invisible is a large fill for nothing.
      if (berriesPainted) { bctx.clearRect(0, 0, bw, bh); berriesPainted = false; }
      return;
    }
    bctx.clearRect(0, 0, bw, bh);
    berriesPainted = true;
    var t = p * 40;
    for (var i = 0; i < parts.length; i++) {
      var o = parts[i];
      var size = 4 + o.d * 13;
      var y = ((o.y + p * o.d * 1.5) % 1.2 - 0.1) * bh;
      var x = (o.x * bw) + Math.sin(t * 0.35 + o.ph) * 26 * o.sw;
      bctx.globalAlpha = alpha * (0.28 + o.d * 0.62);
      bctx.drawImage(sprite, x - size / 2, y - size / 2, size, size);
    }
    bctx.globalAlpha = 1;
  }

  /* ------------------------------------------------------------ the render */
  function render(p) {
    /* ---- sky: interpolate between the two bracketing chapter colours ---- */
    var seg = p * (N - 1);
    var ci = Math.min(N - 2, Math.floor(seg));
    var f = smooth(clamp(seg - ci, 0, 1));
    var a = CHAPTERS[ci].sky, b = CHAPTERS[ci + 1].sky;
    var r = Math.round(a[0] + (b[0] - a[0]) * f);
    var g = Math.round(a[1] + (b[1] - a[1]) * f);
    var bl = Math.round(a[2] + (b[2] - a[2]) * f);

    // the last 9% melts to paper so the price list below starts on the exact
    // same colour and there is no visible seam
    var melt = clamp((p - 0.91) / 0.09, 0, 1);
    if (melt > 0) {
      var m = smooth(melt);
      r = Math.round(r + (244 - r) * m);
      g = Math.round(g + (239 - g) * m);
      bl = Math.round(bl + (227 - bl) * m);
    }
    /* Quantise. Writing background-color invalidates the paint of a
       full-viewport surface, so a fresh value on every frame means a
       full-viewport repaint on every frame. In 3/255 steps the gradient is
       still visually continuous across a slow scroll, but most frames now
       write the same string and Chrome skips the repaint entirely. */
    r -= r % 3; g -= g % 3; bl -= bl % 3;
    var col = 'rgb(' + r + ',' + g + ',' + bl + ')';
    if (col !== lastSky) { sky.style.backgroundColor = col; lastSky = col; }
    if (seam) seam.style.opacity = melt;
    film.classList.toggle('film--light', melt > 0.45);

    /* ---- forest: drifts past and clears before the colour chapter ------- */
    var fa = 1 - smooth(clamp((p - 0.10) / 0.16, 0, 1));
    // Two full-viewport SVG layers stay composited (and keep being transformed)
    // at opacity 0 for the remaining 74% of the film unless they are taken out
    // of the paint order outright.
    var fvis = fa > 0.004 ? 'visible' : 'hidden';
    if (forestN) {
      forestN.style.visibility = fvis;
      if (fa > 0.004) {
        forestN.style.opacity = fa * 0.9;
        forestN.style.transform = 'translate3d(0,' + (-p * 260) + 'px,0) scale(1.08)';
      }
    }
    if (forestF) {
      forestF.style.visibility = fvis;
      if (fa > 0.004) {
        forestF.style.opacity = fa * 0.45;
        forestF.style.transform = 'translate3d(0,' + (-p * 120) + 'px,0)';
      }
    }

    /* ---- berries: chapter 2 --------------------------------------------- */
    var ba = smooth(clamp((p - 0.11) / 0.08, 0, 1)) * (1 - smooth(clamp((p - 0.30) / 0.10, 0, 1)));
    if (berries) {
      berries.style.opacity = ba;
      drawBerries(ba, p);
    }

    /* ---- plates ---------------------------------------------------------- */
    for (var i = 0; i < plates.length; i++) {
      var el = plates[i];
      var d = el.dataset;
      var alpha = envelope({
        in: +d.in, peak: +d.peak, out: +d.out
      }, p);
      el.style.opacity = alpha;
      if (alpha <= 0.004) { el.style.visibility = 'hidden'; continue; }
      el.style.visibility = 'visible';
      // local progress across the plate's own window, for drift + scale
      var lp = clamp((p - +d.in) / Math.max(1e-4, +d.out - +d.in), 0, 1);
      var x = plateX(d);
      var y = plateY(d) + (0.5 - lp) * (+d.drift || 70);
      var sc = 1 + (lp - 0.5) * (+d.zoom || 0.12);
      var rot = (+d.rot || 0);
      el.style.transform =
        'translate3d(calc(-50% + ' + x + 'vw), calc(-50% + ' + y + 'px), 0) ' +
        'scale(' + sc.toFixed(4) + ') rotate(' + rot + 'deg)';
    }

    /* ---- the door, chapter 4 -------------------------------------------- */
    var da = envelope({ in: 0.46, peak: 0.585, out: 0.70 }, p);
    if (door) {
      door.style.opacity = da;
      var dl = clamp((p - 0.46) / 0.24, 0, 1);
      door.style.transform =
        'translate3d(calc(-50% + ' + stageX(22) + 'vw), calc(-50% + ' +
        (stageY(0, -140) + (0.5 - dl) * 80) + 'px), 0) ' +
        'scale(' + (0.9 + dl * 0.34).toFixed(4) + ')';
      // the leaf swings open across the second half of the chapter
      var leaf = door.querySelector('.door__leaf');
      if (leaf) leaf.style.transform = 'scaleX(' + (1 - smooth(clamp((dl - 0.45) / 0.5, 0, 1)) * 0.86).toFixed(4) + ')';
    }
    if (doorlight) {
      var gl = smooth(clamp((p - 0.545) / 0.11, 0, 1)) * (1 - smooth(clamp((p - 0.66) / 0.06, 0, 1)));
      doorlight.style.opacity = gl;
      doorlight.style.transform =
        'translate3d(calc(-50% + ' + stageX(22) + 'vw), calc(-50% + ' + stageY(0, -140) + 'px), 0) ' +
        'scale(' + (0.7 + gl * 0.7).toFixed(3) + ')';
    }

    /* ---- the mirror, chapter 5 ------------------------------------------ */
    var ma = envelope({ in: 0.645, peak: 0.755, out: 0.875 }, p);
    if (mirror) {
      mirror.style.opacity = ma;
      mirror.style.visibility = ma <= 0.004 ? 'hidden' : 'visible';
      var ml = clamp((p - 0.645) / 0.23, 0, 1);
      mirror.style.transform =
        'translate3d(calc(-50% + ' + stageX(21) + 'vw), calc(-50% + ' +
        (stageY(0, -150) + (0.5 - ml) * 90) + 'px), 0) ' +
        'scale(' + (0.88 + ml * 0.2).toFixed(4) + ')';
    }

    /* ---- beats ----------------------------------------------------------- */
    for (var j = 0; j < beats.length; j++) {
      var bt = beats[j];
      var al = envelope(bt, p);
      bt.el.style.opacity = al;
      if (al <= 0.004) { bt.el.style.visibility = 'hidden'; continue; }
      bt.el.style.visibility = 'visible';
      bt.el.style.transform = 'translate3d(0,' + ((1 - al) * bt.rise).toFixed(2) + 'px,0)';
    }

    /* ---- HUD ------------------------------------------------------------- */
    var idx = Math.min(N - 1, Math.floor(p * N + 0.0001));
    if (hudName && hudName.dataset.i !== String(idx)) {
      hudName.dataset.i = String(idx);
      hudName.textContent = CHAPTERS[idx].name;
      hudNum.textContent = '0' + (idx + 1) + ' / 0' + N;
    }
    if (hudFill) hudFill.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    if (cue) cue.style.opacity = (1 - clamp(p / 0.05, 0, 1)) * 0.5;
  }

  /* ------------------------------------------------------------- the ticker
     One rAF loop, started on scroll and parked once the playhead has caught
     up — an always-on rAF burns battery for nothing on a static page. */
  function tick() {
    playhead += (target - playhead) * 0.16;
    if (Math.abs(target - playhead) < 0.00012) playhead = target;
    if (playhead !== lastP) { render(playhead); lastP = playhead; }
    if (playhead !== target) { requestAnimationFrame(tick); }
    else { running = false; }
  }

  function onScroll() {
    target = progress();
    if (!running) { running = true; requestAnimationFrame(tick); }
  }

  addEventListener('scroll', onScroll, { passive: true });

  var rt;
  addEventListener('resize', function () {
    clearTimeout(rt);
    rt = setTimeout(function () {
      mob = innerWidth < 760;
      layout(); initBerries();
      target = progress(); playhead = target; lastP = -1;
      render(playhead);
    }, 140);
  }, { passive: true });

  /* --------------------------------------------------------- anchor scroll
     Per-call smooth, so no CSS `scroll-behavior` is needed anywhere and
     nothing can corrupt a measurement. */
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a) return;
    var id = a.getAttribute('href');
    if (id.length < 2) return;
    var t = document.querySelector(id);
    if (!t) return;
    e.preventDefault();
    var top = t.getBoundingClientRect().top + scrollY - 64;
    scrollTo({ top: top, behavior: 'smooth' });
    history.replaceState(null, '', id);
  });

  /* ------------------------------------------------------------------ boot
     Order matters: decode the film photographs, lay out, settle the scroll
     state, run the one-shot entrance, then flag ready. A lazy first decode of
     a film photo mid-scroll is exactly the "glitchy" spike we are avoiding —
     but img.decode() on an image the browser never loads never settles, so
     the whole gate races a deadline. */
  function boot() {
    initBerries();

    if (JUMP !== null) {
      history.scrollRestoration = 'manual';
      scrollTo(0, +JUMP || 0);
    }
    target = progress();
    playhead = target;
    lastP = -1;
    render(playhead);

    // entrance runs AFTER the settle so it can't re-show copy the film has
    // already scrolled past
    if (wordmark) {
      if (playhead > 0.02) wordmark.classList.add('is-in');
      else requestAnimationFrame(function () {
        requestAnimationFrame(function () { wordmark.classList.add('is-in'); });
      });
    }
    window.__ready = true;
  }

  var imgs = [].slice.call(film.querySelectorAll('img'));
  var gate = Promise.all(imgs.map(function (im) {
    if (!im.decode) return Promise.resolve();
    return im.decode().catch(function () {});
  }));
  Promise.race([gate, new Promise(function (r) { setTimeout(r, 2600); })]).then(boot);

  /* ------------------------------------------------------------ jank meter
     ?jank=1 only. Judge p95/max — an average hides an 80ms spike perfectly. */
  if (new URLSearchParams(location.search).has('jank')) {
    var last = performance.now(), d = [];
    (function loop(t) {
      d.push(t - last); last = t;
      if (d.length >= 120) {
        var s = d.slice().sort(function (a, b) { return a - b; });
        console.log('[jank] p50', s[60].toFixed(1),
                    'p95', s[113].toFixed(1),
                    'max', s[s.length - 1].toFixed(1),
                    'over50', d.filter(function (x) { return x > 50; }).length);
        d = [];
      }
      requestAnimationFrame(loop);
    })(performance.now());
  }
})();
