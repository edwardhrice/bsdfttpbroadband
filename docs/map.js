(function () {
  "use strict";

  var STATUSES = [
    { key: "Available now", color: "var(--c-available)" },
    { key: "Planned – Project Gigabit", color: "var(--c-gis)" },
    { key: "Planned – commercial", color: "var(--c-commercial)" },
    { key: "Not planned", color: "var(--c-notplanned)" },
    { key: "Not counted by BDUK", color: "var(--c-notcounted)" }
  ];
  var BY_KEY = {};
  STATUSES.forEach(function (s) { BY_KEY[s.key] = s; });

  var STEPS = [0.85, 1, 1.25, 1.5, 1.75, 2, 2.5, 3];
  var STORE = "bsd-map-scale";

  function $(id) { return document.getElementById(id); }
  function el(tag, props, children) {
    var e = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      if (k === "text") e.textContent = props[k]; else e.setAttribute(k, props[k]);
    });
    (children || []).forEach(function (c) { e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return e;
  }
  function cssColor(v) {
    return getComputedStyle(document.documentElement).getPropertyValue(v.slice(4, -1)).trim();
  }
  function fmtDate(iso) {
    return new Date(iso.length === 10 ? iso + "T12:00:00Z" : iso)
      .toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "Europe/London" });
  }

  // ---- text size ----
  var scale = 1, map, markers = [];
  try { var saved = parseFloat(localStorage.getItem(STORE)); if (STEPS.indexOf(saved) >= 0) scale = saved; } catch (e) {}
  function applyScale(s) {
    scale = s;
    document.documentElement.style.setProperty("--scale", String(s));
    document.documentElement.style.setProperty("--bar-scale", String(Math.min(s, 1.5) / s));
    $("scale").textContent = Math.round(s * 100) + "%";
    $("smaller").disabled = s <= STEPS[0];
    $("larger").disabled = s >= STEPS[STEPS.length - 1];
    try { localStorage.setItem(STORE, String(s)); } catch (e) {}
    markers.forEach(function (m) { m.setRadius(Math.round(7 * Math.sqrt(s) * 10) / 10); });
    if (map) setTimeout(function () { map.invalidateSize(); }, 0);
  }
  function step(dir) {
    var i = STEPS.indexOf(scale);
    var n = Math.max(0, Math.min(STEPS.length - 1, i + dir));
    applyScale(STEPS[n]);
  }
  $("smaller").addEventListener("click", function () { step(-1); });
  $("larger").addEventListener("click", function () { step(1); });
  $("reset").addEventListener("click", function () { applyScale(1); });
  document.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "+" || e.key === "=") step(1);
    else if (e.key === "-" || e.key === "_") step(-1);
    else if (e.key === "0") applyScale(1);
  });
  applyScale(scale);

  // ---- full screen ----
  var fs = $("fs");
  if (!document.documentElement.requestFullscreen) { fs.hidden = true; }
  fs.addEventListener("click", function () {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen();
  });
  document.addEventListener("fullscreenchange", function () {
    var on = !!document.fullscreenElement;
    fs.setAttribute("aria-pressed", String(on));
    fs.textContent = on ? "Exit full screen" : "Full screen";
    if (map) setTimeout(function () { map.invalidateSize(); }, 100);
  });

  // ---- map ----
  function build(points, summary) {
    var m = summary.release;
    $("meta").textContent = m.data_month + " BDUK release, published " + fmtDate(m.published) +
      ". Plans are provisional and BDUK does not guarantee accuracy. Source: BDUK (OGL v3.0); contains OS data © Crown copyright and database right " +
      new Date(summary.checked_at).getUTCFullYear() + ".";
    if (typeof L === "undefined") { $("map").textContent = "The map could not be loaded."; return; }
    map = L.map("map", { scrollWheelZoom: true, zoomSnap: 0.5, zoomControl: false });
    L.control.zoom({ position: "topright" }).addTo(map);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors"
    }).addTo(map);
    var layers = {}, bounds = [], counts = {};
    STATUSES.forEach(function (s) { layers[s.key] = L.layerGroup().addTo(map); counts[s.key] = 0; });
    points.forEach(function (p) {
      var st = BY_KEY[p.status];
      if (!st) return;
      var c = cssColor(st.color);
      var mk = L.circleMarker([p.lat, p.lon], { radius: 7, weight: 2, fillOpacity: .8, color: c, fillColor: c });
      mk.bindPopup(el("div", {}, [el("strong", { text: p.postcode }), el("br"), p.status]));
      mk.addTo(layers[st.key]);
      markers.push(mk);
      mk._status = st;
      bounds.push([p.lat, p.lon]);
      counts[st.key]++;
    });
    function repaint() {
      markers.forEach(function (mk) { var c = cssColor(mk._status.color); mk.setStyle({ color: c, fillColor: c }); });
    }
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", repaint);
    applyScale(scale);
    if (bounds.length) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18 });
    else map.setView([51.09, -2.65], 14);

    STATUSES.forEach(function (st) {
      var b = el("button", { type: "button", "aria-pressed": "true" }, [
        el("span", { class: "swatch", style: "--sc:" + st.color }),
        el("span", { text: st.key }), el("span", { class: "count", text: String(counts[st.key]) })]);
      b.addEventListener("click", function () {
        var on = b.getAttribute("aria-pressed") !== "true";
        b.setAttribute("aria-pressed", String(on));
        if (on) layers[st.key].addTo(map); else map.removeLayer(layers[st.key]);
      });
      $("legend").appendChild(b);
    });
  }

  Promise.all([
    fetch("data/summary.json").then(function (r) { return r.json(); }),
    fetch("data/points.json").then(function (r) { return r.json(); })
  ]).then(function (r) { build(r[1], r[0]); })
    .catch(function () { $("meta").textContent = "Sorry, the data could not be loaded."; });
})();
