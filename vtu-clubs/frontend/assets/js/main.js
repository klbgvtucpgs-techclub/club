const IMG = { tech: 'assets/images/tech.webp', sports: 'assets/images/sports.webp', culture: 'assets/images/culture.webp', multimedia: 'assets/images/multimedia.webp' };
const CLUBS = [
  { k: 'tech', n: 'Tech', p: 'TECH', d: 'Hackathons, coding contests, robotics and AI/ML workshops for builders.', a: ['Weekly coding sessions', 'Annual hackathon', 'Project showcases', 'Industry talks'], h: 'Tech Club Head', pos: ['0% 15%', '12% 5%', '4% 30%', '16% 18%'] },
  { k: 'sports', n: 'Sports', p: 'SPORTS', d: 'Inter-college tournaments, fitness drives and team training.', a: ['Cricket, football, kabaddi', 'Annual athletics meet', 'Fitness camps', 'Inter-college leagues'], h: 'Sports Club Head', pos: ['0% 95%', '10% 90%', '18% 100%', '6% 80%'] },
  { k: 'culture', n: 'Culture', p: 'CULT', d: 'Music, dance, drama and celebrations of Indian heritage.', a: ['Annual cultural fest', 'Dance and music nights', 'Drama workshops', 'Heritage days'], h: 'Culture Club Head', pos: ['100% 10%', '90% 30%', '96% 4%', '84% 22%'] },
  { k: 'multimedia', n: 'Multi Media', p: 'MM', d: 'Photography, film-making, design and event coverage.', a: ['Photo walks', 'Short-film contests', 'Design workshops', 'Live event coverage'], h: 'Multi Media Head', pos: ['100% 95%', '90% 85%', '100% 70%', '82% 100%'] }];
