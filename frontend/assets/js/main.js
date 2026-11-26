/*  VTU Clubs: behaviour only.
    All page markup now lives in index.html. This file:
      - shows/hides pages by URL hash (router)
      - fills the few areas that come from the API (news, gallery photos, admin lists)
      - runs registration, admin, dialogs and the 3D effects                                   */
(() => {
  'use strict';

  /* ---------- config & helpers ---------- */
  const API_BASE = '';
  const CLUBS = ['tech', 'sports', 'culture', 'multimedia', 'management'];
  const PAGES = ['home', 'gallery', 'announcements', 'register', 'admin'];

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const assetUrl = u => (!u || u.startsWith('http://') || u.startsWith('https://')) ? u : API_BASE + u;
  const setSel = (el, v) => { const i = [...el.options].findIndex(o => o.value === v); el.selectedIndex = i < 0 ? 0 : i };

  let csrf = '';
  try { csrf = sessionStorage.getItem('csrf') || '' } catch (e) { }
  const saveCsrf = v => { csrf = v; try { v ? sessionStorage.setItem('csrf', v) : sessionStorage.removeItem('csrf') } catch (e) { } };

  async function api(p, o = {}) {
    const h = {};
    if (o.body) h['Content-Type'] = 'application/json';
    if (o.m && o.m !== 'GET' && csrf) h['X-CSRF-Token'] = csrf;
    const url = p.startsWith('http') ? p : API_BASE + p;
    const r = await fetch(url, { method: o.m || 'GET', headers: h, credentials: 'include', body: o.form || (o.body ? JSON.stringify(o.body) : undefined) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const x = d.detail;
      throw Object.assign(new Error(Array.isArray(x) ? x.map(v => String(v.msg).replace(/^Value error, /, '')).join(', ') : x || 'Request failed'), { status: r.status });
    }
    return d;
  }

  /* ---------- state ---------- */
  let admin = null, NEWS = [], GAL = { items: [], total: 0 };
  let f = 'all', pg = 0;              // gallery filter + page
  let S = {}, PEND = null, LINK = null; // registration
  let cur = '', seq = 0;              // current page, route sequence guard

  /* ---------- router ---------- */
  async function route() {
    const my = ++seq;
    const [r, qs] = location.hash.slice(1).split('?');
    let name = r || 'home';
    if (!PAGES.includes(name) && !CLUBS.includes(name)) name = 'home';
    LINK = new URLSearchParams(qs || '').get('link');
    if (name !== 'gallery') pg = 0;

    try {
      if (name === 'home' || CLUBS.includes(name) || name === 'announcements') NEWS = await api('/api/announcements');
      if (name === 'gallery') GAL = await api(`/api/gallery?page=${pg + 1}&page_size=8${f === 'all' ? '' : '&club=' + f}`);
    } catch (e) { }
    if (my !== seq) return;           // a newer navigation won
    cur = name;

    $$('.page').forEach(p => p.classList.toggle('on', p.dataset.page === name));
    $$('nav a').forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + name));

    if (name === 'home') { renderTicker(); initHome(); }
    else if (CLUBS.includes(name)) renderClubNews(name);
    else if (name === 'gallery') renderGallery();
    else if (name === 'announcements') renderAnnouncements();
    else if (name === 'register') step1();
    else if (name === 'admin') renderAdmin();
    scrollTo(0, 0);
  }
  addEventListener('hashchange', route);

  /* ---------- API-filled sections ---------- */
  function renderTicker() {
    $('#ticker-track').innerHTML = NEWS.map(n => `<span>${esc(n.title)}</span>`).join('') || '<span>No announcements yet. Check back soon.</span>';
  }
  function renderClubNews(k) {
    const ns = NEWS.filter(n => !n.club_slug || n.club_slug === k);
    $(`[data-club-news="${k}"]`).innerHTML = ns.map(n => `<li>${esc(n.title)}</li>`).join('') || '<li>No announcements yet.</li>';
  }
  function renderAnnouncements() {
    $('#ann-list').innerHTML = NEWS.map(n => `<div class="box" style="margin-bottom:12px"><b style="color:var(--gold)">${esc(n.club_name || 'All clubs')}</b><h3>${esc(n.title)}</h3><p>${esc(n.message)}</p></div>`).join('') || '<p>Nothing published yet.</p>';
  }
  function renderGallery() {
    const real = GAL.items || [], has = real.length > 0, n = Math.max(1, Math.ceil(GAL.total / 8));
    $$('[data-f]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.f === f)));

    $('#gal-real').hidden = !has;
    $('#gal-pager').hidden = !has;
    $('#gal-sample').hidden = has;
    $('#gal-note').hidden = has;

    if (has) {
      $('#gal-real').innerHTML = real.map(u => `<button class="ph tilt" data-u="${u.id}" style="background-image:url('${esc(assetUrl(u.image_url))}');background-size:cover" aria-label="Open ${esc(u.title)}"><span>${esc(u.title)}</span></button>`).join('');
      $('#pg-prev').disabled = !pg;
      $('#pg-next').disabled = pg >= n - 1;
      $('#pg-label').textContent = `Page ${pg + 1} of ${n}`;
    } else {
      let shown = 0; // sample tiles: first 8 that match the filter
      $$('#gal-sample .ph').forEach(t => { const ok = (f === 'all' || t.dataset.k === f) && shown < 8; t.hidden = !ok; if (ok) shown++; });
    }
  }

  /* ---------- 3D: parallax + three.js embers + tilt ---------- */
  const RM = matchMedia('(prefers-reduced-motion:reduce)').matches;
  let mx = 0, my = 0;
  addEventListener('pointermove', e => {
    mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5;
    const b = $('#bg'); if (b && !RM) b.style.transform = `translate3d(${-mx * 30}px,${-my * 20}px,0) scale(1.06)`;
  });
  document.addEventListener('pointermove', e => {
    const t = e.target.closest && e.target.closest('.tilt'); if (!t || RM) return;
    const r = t.getBoundingClientRect();
    t.style.transform = `perspective(700px) rotateY(${((e.clientX - r.left) / r.width - .5) * 18}deg) rotateX(${-((e.clientY - r.top) / r.height - .5) * 18}deg) scale(1.04)`;
  });
  document.addEventListener('pointerout', e => { const t = e.target.closest && e.target.closest('.tilt'); if (t) t.style.transform = ''; });

  let gl = null, raf = 0;
  function buildGL(cv) {
    const r = new THREE.WebGLRenderer({ canvas: cv, alpha: true, antialias: true }), sc = new THREE.Scene(), cam = new THREE.PerspectiveCamera(60, 1, .1, 100);
    cam.position.z = 14;
    const N = 700, g = new THREE.BufferGeometry(), p = new Float32Array(N * 3);
    for (let i = 0; i < N * 3; i++) p[i] = (Math.random() - .5) * (i % 3 == 1 ? 26 : 36);
    g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    const pts = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffa83a, size: .09, transparent: true, opacity: .85 })); sc.add(pts);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(5, .04, 8, 120), new THREE.MeshBasicMaterial({ color: 0xf5b942, transparent: true, opacity: .5 })); sc.add(ring);
    const ring2 = ring.clone(); ring2.scale.setScalar(1.35); sc.add(ring2);
    const size = () => { const w = cv.clientWidth, h = cv.clientHeight; if (!w || !h) return; r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); };
    addEventListener('resize', size);
    return { r, sc, cam, g, p, pts, ring, ring2, size };
  }
  function initHome() {
    cancelAnimationFrame(raf);
    const cv = $('#gl'); if (!cv || !window.THREE || RM) return;
    try { gl = gl || buildGL(cv); } catch (e) { return; } // no WebGL: effect is decorative, skip it
    const { r, sc, cam, g, p, pts, ring, ring2, size } = gl;
    size();
    (function loop() {
      if (cur !== 'home') return;      // stop when leaving the home page
      raf = requestAnimationFrame(loop);
      for (let i = 1; i < p.length; i += 3) { p[i] += .012; if (p[i] > 13) p[i] = -13; }
      g.attributes.position.needsUpdate = true;
      pts.rotation.y += .0006;
      ring.rotation.x = 1.2 + Math.sin(Date.now() / 3000) * .2; ring.rotation.y += .004;
      ring2.rotation.x = -1.1; ring2.rotation.z += .003;
      cam.position.x += (mx * 5 - cam.position.x) * .05; cam.position.y += (-my * 3 - cam.position.y) * .05;
      cam.lookAt(0, 0, 0); r.render(sc, cam);
    })();
  }

  /* ---------- clicks / dialog ---------- */
  const dlg = $('#dlg');
  function openDialog(title, { sample, img, sub } = {}) {
    $('#dlg-title').textContent = title;
    const big = $('#dlg-big'), im = $('#dlg-img'), sb = $('#dlg-sub');
    big.hidden = !sample; im.hidden = !img; sb.hidden = !sub;
    if (sample) {
      big.style.backgroundImage = `var(${sample.im})`;
      big.style.backgroundPosition = sample.pos;
      big.setAttribute('aria-label', title);
    }
    if (img) { im.src = img; im.alt = title; }
    if (sub) sb.textContent = sub;
    dlg.showModal();
  }
  document.addEventListener('click', e => {
    const t = e.target, q = s => t.closest(s); let b;
    const nav = $('#nav'), menu = $('#menu');
    if (q('#menu')) { if (menu && nav) menu.setAttribute('aria-expanded', String(nav.classList.toggle('open'))); return; }
    if (nav && (!nav.contains(t) || q('nav a'))) { nav.classList.remove('open'); if (menu) menu.setAttribute('aria-expanded', 'false'); }

    if (b = q('[data-club]')) S.club = b.dataset.club;                 // "Join this club" preselects the club
    if (b = q('[data-gal]')) { f = b.dataset.gal; pg = 0; }            // "Photos" preselects the gallery filter
    if (b = q('[data-f]')) { f = b.dataset.f; pg = 0; route(); }
    if (b = q('[data-pg]')) { pg += +b.dataset.pg; route(); }
    if (b = q('[data-close]')) dlg.close();
    if (b = q('#gal-sample .ph')) openDialog(b.dataset.title, { sample: { im: b.dataset.im, pos: b.dataset.pos } });
    if (b = q('[data-u]')) {
      const u = GAL.items.find(x => x.id == b.dataset.u);
      if (u) openDialog(u.title, { img: assetUrl(u.image_url), sub: `${u.club_name} Club${u.event_name ? ' · ' + u.event_name : ''}` });
    }
  });

  /* ---------- registration (all checks happen on the server) ---------- */
  const showStep = n => [1, 2, 3].forEach(i => { $('#reg-' + i).hidden = i !== n; });

  let resendTimer = null;
  let captchaData = { token: '', code: '' };

  function renderCaptchaCanvas(code) {
    const cv = $('#captcha-canvas');
    if (!cv) return;
    const ctx = cv.getContext('2d');
    const w = cv.width, h = cv.height;
    ctx.clearRect(0, 0, w, h);

    // Dark canvas background with noise
    ctx.fillStyle = '#170f24';
    ctx.fillRect(0, 0, w, h);

    // Background disturbance lines
    for (let i = 0; i < 4; i++) {
      ctx.strokeStyle = ['rgba(245,185,66,0.3)', 'rgba(255,122,26,0.25)', 'rgba(255,255,255,0.15)'][i % 3];
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(Math.random() * w, Math.random() * h);
      ctx.bezierCurveTo(Math.random() * w, Math.random() * h, Math.random() * w, Math.random() * h, Math.random() * w, Math.random() * h);
      ctx.stroke();
    }

    // Characters with distortion / rotation
    const chars = (code || '').split('');
    const charW = (w - 24) / Math.max(1, chars.length);
    chars.forEach((c, i) => {
      ctx.save();
      const x = 14 + i * charW;
      const y = h / 2 + 7 + (Math.random() * 4 - 2);
      const angle = (Math.random() * 22 - 11) * Math.PI / 180;
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.font = 'bold 22px "Source Sans 3", Arial, sans-serif';
      ctx.fillStyle = ['#ffd27a', '#ffa83a', '#f5b942', '#ffffff'][i % 4];
      ctx.shadowColor = 'rgba(0,0,0,0.85)';
      ctx.shadowBlur = 4;
      ctx.fillText(c, 0, 0);
      ctx.restore();
    });

    // Random dots
    for (let i = 0; i < 24; i++) {
      ctx.fillStyle = 'rgba(245,185,66,' + (Math.random() * 0.4 + 0.1) + ')';
      ctx.beginPath();
      ctx.arc(Math.random() * w, Math.random() * h, Math.random() * 1.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  async function loadCaptcha() {
    try {
      const res = await api('/api/auth/captcha');
      captchaData = res;
      renderCaptchaCanvas(res.code);
      const inp = $('#reg-captcha-input');
      if (inp) inp.value = '';
    } catch (e) {
      const fallbackChars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
      let code = '';
      for (let i = 0; i < 5; i++) code += fallbackChars[Math.floor(Math.random() * fallbackChars.length)];
      captchaData = { token: 'local:' + Math.floor(Date.now() / 1000) + ':client:' + Math.random().toString(36).slice(2, 8), code };
      renderCaptchaCanvas(code);
    }
  }

  function startResendTimer(seconds = 60) {
    if (resendTimer) clearInterval(resendTimer);
    const rsBtn = $('#rs');
    if (!rsBtn) return;
    rsBtn.disabled = true;
    let remaining = seconds;
    rsBtn.textContent = `Resend code (${remaining}s)`;
    resendTimer = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        clearInterval(resendTimer);
        resendTimer = null;
        rsBtn.disabled = false;
        rsBtn.textContent = 'Resend code';
      } else {
        rsBtn.textContent = `Resend code (${remaining}s)`;
      }
    }, 1000);
  }

  async function step1(e = {}) {
    const y = new Date().getFullYear();
    if (LINK && !S.linkOk) {
      try { const l = await api('/api/registration-links/' + encodeURIComponent(LINK)); S.club = l.club_slug; S.linkTitle = l.title; S.linkOk = true; }
      catch (x) { S.linkErr = x.message; }
    }
    if (cur !== 'register') return;     // user navigated away while waiting
    showStep(1);
    $('#reg-link-note').hidden = !S.linkOk; $('#reg-link-note').textContent = S.linkOk ? `Registration link: ${S.linkTitle}` : '';
    $('#reg-link-err').hidden = !S.linkErr; $('#reg-link-err').textContent = S.linkErr || '';
    $('#usn').value = S.usn || ''; $('#nm').value = S.nm || ''; $('#em').value = S.em || ''; $('#ph').value = S.ph || '';
    setSel($('#br'), S.br);
    $('#yr').max = y; $('#yr').value = S.yr || y;
    setSel($('#club'), S.club); $('#club').disabled = !!S.linkOk;
    $('#reg-err').textContent = e.form || '';
    const goBtn = $('#go');
    goBtn.disabled = false;
    goBtn.textContent = 'Send OTP';

    const refreshBtn = $('#captcha-refresh');
    if (refreshBtn && !refreshBtn.dataset.bound) {
      refreshBtn.dataset.bound = '1';
      refreshBtn.onclick = () => loadCaptcha();
    }
    if (!captchaData.code || e.reloadCaptcha) {
      loadCaptcha();
    }
  }

  $('#go').onclick = async () => {
    S = { ...S, usn: $('#usn').value.trim(), nm: $('#nm').value.trim(), em: $('#em').value.trim(), ph: $('#ph').value.trim(), br: $('#br').value, yr: $('#yr').value, club: $('#club').value };
    if (!S.usn || !S.nm || !S.em || !S.ph) {
      step1({ form: 'Please fill in all required fields before requesting an OTP.' });
      return;
    }
    const capInp = $('#reg-captcha-input');
    const userCaptcha = capInp ? capInp.value.trim() : '';
    if (!userCaptcha) {
      step1({ form: 'Please enter the security verification captcha code.' });
      if (capInp) capInp.focus();
      return;
    }
    const goBtn = $('#go');
    goBtn.disabled = true;
    goBtn.textContent = 'Sending OTP...';
    try {
      const p = await api('/api/auth/register', {
        m: 'POST',
        body: {
          usn: S.usn,
          full_name: S.nm,
          email: S.em,
          phone: S.ph,
          branch: S.br,
          joining_year: +S.yr,
          club_slug: S.club,
          link_token: LINK || null,
          captcha_token: captchaData.token || null,
          captcha_code: userCaptcha || null
        }
      });
      PEND = p.pending_id;
      await api('/api/auth/send-otp', { m: 'POST', body: { purpose: 'register', pending_id: PEND } });
      step2('Verification code sent! Please check your email inbox and spam folder.', true);
      startResendTimer(60);
    } catch (x) {
      step1({ form: x.message, reloadCaptcha: true });
    } finally {
      goBtn.disabled = false;
      goBtn.textContent = 'Send OTP';
    }
  };

  function step2(m = '', isInitial = false) {
    showStep(2);
    const p = $('#otp-msg');
    $('#otp-email').textContent = S.em;
    if (isInitial) {
      $('#otp').value = '';
    }
    const isErr = m && !m.toLowerCase().includes('sent') && !m.toLowerCase().includes('success');
    p.className = isErr ? 'err' : 'note';
    p.textContent = m;
    setTimeout(() => {
      const inp = $('#otp');
      if (inp) inp.focus();
    }, 60);
  }

  $('#bk').onclick = () => {
    if (resendTimer) { clearInterval(resendTimer); resendTimer = null; }
    step1();
  };

  $('#rs').onclick = async () => {
    const rsBtn = $('#rs');
    rsBtn.disabled = true;
    rsBtn.textContent = 'Sending...';
    try {
      await api('/api/auth/send-otp', { m: 'POST', body: { purpose: 'register', pending_id: PEND } });
      step2('A new verification code was sent to your email.');
      startResendTimer(60);
    } catch (x) {
      step2(x.message);
      const match = (x.message || '').match(/(\d+)\s*second/i);
      if (match) {
        startResendTimer(parseInt(match[1], 10));
      } else {
        rsBtn.disabled = false;
        rsBtn.textContent = 'Resend code';
      }
    }
  };

  async function doVerify() {
    const raw = ($('#otp').value || '').replace(/\D/g, '').trim();
    if (raw.length !== 6) {
      step2('Please enter the complete 6-digit verification code.');
      $('#otp').focus();
      return;
    }
    const vfBtn = $('#vf');
    if (vfBtn.disabled) return;
    vfBtn.disabled = true;
    vfBtn.textContent = 'Verifying...';
    try {
      const res = await api('/api/auth/verify-otp', {
        m: 'POST',
        body: {
          pending_id: PEND,
          otp: raw,
          captcha_token: captchaData.token || null
        }
      });
      if (resendTimer) { clearInterval(resendTimer); resendTimer = null; }
      step3(res);
    } catch (x) {
      step2(x.message);
      $('#otp').select();
    } finally {
      vfBtn.disabled = false;
      vfBtn.textContent = 'Verify';
    }
  }

  $('#vf').onclick = doVerify;

  const otpInp = $('#otp');
  if (otpInp) {
    otpInp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        doVerify();
      }
    });
    otpInp.addEventListener('input', (e) => {
      const clean = e.target.value.replace(/\D/g, '').slice(0, 6);
      if (e.target.value !== clean) {
        e.target.value = clean;
      }
      if (clean.length === 6) {
        doVerify();
      }
    });
  }

  function step3(r) {
    const m = r.membership;
    showStep(3);
    $('#done-name').textContent = r.student.full_name;
    $('#done-club').textContent = m.club_name;
    $('#done-id').textContent = m.membership_code;
    $('#done-status').textContent = m.status;
  }
  $('#again').onclick = () => { S = {}; PEND = null; step1(); };

  /* ---------- admin (every call is checked by the server) ---------- */
  const memberRows = l => l.map(r => `<tr><td>${esc(r.membership_code)}</td><td>${esc(r.usn)}</td><td>${esc(r.full_name)}</td><td>${esc(r.branch)}</td><td>${esc(r.club_name)}</td><td><select data-ms="${r.membership_id}" aria-label="Status">${['active', 'pending', 'suspended'].map(s => `<option ${r.status === s ? 'selected' : ''}>${s}</option>`).join('')}</select></td><td><button class="chip danger" data-act="md" data-id="${r.membership_id}">Delete</button></td></tr>`).join('') || '<tr><td colspan="7">No members yet.</td></tr>';

  let PH_ITEMS = [];

  function clearFilePreview() {
    const pf = $('#pf'), prev = $('#pf-preview'), img = $('#pf-preview-img');
    if (pf) pf.value = '';
    if (prev) prev.hidden = true;
    if (img) img.src = '';
  }

  function initPhotoPreview() {
    const pf = $('#pf'), prev = $('#pf-preview'), img = $('#pf-preview-img'),
      nEl = $('#pf-preview-name'), sEl = $('#pf-preview-size'), clr = $('#pf-clear');
    if (!pf) return;
    pf.addEventListener('change', () => {
      const fl = pf.files[0];
      if (!fl) { clearFilePreview(); return; }
      if (!fl.type.startsWith('image/')) {
        alert('Selected file is not an image.');
        clearFilePreview();
        return;
      }
      if (fl.size > 5 * 1024 * 1024) {
        alert('Image size exceeds 5MB limit. Please choose a smaller image.');
        clearFilePreview();
        return;
      }
      if (nEl) nEl.textContent = fl.name;
      const sz = fl.size > 1024 * 1024 ? (fl.size / (1024 * 1024)).toFixed(2) + ' MB' : (fl.size / 1024).toFixed(1) + ' KB';
      if (sEl) sEl.textContent = sz;
      const rdr = new FileReader();
      rdr.onload = ev => { if (img) img.src = ev.target.result; if (prev) prev.hidden = false; };
      rdr.readAsDataURL(fl);
    });
    if (clr) clr.onclick = () => clearFilePreview();
  }

  async function renderAdmin(err = '', success = '') {
    if (cur !== 'admin') return;
    const login = $('#admin-login'), dash = $('#admin-dash');

    if (!admin) {
      try { admin = await api('/api/admin/me'); saveCsrf(admin.csrf_token); }
      catch (e) { admin = null; }
    }
    if (!admin) {
      dash.hidden = true; login.hidden = false;
      $('#au').value = ''; $('#ap').value = ''; $('#al-err').textContent = err;
      return;
    }

    let D, AN, LK, PH;
    try {
      [D, AN, LK, PH] = await Promise.all([
        api('/api/admin/dashboard'),
        api('/api/admin/announcements'),
        api('/api/admin/registration-links'),
        api('/api/gallery?page_size=36')
      ]);
    } catch (x) {
      admin = null;
      return renderAdmin('Session expired. Please sign in again.');
    }

    login.hidden = true; dash.hidden = false;
    PH_ITEMS = PH.items || [];

    if (success) {
      $$('input:not(#sq), textarea', dash).forEach(i => { i.value = ''; });
      ['nc', 'pc', 'lc'].forEach(id => { const el = $('#' + id); if (el) el.selectedIndex = 0; });
      clearFilePreview();
    }

    const amMsg = $('#am-msg');
    if (amMsg) { amMsg.hidden = !success; amMsg.textContent = success || ''; }
    const amErr = $('#am');
    if (amErr) { amErr.hidden = !err; amErr.textContent = err || ''; }

    $('#adm-user').textContent = `${admin.username} (${admin.role})`;
    $('#st-students').textContent = D.total_students;
    $('#st-clubs').innerHTML = D.members_per_club.map(c => `<div class="box"><b>${c.members}</b>${esc(c.name)}</div>`).join('');
    $('#st-news').textContent = D.published_announcements;
    $('#st-photos').textContent = D.photos;

    $('#an-list').innerHTML = AN.map(n => `<div class="row"><span>${esc(n.title)} <small>(${esc(n.club_name || 'All')})</small></span><span><button class="chip" data-act="nt" data-id="${n.id}" data-pub="${n.published}">${n.published ? 'Unpublish' : 'Publish'}</button> <button class="chip danger" data-act="nd" data-id="${n.id}">Delete</button></span></div>`).join('') || '<p style="color:var(--muted);margin:8px 0;">No announcements published.</p>';

    const phCount = $('#ph-count');
    if (phCount) phCount.textContent = PH.total ?? PH_ITEMS.length;

    $('#lk-list').innerHTML = LK.map(l => `<div class="row"><span><code>${esc(l.url)}</code> <small>(${esc(l.title)})</small></span><span><button class="chip" data-act="lt2" data-id="${l.id}" data-on="${l.active}">${l.active ? 'Disable' : 'Enable'}</button> <button class="chip danger" data-act="ld" data-id="${l.id}">Delete</button></span></div>`).join('') || '<p style="color:var(--muted);margin:8px 0;">No active registration links.</p>';
  }

  let adminPhFilter = 'all', adminPg = 0;

  async function renderAdminPhotos(err = '', success = '') {
    // admin-photos is now a standalone page (admin-photos.html).
    // This stub exists only as a safety guard if the hash '#admin-photos' is somehow typed.
    window.location.href = 'admin-photos.html';
  }

  const expBtn = $('#export');
  if (expBtn) expBtn.href = API_BASE + '/api/admin/students/export';

  async function doAdminLogin() {
    const u = $('#au').value.trim(), p = $('#ap').value;
    if (!u || !p) {
      $('#al-err').textContent = 'Please enter both username and password.';
      return;
    }
    const btn = $('#al');
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    $('#al-err').textContent = '';
    try {
      admin = await api('/api/admin/login', { m: 'POST', body: { username: u, password: p } });
      saveCsrf(admin.csrf_token);
      await renderAdmin();
    } catch (x) {
      renderAdmin(x.message || 'Login failed.');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Sign in';
    }
  }

  $('#al').onclick = doAdminLogin;
  ['au', 'ap'].forEach(id => {
    const el = $('#' + id);
    if (el) {
      el.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          e.preventDefault();
          doAdminLogin();
        }
      });
    }
  });

  const dash = $('#admin-dash');
  const run = async (fn, okMsg = '') => {
    try {
      await fn();
      if (cur === 'admin-photos') renderAdminPhotos('', okMsg);
      else renderAdmin('', okMsg);
    } catch (x) {
      if (x.status === 401) { admin = null; location.hash = '#admin'; }
      else {
        const errEl = cur === 'admin-photos' ? $('#am-photos-err') : $('#am');
        if (errEl) { errEl.hidden = false; errEl.textContent = x.message; }
      }
    }
  };
  const v = s => $(s).value.trim();

  let tm;
  const sq = $('#sq');
  if (sq) {
    sq.oninput = e => {
      clearTimeout(tm);
      tm = setTimeout(async () => {
        const tb = $('#tb');
        if (tb) {
          try { tb.innerHTML = memberRows((await api('/api/admin/students?page_size=100&q=' + encodeURIComponent(e.target.value))).items); } catch (x) { }
        }
      }, 300);
    };
  }

  dash.addEventListener('change', e => {
    const s = e.target.closest('[data-ms]');
    if (s) run(() => api('/api/admin/memberships/' + s.dataset.ms, { m: 'PATCH', body: { status: s.value } }), 'Membership status updated.');
  });

  document.addEventListener('click', e => {
    const b = e.target.closest('[data-act]'); if (!b) return;
    const id = b.dataset.id;
    const act = b.dataset.act;

    if (act === 'lo') {
      run(async () => { await api('/api/admin/logout', { m: 'POST' }); admin = null; saveCsrf(''); });
      return;
    }
    if (act === 'pv') {
      const u = PH_ITEMS.find(x => x.id == id);
      if (u) {
        openDialog(u.title, { img: assetUrl(u.image_url), sub: `${u.club_name} Club${u.event_name ? ' · ' + u.event_name : ''}` });
      }
      return;
    }
    if (act === 'np') {
      const t = v('#nt'), m = v('#nm2');
      if (!t) { $('#am').hidden = false; $('#am').textContent = 'Please enter an announcement title.'; return; }
      run(() => api('/api/admin/announcements', { m: 'POST', body: { title: t, message: m, club_slug: $('#nc').value || null, published: true } }), 'Announcement published.');
      return;
    }
    if (act === 'nt') {
      run(() => api('/api/admin/announcements/' + id, { m: 'PATCH', body: { published: b.dataset.pub !== 'true' } }), 'Announcement updated.');
      return;
    }
    if (act === 'nd') {
      if (confirm('Delete this announcement?')) run(() => api('/api/admin/announcements/' + id, { m: 'DELETE' }), 'Announcement deleted.');
      return;
    }
    if (act === 'pu') {
      const fl = $('#pf').files[0];
      if (!fl) { $('#am').hidden = false; $('#am').textContent = 'Please choose an image first.'; return; }
      const title = v('#pt');
      if (!title) { $('#am').hidden = false; $('#am').textContent = 'Please enter a title for the photo.'; $('#pt').focus(); return; }
      const btn = $('#btn-upload') || b;
      btn.disabled = true;
      btn.textContent = 'Uploading photo...';
      $('#am').hidden = true;

      const fd = new FormData();
      fd.append('club_slug', $('#pc').value);
      fd.append('title', title);
      fd.append('event_name', v('#pe'));
      fd.append('file', fl);

      api('/api/admin/photos', { m: 'POST', form: fd })
        .then(async uploaded => {
          try {
            GAL = await api(`/api/gallery?page=1&page_size=8${f === 'all' ? '' : '&club=' + f}`);
            if (cur === 'gallery') renderGallery();
          } catch (_) { }
          await renderAdmin('', `Photo "${uploaded.title}" uploaded successfully to ${uploaded.club_name} Club!`);
        })
        .catch(x => {
          if (x.status === 401) { admin = null; location.hash = '#admin'; }
          else { $('#am').hidden = false; $('#am').textContent = x.message || 'Upload failed.'; }
        })
        .finally(() => {
          btn.disabled = false;
          btn.textContent = 'Upload to Gallery';
        });
      return;
    }
    if (act === 'pd') {
      if (confirm('Are you sure you want to permanently delete this photo from the gallery?')) {
        api('/api/admin/photos/' + id, { m: 'DELETE' })
          .then(async () => {
            try {
              GAL = await api(`/api/gallery?page=1&page_size=8${f === 'all' ? '' : '&club=' + f}`);
              if (cur === 'gallery') renderGallery();
            } catch (_) { }
            if (cur === 'admin-photos') {
              await renderAdminPhotos('', 'Photo deleted successfully.');
            } else {
              await renderAdmin('', 'Photo deleted successfully.');
            }
          })
          .catch(x => {
            if (x.status === 401) { admin = null; location.hash = '#admin'; }
            else {
              const errEl = cur === 'admin-photos' ? $('#am-photos-err') : $('#am');
              if (errEl) { errEl.hidden = false; errEl.textContent = x.message; }
            }
          });
      }
      return;
    }
    if (act === 'lk') {
      const d = $('#le').value;
      run(() => api('/api/admin/registration-links', { m: 'POST', body: { club_slug: $('#lc').value, title: v('#lt') || 'Registration link', ends_at: d ? new Date(d + 'T23:59:59').toISOString() : null } }), 'Registration link generated.');
      return;
    }
    if (act === 'lt2') {
      run(() => api('/api/admin/registration-links/' + id, { m: 'PATCH', body: { active: b.dataset.on !== 'true' } }), 'Link status changed.');
      return;
    }
    if (act === 'ld') {
      if (confirm('Delete this registration link?')) run(() => api('/api/admin/registration-links/' + id, { m: 'DELETE' }), 'Registration link deleted.');
      return;
    }
    if (act === 'md') {
      if (confirm('Delete this club member?')) run(() => api('/api/admin/memberships/' + id, { m: 'DELETE' }), 'Member removed.');
      return;
    }
  });

  initPhotoPreview();
  route();
})();
