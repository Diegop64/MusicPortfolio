/* DolmosMusic v2 · créditos desplegables, pantalla de YouTube y formulario.
   El reproductor de YouTube solo se carga cuando alguien pulsa reproducir
   (youtube-nocookie.com), y se elimina al cerrar el crédito. */
(function () {
  'use strict';
  var T = window.DM_I18N || {};

  function embedUrl(video, list) {
    var q = 'autoplay=1&rel=0&playsinline=1&modestbranding=1';
    if (list) q += '&list=' + encodeURIComponent(list);
    return 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(video) + '?' + q;
  }

  function play(credit, video, list) {
    var screen = credit.querySelector('.screen');
    var frame = screen.querySelector('iframe');
    if (!frame) {
      frame = document.createElement('iframe');
      frame.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      frame.allowFullscreen = true;
      frame.referrerPolicy = 'strict-origin-when-cross-origin';
      frame.title = (T.player || 'YouTube') + ': ' + credit.dataset.title;
      screen.appendChild(frame);
      var start = screen.querySelector('.screen-start');
      if (start) start.remove();
    }
    frame.src = embedUrl(video, list);
  }

  function stop(credit) {
    var screen = credit.querySelector('.screen');
    var frame = screen.querySelector('iframe');
    if (!frame) return;
    frame.remove();
    screen.insertAdjacentHTML('beforeend', credit.querySelector('template.screen-facade').innerHTML);
    bindStart(credit);
    credit.querySelectorAll('.track[aria-current]').forEach(function (t) { t.removeAttribute('aria-current'); });
  }

  function setOpen(credit, open) {
    credit.classList.toggle('is-open', open);
    var btn = credit.querySelector('.credit-toggle');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    var panel = credit.querySelector('.credit-panel');
    if (open) panel.removeAttribute('inert'); else { panel.setAttribute('inert', ''); stop(credit); }
  }

  function bindStart(credit) {
    var start = credit.querySelector('.screen-start');
    if (!start) return;
    start.addEventListener('click', function () {
      var first = credit.querySelector('.track');
      if (first) first.click();
      else play(credit, credit.dataset.video, credit.dataset.list);
    });
  }

  var credits = Array.prototype.slice.call(document.querySelectorAll('.credit'));
  credits.forEach(function (credit) {
    bindStart(credit);
    credit.querySelector('.credit-toggle').addEventListener('click', function () {
      var open = !credit.classList.contains('is-open');
      if (open) credits.forEach(function (c) { if (c !== credit && c.classList.contains('is-open')) setOpen(c, false); });
      setOpen(credit, open);
      // a work without a tracklist has nothing to choose: start it right away
      if (open && !credit.querySelector('.track')) play(credit, credit.dataset.video, credit.dataset.list);
    });
    credit.querySelectorAll('.track').forEach(function (track) {
      track.addEventListener('click', function () {
        credit.querySelectorAll('.track').forEach(function (t) { t.removeAttribute('aria-current'); });
        track.setAttribute('aria-current', 'true');
        play(credit, track.dataset.video, '');
      });
    });
  });

  var openFirst = document.querySelector('[data-open-first]');
  if (openFirst && credits[0]) {
    openFirst.addEventListener('click', function () {
      if (!credits[0].classList.contains('is-open')) credits[0].querySelector('.credit-toggle').click();
    });
  }

  /* "Ask for process examples": prefill the message so the request is clear */
  document.querySelectorAll('[data-prefill]').forEach(function (a) {
    a.addEventListener('click', function () {
      var msg = document.querySelector('.contact-form textarea[name="message"]');
      if (msg && !msg.value.trim()) msg.value = a.dataset.prefill;
      var name = document.querySelector('.contact-form input[name="name"]');
      if (name) setTimeout(function () { name.focus({ preventScroll: true }); }, 600);
    });
  });

  /* Contact form: send with fetch, show the result inline instead of alert() */
  var form = document.querySelector('.contact-form');
  if (form) {
    var status = form.querySelector('.form-status');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      status.classList.remove('is-error');
      if (!form.checkValidity()) {
        status.textContent = T.formInvalid; status.classList.add('is-error');
        var bad = form.querySelector(':invalid'); if (bad) bad.focus();
        return;
      }
      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true; status.textContent = T.formSending;
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } })
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          form.reset(); status.textContent = T.formSent;
        })
        .catch(function () { status.textContent = T.formError; status.classList.add('is-error'); })
        .then(function () { btn.disabled = false; });
    });
  }
})();
