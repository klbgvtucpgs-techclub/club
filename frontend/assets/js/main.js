/*  VTU Clubs: behaviour only.
    All page markup now lives in index.html. This file:
      - shows/hides pages by URL hash (router)
      - fills the few areas that come from the API (news, gallery photos, admin lists)
      - runs registration, admin, dialogs and the 3D effects                                   */
(() => {
'use strict';

/* ---------- config & helpers ---------- */
const API_BASE = window.API_BASE ?? (location.port === '8000' ? '' : 'http://127.0.0.1:8000');
const CLUBS = ['tech', 'sports', 'culture', 'multimedia'];
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
  const nav = $('#nav');
  if (t.id === 'menu') { t.setAttribute('aria-expanded', String(nav.classList.toggle('open'))); return; }
  nav.classList.remove('open'); $('#menu').setAttribute('aria-expanded', 'false');

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
  $('#go').disabled = false;
}
$('#go').onclick = async () => {
  S = { ...S, usn: $('#usn').value, nm: $('#nm').value, em: $('#em').value, ph: $('#ph').value, br: $('#br').value, yr: $('#yr').value, club: $('#club').value };
  $('#go').disabled = true;
  try {
    const p = await api('/api/auth/register', { m: 'POST', body: { usn: S.usn, full_name: S.nm, email: S.em, phone: S.ph, branch: S.br, joining_year: +S.yr, club_slug: S.club, link_token: LINK || null } });
    PEND = p.pending_id;
    await api('/api/auth/send-otp', { m: 'POST', body: { purpose: 'register', pending_id: PEND } });
    step2('');
  } catch (x) { step1({ form: x.message }); }
};

function step2(m = '') {
  showStep(2);
  const isErr = m && m !== 'A new code was sent.', p = $('#otp-msg');
  $('#otp-email').textContent = S.em; $('#otp').value = '';
  p.className = isErr ? 'err' : 'note'; p.textContent = m;
}
$('#bk').onclick = () => step1();
$('#rs').onclick = async () => {
  try { await api('/api/auth/send-otp', { m: 'POST', body: { purpose: 'register', pending_id: PEND } }); step2('A new code was sent.'); }
  catch (x) { step2(x.message); }
};
$('#vf').onclick = async () => {
  try { step3(await api('/api/auth/verify-otp', { m: 'POST', body: { pending_id: PEND, otp: $('#otp').value.trim() } })); }
  catch (x) { step2(x.message); }
};

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

async function renderAdmin(m = '') {
  if (cur !== 'admin') return;
  const login = $('#admin-login'), dash = $('#admin-dash');

  if (!admin) { try { admin = await api('/api/admin/me'); saveCsrf(admin.csrf_token); } catch (e) { admin = null; } }
  if (!admin) {
    dash.hidden = true; login.hidden = false;
    $('#au').value = ''; $('#ap').value = ''; $('#al-err').textContent = m;
    return;
  }

  let D, AN, LK, ST, PH;
  try { [D, AN, LK, ST, PH] = await Promise.all([api('/api/admin/dashboard'), api('/api/admin/announcements'), api('/api/admin/registration-links'), api('/api/admin/students?page_size=100'), api('/api/gallery?page_size=24')]); }
  catch (x) { admin = null; return renderAdmin('Session expired. Please sign in again.'); }

  login.hidden = true; dash.hidden = false;
  // clear the forms (same as a fresh render)
  $$('input, textarea', dash).forEach(i => { i.value = ''; });
  ['nc', 'pc', 'lc'].forEach(id => { $('#' + id).selectedIndex = 0; });
  $('#am').textContent = '';

  $('#adm-user').textContent = `${admin.username} (${admin.role})`;
  $('#st-students').textContent = D.total_students;
  $('#st-clubs').innerHTML = D.members_per_club.map(c => `<div class="box"><b>${c.members}</b>${esc(c.name)}</div>`).join('');
  $('#st-news').textContent = D.published_announcements;
  $('#st-photos').textContent = D.photos;

  $('#an-list').innerHTML = AN.map(n => `<div class="row"><span>${esc(n.title)} <small>(${esc(n.club_name || 'All')})</small></span><span><button class="chip" data-act="nt" data-id="${n.id}" data-pub="${n.published}">${n.published ? 'Unpublish' : 'Publish'}</button> <button class="chip danger" data-act="nd" data-id="${n.id}">Delete</button></span></div>`).join('');
  $('#ph-list').innerHTML = PH.items.map(u => `<div class="row"><span>${esc(u.title)} <small>(${esc(u.club_name)})</small></span><button class="chip danger" data-act="pd" data-id="${u.id}">Delete</button></div>`).join('');
  $('#lk-list').innerHTML = LK.map(l => `<div class="row"><span><code>${esc(l.url)}</code> <small>(${esc(l.title)})</small></span><span><button class="chip" data-act="lt2" data-id="${l.id}" data-on="${l.active}">${l.active ? 'Disable' : 'Enable'}</button> <button class="chip danger" data-act="ld" data-id="${l.id}">Delete</button></span></div>`).join('');
  $('#mem-count').textContent = ST.total;
  $('#tb').innerHTML = memberRows(ST.items);
}

$('#export').href = API_BASE + '/api/admin/students/export';

$('#al').onclick = async () => {
  try { admin = await api('/api/admin/login', { m: 'POST', body: { username: $('#au').value, password: $('#ap').value } }); saveCsrf(admin.csrf_token); renderAdmin(); }
  catch (x) { renderAdmin(x.message); }
};

const dash = $('#admin-dash');
const run = async fn => {
  try { await fn(); renderAdmin(); }
  catch (x) { if (x.status === 401) { admin = null; renderAdmin('Session expired.'); } else $('#am').textContent = x.message; }
};
const v = s => $(s).value.trim();

let tm;
$('#sq').oninput = e => {
  clearTimeout(tm);
  tm = setTimeout(async () => { try { $('#tb').innerHTML = memberRows((await api('/api/admin/students?page_size=100&q=' + encodeURIComponent(e.target.value))).items); } catch (x) { } }, 300);
};
dash.addEventListener('change', e => {
  const s = e.target.closest('[data-ms]');
  if (s) run(() => api('/api/admin/memberships/' + s.dataset.ms, { m: 'PATCH', body: { status: s.value } }));
});
dash.addEventListener('click', e => {
  const b = e.target.closest('[data-act]'); if (!b) return;
  const id = b.dataset.id;
  ({
    lo: () => run(async () => { await api('/api/admin/logout', { m: 'POST' }); admin = null; saveCsrf(''); }),
    np: () => run(() => api('/api/admin/announcements', { m: 'POST', body: { title: v('#nt'), message: v('#nm2'), club_slug: $('#nc').value || null, published: true } })),
    nt: () => run(() => api('/api/admin/announcements/' + id, { m: 'PATCH', body: { published: b.dataset.pub !== 'true' } })),
    nd: () => run(() => { if (confirm('Delete this announcement?')) return api('/api/admin/announcements/' + id, { m: 'DELETE' }); }),
    pu: () => run(() => {
      const fl = $('#pf').files[0]; if (!fl) throw new Error('Choose an image first.');
      const fd = new FormData(); fd.append('club_slug', $('#pc').value); fd.append('title', v('#pt')); fd.append('event_name', v('#pe')); fd.append('file', fl);
      return api('/api/admin/photos', { m: 'POST', form: fd });
    }),
    pd: () => run(() => { if (confirm('Delete this photo?')) return api('/api/admin/photos/' + id, { m: 'DELETE' }); }),
    lk: () => run(() => { const d = $('#le').value; return api('/api/admin/registration-links', { m: 'POST', body: { club_slug: $('#lc').value, title: v('#lt') || 'Registration link', ends_at: d ? new Date(d + 'T23:59:59').toISOString() : null } }); }),
    lt2: () => run(() => api('/api/admin/registration-links/' + id, { m: 'PATCH', body: { active: b.dataset.on !== 'true' } })),
    ld: () => run(() => { if (confirm('Delete this registration link?')) return api('/api/admin/registration-links/' + id, { m: 'DELETE' }); }),
    md: () => run(() => { if (confirm('Delete this club member?')) return api('/api/admin/memberships/' + id, { m: 'DELETE' }); })
  })[b.dataset.act]();
});

route();
})();