const $ = s => document.querySelector(s), esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const API_BASE = window.API_BASE ?? (typeof location !== 'undefined' && location.port === '8000' ? '' : 'http://127.0.0.1:8000');
const assetUrl = u => (!u || u.startsWith('http://') || u.startsWith('https://')) ? u : API_BASE + u;
let csrf = ''; try { csrf = sessionStorage.getItem('csrf') || '' } catch (e) { }
async function api(p, o = {}) {
  const h = {}; if (o.body) h['Content-Type'] = 'application/json'; if (o.m && o.m !== 'GET' && csrf) h['X-CSRF-Token'] = csrf;
  const url = p.startsWith('http') ? p : API_BASE + p;
  const r = await fetch(url, { method: o.m || 'GET', headers: h, credentials: 'include', body: o.form || (o.body ? JSON.stringify(o.body) : undefined) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { const x = d.detail; throw Object.assign(new Error(Array.isArray(x) ? x.map(v => String(v.msg).replace(/^Value error, /, '')).join(', ') : x || 'Request failed'), { status: r.status }) } return d
}
let admin = null, NEWS = [], GAL = { items: [], total: 0 }, f = 'all', pg = 0, S = {}, PEND = null, LINK = null, cur = '', seq = 0;
const cl = k => CLUBS.find(c => c.k === k);
const tiles = CLUBS.flatMap((c, ci) => c.pos.map((p, i) => ({ k: c.k, p, im: (i + ci) % 2 ? '--p2' : '--p1', t: `${c.n} · ${['Opening day', 'Workshop', 'Finals', 'Showcase'][i]}` })));

/* ---------- pages ---------- */
const V = {
  home: () => `<div class="hero"><div class="bg" id="bg"></div><canvas id="gl" aria-hidden="true"></canvas><div class="wrap">
 <h1>Join. Create. <span>Shine</span> at VTU.</h1><p class="l">Four clubs, one campus. Spin the ring and pick yours.</p>
 <div class="stage"><div class="ring">${CLUBS.map((c, i) => `<a class="face" style="--i:${i}" href="#${c.k}" aria-label="${c.n} Club"><img src="${IMG[c.k]}" alt="${c.n} Club badge"></a>`).join('')}</div></div>
 <a class="btn" href="#register">Register now</a> <a class="btn ghost" href="#gallery">Gallery</a></div>
 <div class="ticker" tabindex="0" role="region" aria-label="Announcements"><b>NEWS</b><div class="track">${NEWS.map(n => `<span>${esc(n.title)}</span>`).join('') || '<span>No announcements yet. Check back soon.</span>'}</div></div></div>
 <section class="s"><div class="wrap"><h2>Our Clubs</h2><p class="sub">Each club has its own page with activities, events and registration.</p>
 <div class="g4">${CLUBS.map(c => `<a class="card tilt" href="#${c.k}"><img src="${IMG[c.k]}" alt="${c.n} Club badge"><h3>${c.n} Club</h3><p>${c.d}</p></a>`).join('')}</div></div></section>`,
  club: k => {
    const c = cl(k), ns = NEWS.filter(n => !n.club_slug || n.club_slug === k); return `<div class="club-hero"><div class="bg" style="background:linear-gradient(rgba(11,7,16,.6),rgba(11,7,16,.9)),var(--p${k === 'tech' || k === 'culture' ? 2 : 1}) ${c.pos[0]}/260% auto"></div><div class="wrap"><img src="${IMG[k]}" alt="${c.n} Club badge"><div><h1>${c.n} Club</h1><p style="max-width:50ch">${c.d}</p><a class="btn" href="#register" data-club="${k}">Join this club</a> <a class="btn ghost" href="#gallery" data-gal="${k}">Photos</a></div></div></div>
 <section class="s"><div class="wrap two"><div class="box"><h3>Activities and events</h3><ul>${c.a.map(a => `<li>${a}</li>`).join('')}</ul></div><div class="box"><h3>Club head</h3><p>${c.h}<br>${k}@vtu.example</p><h3>Announcements</h3><ul>${ns.map(n => `<li>${esc(n.title)}</li>`).join('') || '<li>No announcements yet.</li>'}</ul></div></div></section>`
  },
  gallery: () => {
    const real = GAL.items, n = Math.max(1, Math.ceil(GAL.total / 8));
    return `<div class="wrap top"><h2>Gallery</h2><p class="sub">Moments from all four clubs. Open any photo for a large preview.</p>
 <div class="filters" role="group" aria-label="Filter by club">${[{ k: 'all', n: 'All' }, ...CLUBS].map(c => `<button class="chip" data-f="${c.k}" aria-pressed="${c.k === f}">${c.n}</button>`).join('')}</div>
 <div class="grid">${real.length ? real.map(u => `<button class="ph tilt" data-u="${u.id}" style="background-image:url('${esc(assetUrl(u.image_url))}');background-size:cover" aria-label="Open ${esc(u.title)}"><span>${esc(u.title)}</span></button>`).join('') : tiles.filter(t => f === 'all' || t.k === f).slice(0, 8).map(t => `<button class="ph tilt" data-t="${tiles.indexOf(t)}" style="background-image:var(${t.im});background-position:${t.p}" aria-label="Open ${t.t}"><span>${t.t}</span></button>`).join('')}</div>
 ${real.length ? `<div class="pager"><button class="chip" data-pg="-1" ${pg ? '' : 'disabled'}>Previous</button><span aria-live="polite">Page ${pg + 1} of ${n}</span><button class="chip" data-pg="1" ${pg >= n - 1 ? 'disabled' : ''}>Next</button></div>` : '<p class="sub" style="margin-top:18px">Sample artwork is shown until admins upload real photos.</p>'}</div>`
  },
  announcements: () => `<div class="wrap top"><h2>Announcements</h2><p class="sub">Published by the club admins.</p>${NEWS.map(n => `<div class="box" style="margin-bottom:12px"><b style="color:var(--gold)">${esc(n.club_name || 'All clubs')}</b><h3>${esc(n.title)}</h3><p>${esc(n.message)}</p></div>`).join('') || '<p>Nothing published yet.</p>'}</div>`,
  register: () => `<div class="wrap top"><h2>Student Registration</h2><p class="sub">Details, then email OTP, then your club ID.</p><div class="form" id="reg"></div></div>`,
  admin: () => `<div class="wrap top" id="adm"></div>`
};

/* ---------- router ---------- */
async function route() {
  const my = ++seq, [r, qs] = location.hash.slice(1).split('?'), name = r || 'home'; LINK = new URLSearchParams(qs || '').get('link'); if (name !== 'gallery') pg = 0;
  try { if (name === 'home' || cl(name) || name === 'announcements') NEWS = await api('/api/announcements'); if (name === 'gallery') GAL = await api(`/api/gallery?page=${pg + 1}&page_size=8${f === 'all' ? '' : '&club=' + f}`) } catch (e) { }
  if (my !== seq) return; cur = name;
  $('#app').innerHTML = `<div class="page on">${cl(name) ? V.club(name) : (V[name] || V.home)()}</div>`;
  document.querySelectorAll('nav a').forEach(a => a.classList.toggle('on', a.getAttribute('href') === '#' + name));
  if (name === 'register') step1(); if (name === 'admin') renderAdmin(); if (name === 'home' || !V[name] && !cl(name)) initHome(); scrollTo(0, 0)
}
addEventListener('hashchange', route);
/* ---------- 3D: parallax + three.js embers + tilt ---------- */
const RM = matchMedia('(prefers-reduced-motion:reduce)').matches; let mx = 0, my = 0;
addEventListener('pointermove', e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; const b = $('#bg'); if (b && !RM) b.style.transform = `translate3d(${-mx * 30}px,${-my * 20}px,0) scale(1.06)` });
document.addEventListener('pointermove', e => { const t = e.target.closest && e.target.closest('.tilt'); if (!t || RM) return; const r = t.getBoundingClientRect(); t.style.transform = `perspective(700px) rotateY(${((e.clientX - r.left) / r.width - .5) * 18}deg) rotateX(${-((e.clientY - r.top) / r.height - .5) * 18}deg) scale(1.04)` });
document.addEventListener('pointerout', e => { const t = e.target.closest && e.target.closest('.tilt'); if (t) t.style.transform = '' });
let raf; function initHome() {
  cancelAnimationFrame(raf); const cv = $('#gl'); if (!cv || !window.THREE || RM) return;
  const r = new THREE.WebGLRenderer({ canvas: cv, alpha: true, antialias: true }), sc = new THREE.Scene(), cam = new THREE.PerspectiveCamera(60, 1, .1, 100); cam.position.z = 14;
  const N = 700, g = new THREE.BufferGeometry(), p = new Float32Array(N * 3); for (let i = 0; i < N * 3; i++)p[i] = (Math.random() - .5) * (i % 3 == 1 ? 26 : 36); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
  const pts = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffa83a, size: .09, transparent: true, opacity: .85 })); sc.add(pts);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(5, .04, 8, 120), new THREE.MeshBasicMaterial({ color: 0xf5b942, transparent: true, opacity: .5 })); sc.add(ring);
  const ring2 = ring.clone(); ring2.scale.setScalar(1.35); sc.add(ring2);
  function size() { const w = cv.clientWidth, h = cv.clientHeight; r.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix() } size(); addEventListener('resize', size);
  (function loop() {
    if (cur !== '' && cur !== 'home' && V[cur] || cl(cur)) return; raf = requestAnimationFrame(loop); const a = p; for (let i = 1; i < a.length; i += 3) { a[i] += .012; if (a[i] > 13) a[i] = -13 } g.attributes.position.needsUpdate = true;
    pts.rotation.y += .0006; ring.rotation.x = 1.2 + Math.sin(Date.now() / 3000) * .2; ring.rotation.y += .004; ring2.rotation.x = -1.1; ring2.rotation.z += .003; cam.position.x += (mx * 5 - cam.position.x) * .05; cam.position.y += (-my * 3 - cam.position.y) * .05; cam.lookAt(0, 0, 0); r.render(sc, cam)
  })()
}

