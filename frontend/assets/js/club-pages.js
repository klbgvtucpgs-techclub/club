/* club-pages.js — shared by all four club pages.
   Sub-club details live in the HTML (see each page). This file only opens the floating panel. */
(function () {
  "use strict";
  var dlg = document.getElementById("subclub-panel");

  if (dlg) {
    document.querySelectorAll(".cp-item").forEach(function (item) {
      var card = item.querySelector(".cp-card");
      var tpl = item.querySelector("template.cp-detail");
      if (!card || !tpl) return;

      card.addEventListener("click", function () {
        dlg.textContent = "";
        dlg.appendChild(tpl.content.cloneNode(true));

        var act = document.createElement("div");
        act.className = "cp-act";
        var join = document.createElement("a");
        join.className = "cp-btn";
        join.href = "index.html#register";
        join.textContent = "Join this club";
        var close = document.createElement("button");
        close.type = "button";
        close.className = "cp-btn ghost";
        close.textContent = "Close";
        close.addEventListener("click", function () { dlg.close(); });
        act.appendChild(join);
        act.appendChild(close);
        dlg.appendChild(act);

        dlg._opener = card;
        dlg.showModal();
      });
    });

    dlg.addEventListener("click", function (e) { if (e.target === dlg) dlg.close(); });
    dlg.addEventListener("close", function () { if (dlg._opener) dlg._opener.focus(); });
  }

  var menu = document.getElementById("menu"), nav = document.getElementById("nav");
  if (menu && nav) {
    menu.addEventListener("click", function () {
      menu.setAttribute("aria-expanded", nav.classList.toggle("open"));
    });
  }
})();
