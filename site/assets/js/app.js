/* AUGUSTS /08/ — plain script, no modules (an ES module is blocked on file://
   and the client previews this page straight off disk). */
(function () {
  'use strict';


  /* Booking is the salon's own Calendly. There is no calendar URL in this file
     on purpose: every trigger is a real <a href> to it, so the flow still works
     with JS off (and with this script 404ing) — the script only upgrades the
     link into an in-page modal. Nothing here needs translating either, which is
     why one app.js serves both language variants. */

  /* ---------------- generic tab group ----------------
     `sel` selects the buttons, `onPick` gets the chosen key. */
  function tabs(sel, attr, onPick) {
    var btns = Array.prototype.slice.call(document.querySelectorAll(sel));
    if (!btns.length) return;

    function pick(btn) {
      btns.forEach(function (b) { b.setAttribute('aria-selected', String(b === btn)); });
      onPick(btn.getAttribute(attr), btn);
    }
    btns.forEach(function (b) {
      b.addEventListener('click', function () { pick(b); });
      b.addEventListener('keydown', function (e) {
        var i = btns.indexOf(b), n = null;
        if (e.key === 'ArrowRight') n = btns[(i + 1) % btns.length];
        if (e.key === 'ArrowLeft') n = btns[(i - 1 + btns.length) % btns.length];
        if (n) { e.preventDefault(); n.focus(); pick(n); }
      });
    });
  }

  /* ---------------- services: swap price panels ---------------- */
  tabs('.tab[data-panel]', 'data-panel', function (key) {
    ['women', 'men', 'kids'].forEach(function (k) {
      var p = document.getElementById('panel-' + k);
      if (!p) return;
      p.hidden = (k !== key);
      // panels start hidden, so their reveal observer never fired
      if (k === key) p.classList.add('is-in');
    });
  });

  /* ---------------- booking modal ----------------
     The title's base text is read out of the markup once, so the localised
     string lives on the page and not in here. A trigger's `data-svc` is
     appended to it, which is what tells the visitor which service they clicked
     — the calendar itself offers a single appointment type. */
  var modal = document.getElementById('bookModal');
  var modalBody = document.getElementById('bookModalBody');
  var modalTitle = document.getElementById('bookModalTitle');
  var modalNewTab = document.getElementById('modalNewTab');
  var modalClose = document.getElementById('bookModalClose');
  var titleBase = modalTitle ? modalTitle.textContent.trim() : '';
  var lastFocus = null;

  /* Framed Calendly needs three extra parameters that a top-level link must not
     have. `embed_type=Inline` suppresses Calendly's cookie dialog — without it a
     large consent panel opens across the calendar — and drops their page
     background to transparent so the modal's own paper shows through. The link
     the visitor may open in a new tab stays clean. */
  function embedded(url) {
    return url + (url.indexOf('?') < 0 ? '?' : '&')
      + 'embed_domain=' + encodeURIComponent(location.hostname || 'augusts08.lv')
      + '&embed_type=Inline&hide_gdpr_banner=1'
      + '&primary_color=b4502e&background_color=f4efe3&text_color=12140e';
  }

  function openModal(url, svc) {
    if (!modal || !url) return;
    var label = svc ? titleBase + ' · ' + svc : titleBase;
    lastFocus = document.activeElement;
    modalTitle.textContent = label;
    modalNewTab.href = url;
    // built on open, torn down on close — so the calendar isn't loaded (or left
    // running) behind a closed dialog
    modalBody.innerHTML = '';
    var f = document.createElement('iframe');
    f.src = embedded(url);
    f.title = label;
    modalBody.appendChild(f);
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    modalClose.focus();
  }

  function closeModal() {
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    modalBody.innerHTML = '';           // stop the embed from running in the background
    document.body.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener('click', function (e) {
    var trigger = e.target.closest ? e.target.closest('[data-book]') : null;
    if (trigger) {
      var href = trigger.getAttribute('href') || '';
      // An in-page anchor is a scroll, not a booking — never let a `#…` target
      // end up as the modal iframe's src.
      if (href.charAt(0) === '#' || !href) return;
      e.preventDefault();
      openModal(trigger.href, trigger.getAttribute('data-svc'));
      return;
    }
    if (e.target === modal) closeModal();          // click the backdrop
  });

  if (modalClose) modalClose.addEventListener('click', closeModal);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeModal();
  });

  /* ---------------- header: float over the film's opening frame ----------
     Recomputed idempotently from one scroll read rather than toggled by
     enter/leave handlers — a pair of handlers fight each other at boundaries
     and under a forced scroll settle the wrong one wins. */
  var hdr = document.getElementById('hdr');
  if (hdr) {
    var floatUp = function () {
      hdr.classList.toggle('hdr--float', scrollY < 40);
    };
    floatUp();
    addEventListener('scroll', floatUp, { passive: true });
  }

  /* ---------------- reveal on scroll ----------------
     Opacity + translateY only. A clip-path: inset(100%) start state makes the
     element report zero intersection, so the observer would never fire. */
  var targets = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) {
    Array.prototype.forEach.call(targets, function (t) { t.classList.add('is-in'); });
  } else {
    // Arm the hidden start state only now, immediately before the observer
    // that will undo it — so a failure anywhere above this line leaves the
    // content plainly visible rather than blank.
    document.documentElement.classList.add('reveal-ready');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.classList.add('is-in');
          io.unobserve(en.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });
    Array.prototype.forEach.call(targets, function (t) { io.observe(t); });
  }
})();