/* ---------- clicks / dialogs ---------- */
const dlg = $('#dlg');
document.addEventListener('click', e => {
  const t = e.target, q = s => t.closest(s); let b;
  if (t.id === 'menu') { t.setAttribute('aria-expanded', $('#nav').classList.toggle('open')); return } $('#nav').classList.remove('open');
  if (b = q('[data-club]')) S.club = b.dataset.club;
  if (b = q('[data-gal]')) { f = b.dataset.gal; pg = 0 }
  if (b = q('[data-f]')) { f = b.dataset.f; pg = 0; route() }
  if (b = q('[data-pg]')) { pg += +b.dataset.pg; route() }
  if (b = q('[data-t]')) { const x = tiles[b.dataset.t]; dlg.innerHTML = `<button class="btn ghost" onclick="dlg.close()">Close</button><h3>${x.t}</h3><div class="big" role="img" aria-label="${x.t}" style="background-image:var(${x.im});background-position:${x.p}"></div>`; dlg.showModal() }
  if (b = q('[data-u]')) { const u = GAL.items.find(x => x.id == b.dataset.u); if (u) { dlg.innerHTML = `<button class="btn ghost" onclick="dlg.close()">Close</button><h3>${esc(u.title)}</h3><img src="${esc(assetUrl(u.image_url))}" alt="${esc(u.title)}" style="max-width:100%;border-radius:12px"><p class="sub">${esc(u.club_name)} Club${u.event_name ? ' · ' + esc(u.event_name) : ''}</p>`; dlg.showModal() } }
});

