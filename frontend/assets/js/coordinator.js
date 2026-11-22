/* coordinator.js — frontend for the coordinator portal (login, announcements, photos, reports). */
(function () {
  "use strict";

  /* ===================== SETTINGS =====================
     DEMO:false  talks to your backend. Set API to your server URL ("" = same site) and match PATHS.
     To create a coordinator account: log in to the admin dashboard and create an admin with role=coordinator
     and assign them to a club_id via the API (POST /api/admin/admins). */
  var CONFIG = {
    DEMO: false,
    API: "",
    PATHS: { login: "/api/coordinator/login", ann: "/api/coordinator/announcements", ph: "/api/coordinator/photos", rep: "/api/coordinator/reports" }
  };
  /* Demo accounts, used only when DEMO is true. Real accounts must be created and checked on the server. */
  var DEMO_USERS = [
    { u: "tech.coord", p: "Tech@123", name: "Tech Coordinator", club: "Tech Club" },
    { u: "sports.coord", p: "Sports@123", name: "Sports Coordinator", club: "Sports Club" },
    { u: "management.coord", p: "Mgmt@123", name: "Management Coordinator", club: "Management Club" }
  ];
  var MAX = { ph: 5 * 1024 * 1024, rep: 10 * 1024 * 1024 };
  var REPORT_EXT = /\.(pdf|docx?|xlsx?|pptx?)$/i;

  var $ = function (id) { return document.getElementById(id); };
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function fmt(d) { var x = new Date(d); return isNaN(x) ? "" : x.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }); }
  function size(b) { return b > 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB"; }
  function formOf(o) { var f = new FormData(); Object.keys(o).forEach(function (k) { f.append(k, o[k]); }); return f; }
  function say(text, ok) { var m = $("msg"); m.className = ok ? "ok" : "err"; m.textContent = text || ""; }

  var session = null;
  try { session = JSON.parse(sessionStorage.getItem("coSession")); } catch (e) {}

  /* ===================== DATA LAYER (demo or real) ===================== */
  function req(method, path, body) {
    var h = {}, o = { method: method, headers: h };
    if (session && session.token) h.Authorization = "Bearer " + session.token;
    if (body instanceof FormData) o.body = body;
    else if (body) { h["Content-Type"] = "application/json"; o.body = JSON.stringify(body); }
    return fetch(CONFIG.API + path, o).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error(d.detail || d.message || "Request failed (" + r.status + ")");
        return d;
      });
    });
  }
  function dkey(k) { return "co:" + session.u + ":" + k; }
  function dload(k) { try { return JSON.parse(localStorage.getItem(dkey(k))) || []; } catch (e) { return []; } }

  var api = {
    login: function (u, p) {
      if (!CONFIG.DEMO) return req("POST", CONFIG.PATHS.login, { username: u, password: p }); // expects {token, name, club}
      var m = DEMO_USERS.filter(function (x) { return x.u === u && x.p === p; })[0];
      return m ? Promise.resolve({ token: "demo", name: m.name, club: m.club }) : Promise.reject(new Error("Wrong username or password."));
    },
    list: function (k) { return CONFIG.DEMO ? Promise.resolve(dload(k)) : req("GET", CONFIG.PATHS[k]); },
    add: function (k, item, form) {
      if (!CONFIG.DEMO) return req("POST", CONFIG.PATHS[k], form || item);
      item.id = Date.now() + Math.random().toString(36).slice(2, 6);
      item.at = new Date().toISOString();
      var a = dload(k); a.unshift(item);
      try { localStorage.setItem(dkey(k), JSON.stringify(a)); } catch (e) { return Promise.reject(new Error("Browser storage is full (demo mode).")); }
      return Promise.resolve(item);
    },
    del: function (k, id) {
      if (!CONFIG.DEMO) return req("DELETE", CONFIG.PATHS[k] + "/" + encodeURIComponent(id));
      localStorage.setItem(dkey(k), JSON.stringify(dload(k).filter(function (x) { return x.id !== id; })));
      return Promise.resolve({});
    }
  };

  /* ===================== LISTS ===================== */
  function delBtn(kind, id) {
    var b = el("button", "chip danger sm", "Delete"); b.type = "button";
    b.addEventListener("click", function () {
      if (confirm("Delete this item?")) api.del(kind, id).then(function () { say("Deleted.", true); return refresh(kind); }).catch(function (e) { say(e.message); });
    });
    return b;
  }
  function empty(box, text) { box.appendChild(el("p", "empty", text)); }

  var render = {
    ann: function (box, items) {
      items.forEach(function (a) {
        var d = el("div", "item");
        d.appendChild(el("h4", "", a.title)); d.appendChild(el("small", "", fmt(a.at || a.created || a.published_at)));
        d.appendChild(el("p", "", a.message)); d.appendChild(delBtn("ann", a.id)); box.appendChild(d);
      });
    },
    ph: function (box, items) {
      items.forEach(function (p) {
        var f = el("figure"), i = el("img"); i.src = p.src || p.url || p.image_url; i.alt = p.title || "";
        f.appendChild(i); f.appendChild(el("figcaption", "", (p.title || "") + ((p.event || p.event_name) ? " · " + (p.event || p.event_name) : "")));
        f.appendChild(delBtn("ph", p.id)); box.appendChild(f);
      });
    },
    rep: function (box, items) {
      items.forEach(function (r) {
        var d = el("div", "item"), meta = el("div", "rep-meta"), btns = el("div", "rep-btns");
        d.appendChild(el("h4", "", r.title));
        if (r.event_date) meta.appendChild(el("span", "", "Event: " + fmt(r.event_date)));
        meta.appendChild(el("span", "", (r.filename || "report") + (r.size ? " (" + size(r.size) + ")" : "")));
        meta.appendChild(el("span", "", "Uploaded " + fmt(r.at || r.created)));
        d.appendChild(meta);
        if (r.summary) d.appendChild(el("p", "", r.summary));
        if (r.url) { var a = el("a", "chip sm", "Open"); a.href = r.url; a.target = "_blank"; a.rel = "noopener"; btns.appendChild(a); }
        btns.appendChild(delBtn("rep", r.id)); d.appendChild(btns); box.appendChild(d);
      });
    }
  };
  var EMPTY = { ann: "Nothing published yet.", ph: "No photos uploaded yet.", rep: "No reports uploaded yet." };

  function refresh(kind) {
    return api.list(kind).then(function (items) {
      var box = $(kind + "-list"); box.textContent = "";
      $("n-" + kind).textContent = items.length;
      if (items.length) render[kind](box, items); else empty(box, EMPTY[kind]);
    }).catch(function (e) { say(e.message); });
  }

  /* ===================== LOGIN / LOGOUT ===================== */
  function showDash() {
    $("login-view").hidden = true; $("dash-view").hidden = false;
    $("co-club").textContent = session.club + " Coordinator";
    $("co-name").textContent = "Signed in as " + session.name;
    ["ann", "ph", "rep"].forEach(refresh);
  }
  function showLogin() { $("dash-view").hidden = true; $("login-view").hidden = false; say(""); }

  $("login-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var err = $("login-err"), u = $("cu").value.trim(), p = $("cp").value;
    err.textContent = "";
    if (!u || !p) { err.textContent = "Enter your username and password."; return; }
    api.login(u, p).then(function (d) {
      session = { token: d.token, name: d.name || u, club: d.club || "Club", u: u };
      sessionStorage.setItem("coSession", JSON.stringify(session));
      $("cp").value = ""; showDash();
    }).catch(function (x) { err.textContent = x.message; });
  });
  $("logout").addEventListener("click", function () { sessionStorage.removeItem("coSession"); session = null; showLogin(); });

  /* ===================== TABS ===================== */
  [].forEach.call(document.querySelectorAll("[data-tab]"), function (b) {
    b.addEventListener("click", function () {
      [].forEach.call(document.querySelectorAll("[data-tab]"), function (x) {
        var on = x === b; x.setAttribute("aria-pressed", on); $("tab-" + x.dataset.tab).hidden = !on;
      });
      say("");
    });
  });

  /* ===================== ANNOUNCEMENTS ===================== */
  $("ann-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var t = $("at").value.trim(), m = $("am").value.trim();
    if (!t || !m) return say("Enter a title and a message.");
    api.add("ann", { title: t, message: m }).then(function () {
      $("ann-form").reset(); say("Announcement published.", true); return refresh("ann");
    }).catch(function (x) { say(x.message); });
  });

  /* ===================== PHOTOS ===================== */
  function shrink(f) { // demo mode only: keep a small copy so it fits in browser storage
    return new Promise(function (res, rej) {
      var r = new FileReader();
      r.onerror = function () { rej(new Error("Could not read " + f.name)); };
      r.onload = function () {
        var im = new Image();
        im.onerror = function () { rej(new Error("Could not read " + f.name)); };
        im.onload = function () {
          var s = Math.min(1, 480 / Math.max(im.width, im.height)), c = document.createElement("canvas");
          c.width = Math.round(im.width * s); c.height = Math.round(im.height * s);
          c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); res(c.toDataURL("image/jpeg", 0.7));
        };
        im.src = r.result;
      };
      r.readAsDataURL(f);
    });
  }
  $("phf").addEventListener("change", function () {
    var box = $("ph-prev"); box.textContent = "";
    [].forEach.call($("phf").files, function (f) {
      if (f.type.indexOf("image/") !== 0) return;
      var fig = el("figure"), i = el("img"); i.src = URL.createObjectURL(f); i.alt = "";
      fig.appendChild(i); fig.appendChild(el("figcaption", "", f.name)); box.appendChild(fig);
    });
  });
  $("ph-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var files = [].slice.call($("phf").files), t = $("pt").value.trim(), ev = $("pe").value.trim();
    if (!files.length) return say("Choose at least one image.");
    for (var i = 0; i < files.length; i++) {
      if (files[i].type.indexOf("image/") !== 0) return say(files[i].name + " is not an image.");
      if (files[i].size > MAX.ph) return say(files[i].name + " is larger than 5 MB.");
    }
    Promise.all(files.map(function (f) {
      var title = t || f.name;
      return CONFIG.DEMO
        ? shrink(f).then(function (src) { return api.add("ph", { title: title, event: ev, src: src }); })
        : api.add("ph", null, formOf({ file: f, title: title, event: ev }));
    })).then(function () {
      $("ph-form").reset(); $("ph-prev").textContent = ""; say(files.length + " photo(s) uploaded.", true); return refresh("ph");
    }).catch(function (x) { say(x.message); });
  });

  /* ===================== REPORTS ===================== */
  $("rep-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var f = $("rf").files[0], t = $("rt").value.trim();
    if (!f) return say("Choose a report file.");
    if (!REPORT_EXT.test(f.name)) return say("Reports must be PDF, Word, Excel or PowerPoint files.");
    if (f.size > MAX.rep) return say("The report is larger than 10 MB.");
    if (!t) return say("Enter a report title.");
    var meta = { title: t, event_date: $("rd").value, summary: $("rs").value.trim() };
    var p = CONFIG.DEMO
      ? api.add("rep", { title: meta.title, event_date: meta.event_date, summary: meta.summary, filename: f.name, size: f.size })
      : api.add("rep", null, formOf({ file: f, title: meta.title, event_date: meta.event_date, summary: meta.summary }));
    p.then(function () { $("rep-form").reset(); say("Report uploaded.", true); return refresh("rep"); })
      .catch(function (x) { say(x.message); });
  });

  /* ===================== START ===================== */
  if (CONFIG.DEMO) {
    var n = $("demo-note"); n.hidden = false;
    n.textContent = "Demo mode: nothing is sent to a server. Try " + DEMO_USERS[0].u + " / " + DEMO_USERS[0].p + ".";
  } else {
    var n2 = $("demo-note"); if (n2) n2.hidden = true;
  }
  if (session && session.u) showDash();
})();