/* ---------- registration (all checks happen on the server) ---------- */
const R = () => $('#reg');
async function step1(e = {}) {
  const y = new Date().getFullYear();
  if (LINK && !S.linkOk) { try { const l = await api('/api/registration-links/' + encodeURIComponent(LINK)); S.club = l.club_slug; S.linkTitle = l.title; S.linkOk = true } catch (x) { S.linkErr = x.message } }
  if (!R()) return;
  R().innerHTML = `<div class="steps"><b>1 Details</b> &rarr; 2 Verify &rarr; 3 Club ID</div>${S.linkOk ? `<p class="note">Registration link: ${esc(S.linkTitle)}</p>` : ''}${S.linkErr ? `<p class="err">${esc(S.linkErr)}</p>` : ''}
 <label for="usn">USN</label><input id="usn" value="${esc(S.usn || '')}" placeholder="1VT22CS001" autocomplete="off">
 <label for="nm">Full name</label><input id="nm" value="${esc(S.nm || '')}">
 <label for="em">College email</label><input id="em" type="email" value="${esc(S.em || '')}">
 <label for="ph">Phone</label><input id="ph" inputmode="numeric" value="${esc(S.ph || '')}">
 <label for="br">Branch</label><select id="br">${['CSE', 'ECE', 'AI&DS', 'ME'].map(b => `<option ${S.br === b ? 'selected' : ''}>${b}</option>`).join('')}</select>
 <label for="yr">Year of joining college</label><input id="yr" type="number" min="2000" max="${y}" value="${S.yr || y}">
 <label for="club">Club</label><select id="club" ${S.linkOk ? 'disabled' : ''}>${CLUBS.map(c => `<option value="${c.k}" ${S.club === c.k ? 'selected' : ''}>${c.n}</option>`).join('')}</select>
 <p class="err" role="alert">${esc(e.form || '')}</p><p><button class="btn" id="go">Send OTP</button></p>`;
  $('#go').onclick = async () => {
    S = { ...S, usn: $('#usn').value, nm: $('#nm').value, em: $('#em').value, ph: $('#ph').value, br: $('#br').value, yr: $('#yr').value, club: $('#club').value };
    $('#go').disabled = true;
    try {
      const p = await api('/api/auth/register', { m: 'POST', body: { usn: S.usn, full_name: S.nm, email: S.em, phone: S.ph, branch: S.br, joining_year: +S.yr, club_slug: S.club, link_token: LINK || null } });
      PEND = p.pending_id; await api('/api/auth/send-otp', { m: 'POST', body: { purpose: 'register', pending_id: PEND } }); step2('')
    } catch (x) { step1({ form: x.message }) }
  }
}
function step2(m = '') {
  const isErr = m && m !== 'A new code was sent.'; R().innerHTML = `<div class="steps">1 Details &rarr; <b>2 Verify</b> &rarr; 3 Club ID</div><p>We emailed a 6-digit code to <b>${esc(S.em)}</b>. It expires in 5 minutes.</p>
 <label for="otp">Enter OTP</label><input id="otp" inputmode="numeric" maxlength="6" autocomplete="one-time-code"><p class="${isErr ? 'err' : 'note'}" role="alert">${esc(m)}</p>
 <p><button class="btn" id="vf">Verify</button> <button class="btn ghost" id="rs">Resend code</button> <button class="btn ghost" id="bk">Back</button></p>`;
  $('#bk').onclick = () => step1();
  $('#rs').onclick = async () => { try { await api('/api/auth/send-otp', { m: 'POST', body: { purpose: 'register', pending_id: PEND } }); step2('A new code was sent.') } catch (x) { step2(x.message) } };
  $('#vf').onclick = async () => { try { step3(await api('/api/auth/verify-otp', { m: 'POST', body: { pending_id: PEND, otp: $('#otp').value.trim() } })) } catch (x) { step2(x.message) } }
}
function step3(r) {
  const m = r.membership; R().innerHTML = `<div class="steps">1 Details &rarr; 2 Verify &rarr; <b>3 Club ID</b></div><h3>Welcome, ${esc(r.student.full_name)}!</h3><p>Your ${esc(m.club_name)} Club membership ID:</p><div class="id">${esc(m.membership_code)}</div><p>Status: ${esc(m.status)}. A confirmation email has been sent.</p><button class="btn ghost" id="again">New registration</button>`;
  $('#again').onclick = () => { S = {}; PEND = null; step1() }
}

/* ---------- admin (every call is checked by the server) ---------- */
async function renderAdmin(m = '') {
  const A = $('#adm'); if (!A) return;
  if (!admin) { try { admin = await api('/api/admin/me'); csrf = admin.csrf_token; sessionStorage.setItem('csrf', csrf) } catch (e) { admin = null } }
  if (!admin) {
    A.innerHTML = `<h2>Admin Login</h2><p class="sub">Restricted area.</p><div class="form"><label for="au">Username</label><input id="au" autocomplete="username"><label for="ap">Password</label><input id="ap" type="password" autocomplete="current-password"><p class="err" role="alert">${esc(m)}</p><button class="btn" id="al">Sign in</button></div>`;
    $('#al').onclick = async () => { try { admin = await api('/api/admin/login', { m: 'POST', body: { username: $('#au').value, password: $('#ap').value } }); csrf = admin.csrf_token; sessionStorage.setItem('csrf', csrf); renderAdmin() } catch (x) { renderAdmin(x.message) } }; return
  }
  let D, AN, LK, ST, PH;
  try { [D, AN, LK, ST, PH] = await Promise.all([api('/api/admin/dashboard'), api('/api/admin/announcements'), api('/api/admin/registration-links'), api('/api/admin/students?page_size=100'), api('/api/gallery?page_size=24')]) } catch (x) { admin = null; return renderAdmin('Session expired. Please sign in again.') }
  const opts = CLUBS.map(c => `<option value="${c.k}">${c.n}</option>`).join(''), rows = l => l.map(r => `<tr><td>${esc(r.membership_code)}</td><td>${esc(r.usn)}</td><td>${esc(r.full_name)}</td><td>${esc(r.branch)}</td><td>${esc(r.club_name)}</td><td><select data-ms="${r.membership_id}" aria-label="Status">${['active', 'pending', 'suspended'].map(s => `<option ${r.status === s ? 'selected' : ''}>${s}</option>`).join('')}</select></td><td><button class="chip danger" data-act="md" data-id="${r.membership_id}">Delete</button></td></tr>`).join('') || '<tr><td colspan="7">No members yet.</td></tr>';
  A.innerHTML = `<div class="row"><h2>Admin Dashboard</h2><span>${esc(admin.username)} (${esc(admin.role)}) <button class="btn ghost" data-act="lo">Log out</button></span></div><p class="err" id="am" role="alert"></p>
 <div class="stats"><div class="box"><b>${D.total_students}</b>Students</div>${D.members_per_club.map(c => `<div class="box"><b>${c.members}</b>${esc(c.name)}</div>`).join('')}<div class="box"><b>${D.published_announcements}</b>Published news</div><div class="box"><b>${D.photos}</b>Photos</div></div>
 <div class="two"><div class="box"><h3>Announcements</h3><label for="nt">Title</label><input id="nt"><label for="nm2">Message</label><textarea id="nm2" rows="3"></textarea><label for="nc">Target</label><select id="nc"><option value="">All clubs</option>${opts}</select><p><button class="btn" data-act="np">Publish</button></p>
  ${AN.map(n => `<div class="row"><span>${esc(n.title)} <small>(${esc(n.club_name || 'All')})</small></span><span><button class="chip" data-act="nt" data-id="${n.id}" data-pub="${n.published}">${n.published ? 'Unpublish' : 'Publish'}</button> <button class="chip danger" data-act="nd" data-id="${n.id}">Delete</button></span></div>`).join('')}</div>
 <div class="box"><h3>Upload gallery photo</h3><label for="pf">Image</label><input id="pf" type="file" accept="image/*"><label for="pt">Title</label><input id="pt"><label for="pe">Event name</label><input id="pe"><label for="pc">Club</label><select id="pc">${opts}</select><p><button class="btn" data-act="pu">Upload</button></p>
  ${PH.items.map(u => `<div class="row"><span>${esc(u.title)} <small>(${esc(u.club_name)})</small></span><button class="chip danger" data-act="pd" data-id="${u.id}">Delete</button></div>`).join('')}</div></div>
 <div class="box" style="margin-top:20px"><h3>Registration links</h3><div class="row"><select id="lc" style="max-width:180px">${opts}</select><input id="lt" placeholder="Link title" style="max-width:220px"><input id="le" type="date" style="max-width:170px" aria-label="Expiry date"><button class="btn" data-act="lk">Generate link</button></div>
  ${LK.map(l => `<div class="row"><span><code>${esc(l.url)}</code> <small>(${esc(l.title)})</small></span><span><button class="chip" data-act="lt2" data-id="${l.id}" data-on="${l.active}">${l.active ? 'Disable' : 'Enable'}</button> <button class="chip danger" data-act="ld" data-id="${l.id}">Delete</button></span></div>`).join('')}</div>
 <div class="box" style="margin-top:20px"><div class="row"><h3>Members (${ST.total})</h3><input id="sq" placeholder="Search USN, name, branch or club ID" style="max-width:320px" aria-label="Search members"><a class="btn ghost" href="${API_BASE}/api/admin/students/export">Export CSV</a></div><div class="tw"><table><thead><tr><th>Club ID</th><th>USN</th><th>Name</th><th>Branch</th><th>Club</th><th>Status</th><th>Action</th></tr></thead><tbody id="tb">${rows(ST.items)}</tbody></table></div></div>`;
  const run = async fn => { try { await fn(); renderAdmin() } catch (x) { if (x.status === 401) { admin = null; renderAdmin('Session expired.') } else $('#am').textContent = x.message } }, v = s => $(s).value.trim();
  let tm; $('#sq').oninput = e => { clearTimeout(tm); tm = setTimeout(async () => { try { $('#tb').innerHTML = rows((await api('/api/admin/students?page_size=100&q=' + encodeURIComponent(e.target.value))).items) } catch (x) { } }, 300) };
  A.onchange = e => { const s = e.target.closest('[data-ms]'); if (s) run(() => api('/api/admin/memberships/' + s.dataset.ms, { m: 'PATCH', body: { status: s.value } })) };
  A.onclick = e => {
    const b = e.target.closest('[data-act]'); if (!b) return; const id = b.dataset.id;
    ({
      lo: () => run(async () => { await api('/api/admin/logout', { m: 'POST' }); admin = null; csrf = ''; sessionStorage.removeItem('csrf') }),
      np: () => run(() => api('/api/admin/announcements', { m: 'POST', body: { title: v('#nt'), message: v('#nm2'), club_slug: $('#nc').value || null, published: true } })),
      nt: () => run(() => api('/api/admin/announcements/' + id, { m: 'PATCH', body: { published: b.dataset.pub !== 'true' } })),
      nd: () => run(() => { if (confirm('Delete this announcement?')) return api('/api/admin/announcements/' + id, { m: 'DELETE' }) }),
      pu: () => run(() => { const fl = $('#pf').files[0]; if (!fl) throw new Error('Choose an image first.'); const fd = new FormData(); fd.append('club_slug', $('#pc').value); fd.append('title', v('#pt')); fd.append('event_name', v('#pe')); fd.append('file', fl); return api('/api/admin/photos', { m: 'POST', form: fd }) }),
      pd: () => run(() => { if (confirm('Delete this photo?')) return api('/api/admin/photos/' + id, { m: 'DELETE' }) }),
      lk: () => run(() => { const d = $('#le').value; return api('/api/admin/registration-links', { m: 'POST', body: { club_slug: $('#lc').value, title: v('#lt') || 'Registration link', ends_at: d ? new Date(d + 'T23:59:59').toISOString() : null } }) }),
      lt2: () => run(() => api('/api/admin/registration-links/' + id, { m: 'PATCH', body: { active: b.dataset.on !== 'true' } })),
      ld: () => run(() => { if (confirm('Delete this registration link?')) return api('/api/admin/registration-links/' + id, { m: 'DELETE' }) }),
      md: () => run(() => { if (confirm('Delete this club member?')) return api('/api/admin/memberships/' + id, { m: 'DELETE' }) })
    })[b.dataset.act]()
  }
}
route();
