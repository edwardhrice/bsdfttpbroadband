(function () {
  "use strict";

  var STATUSES = [
    { key: "Available now", slug: "available_now", color: "var(--c-available)",
      def: "BDUK's data says the premises can already get a gigabit-capable connection." },
    { key: "Planned – Project Gigabit", slug: "planned_project_gigabit", color: "var(--c-gis)",
      def: "Included in a government-funded Project Gigabit contract." },
    { key: "Planned – commercial", slug: "planned_commercial", color: "var(--c-commercial)",
      def: "A broadband company has said it plans to build gigabit coverage here without public money." },
    { key: "Not planned", slug: "not_planned", color: "var(--c-notplanned)",
      def: "No gigabit connection and no plan on record. Premises marked “Gigabit White” are eligible for public subsidy." },
    { key: "Not counted by BDUK", slug: "not_counted", color: "var(--c-notcounted)",
      def: "BDUK does not treat this as a premises for its plans (for example a non-residential or unoccupied building)." }
  ];
  var BY_KEY = {};
  STATUSES.forEach(function (s) { BY_KEY[s.key] = s; });

  function $(id) { return document.getElementById(id); }
  function el(tag, props, children) {
    var e = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      if (k === "text") e.textContent = props[k];
      else if (k === "style") e.setAttribute("style", props[k]);
      else e.setAttribute(k, props[k]);
    });
    (children || []).forEach(function (c) { e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return e;
  }
  function fmtDate(iso) {
    var d = new Date(iso.length === 10 ? iso + "T12:00:00Z" : iso);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "Europe/London" });
  }
  function pct(n, d) { return d ? Math.round(100 * n / d) + "%" : "–"; }
  function getJSON(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function getText(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u); return r.text(); }); }

  function parseCSV(text) {
    var lines = text.trim().split(/\r?\n/), head = lines[0].split(",");
    return lines.slice(1).map(function (l) {
      var v = l.split(","), o = {};
      head.forEach(function (h, i) { o[h] = v[i]; });
      return o;
    });
  }

  function renderMeta(s, lc) {
    $("meta").textContent = "";
    $("meta").appendChild(document.createTextNode("Data: "));
    $("meta").appendChild(el("a", { href: s.release.page_url, text: s.release.data_month + " BDUK release" }));
    $("meta").appendChild(document.createTextNode(", published " + fmtDate(s.release.published) +
      ". Last checked for a new release " + fmtDate((lc && lc.last_checked) || s.checked_at) + "."));
    $("osyear").textContent = new Date(s.checked_at).getUTCFullYear();
  }

  function renderHeadline(s) {
    var n = s.by_status, rec = s.recognised_premises;
    var avail = n["Available now"], gis = n["Planned – Project Gigabit"],
        none = n["Not planned"] + n["Planned – commercial"];
    $("headline").textContent = avail + " of the " + rec + " premises BDUK counts in the parish (" + pct(avail, rec) +
      ") can get gigabit broadband today. " + gis + " more (" + pct(gis, rec) +
      ") are in a Project Gigabit plan, and " + n["Not planned"] + " have no plan on record.";
    var tiles = $("tiles");
    tiles.appendChild(el("li", { class: "tile", style: "--tc:var(--border)" }, [
      el("span", { class: "n", text: String(s.total_premises) }), el("span", { class: "l", text: "premises in the parish" })]));
    STATUSES.forEach(function (st) {
      tiles.appendChild(el("li", { class: "tile", style: "--tc:" + st.color }, [
        el("span", { class: "n", text: String(n[st.key]) }), el("span", { class: "l", text: st.key })]));
    });
  }

  function renderGis(s) {
    var g = s.project_gigabit, box = $("gis");
    if (!g.premises) {
      box.appendChild(el("p", { text: "No premises in the parish are in a Project Gigabit plan in this release." }));
      return;
    }
    var join = function (a) { return a.join(", "); };
    box.appendChild(el("p", { text: g.premises + " premises are in a Project Gigabit plan. Supplier: " + join(g.suppliers) +
      ". Contract scope: " + join(g.contract_scopes) + ". Final coverage date: " +
      g.final_coverage_dates.map(fmtDate).join(", ") + "." }));
    if (g.under_review && g.under_review === g.premises) {
      box.appendChild(el("p", { text: "All " + g.under_review + " are classed “Gigabit Under Review” in the BDUK data." }));
    } else if (g.under_review) {
      box.appendChild(el("p", { text: g.under_review + " of these are classed “Gigabit Under Review” in the BDUK data." }));
    }
    if (s.vouchers.length) {
      box.appendChild(el("p", { text: "Gigabit voucher connections on record: " + s.vouchers.map(function (v) {
        return v.supplier + " at " + v.postcode; }).join("; ") + "." }));
    }
  }

  function renderPostcodes(s) {
    var t = $("pc-table"), head = el("tr", {}, [el("th", { scope: "col", text: "Postcode" }), el("th", { scope: "col", text: "Premises" })]);
    STATUSES.forEach(function (st) { head.appendChild(el("th", { scope: "col", text: st.key })); });
    t.appendChild(el("thead", {}, [head]));
    var body = el("tbody"), tot = { all: 0 };
    Object.keys(s.by_postcode).forEach(function (pc) {
      var row = s.by_postcode[pc], sum = 0, tr = el("tr");
      STATUSES.forEach(function (st) { sum += row[st.key]; });
      tr.appendChild(el("th", { scope: "row", text: pc }));
      tr.appendChild(el("td", { text: String(sum) }));
      tot.all += sum;
      STATUSES.forEach(function (st) {
        tot[st.key] = (tot[st.key] || 0) + row[st.key];
        tr.appendChild(el("td", { class: row[st.key] ? "" : "zero", text: String(row[st.key]) }));
      });
      body.appendChild(tr);
    });
    t.appendChild(body);
    var foot = el("tr", {}, [el("th", { scope: "row", text: "Parish total" }), el("td", { text: String(tot.all) })]);
    STATUSES.forEach(function (st) { foot.appendChild(el("td", { text: String(tot[st.key] || 0) })); });
    t.appendChild(el("tfoot", {}, [foot]));
  }

  function renderDefs() {
    var dl = $("defs");
    STATUSES.forEach(function (st) {
      dl.appendChild(el("dt", {}, [el("span", { class: "swatch", style: "--sc:" + st.color }), st.key]));
      dl.appendChild(el("dd", { text: st.def }));
    });
  }

  function renderChart(history) {
    var NS = "http://www.w3.org/2000/svg";
    function s(tag, attrs, text) {
      var e = document.createElementNS(NS, tag);
      Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
      if (text != null) e.textContent = text;
      return e;
    }
    var W = 640, H = 320, m = { l: 40, r: 12, t: 16, b: 52 };
    var rows = history.map(function (r) {
      var o = { label: r.data_month, total: 0 };
      STATUSES.forEach(function (st) { o[st.slug] = +r[st.slug]; o.total += +r[st.slug]; });
      return o;
    });
    var max = Math.max.apply(null, rows.map(function (r) { return r.total; }));
    var ymax = Math.ceil(max / 50) * 50 || 50;
    var iw = W - m.l - m.r, ih = H - m.t - m.b, slot = iw / rows.length, bw = Math.min(slot * 0.62, 80);
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, role: "img",
      "aria-label": "Stacked bar chart of premises by gigabit status in each BDUK release" });
    function y(v) { return m.t + ih - ih * v / ymax; }
    for (var g = 0; g <= ymax; g += ymax / 5) {
      svg.appendChild(s("line", { x1: m.l, x2: W - m.r, y1: y(g), y2: y(g), class: "axis", "stroke-width": 1 }));
      svg.appendChild(s("text", { x: m.l - 6, y: y(g) + 4, "text-anchor": "end" }, String(Math.round(g))));
    }
    rows.forEach(function (r, i) {
      var x = m.l + slot * i + (slot - bw) / 2, acc = 0;
      STATUSES.forEach(function (st) {
        var v = r[st.slug];
        if (!v) return;
        var top = y(acc + v), h = y(acc) - top;
        svg.appendChild(s("rect", { x: x, y: top, width: bw, height: h, fill: st.color }, null))
          .appendChild(s("title", {}, r.label + ": " + st.key + " " + v));
        if (h > 16) svg.appendChild(s("text", { x: x + bw / 2, y: top + h / 2 + 4, "text-anchor": "middle", class: "seg-label" }, String(v)));
        acc += v;
      });
      var cx = x + bw / 2, parts = r.label.split(" ");
      svg.appendChild(s("text", { x: cx, y: H - m.b + 18, "text-anchor": "middle" }, parts[0]));
      svg.appendChild(s("text", { x: cx, y: H - m.b + 33, "text-anchor": "middle" }, parts.slice(1).join(" ")));
    });
    $("chart").appendChild(svg);
    var key = el("div", { class: "chart-key" });
    STATUSES.forEach(function (st) {
      key.appendChild(el("span", {}, [el("span", { class: "swatch", style: "--sc:" + st.color }), st.key]));
    });
    $("chart").appendChild(key);

    var t = $("history-table"), hr = el("tr", {}, [el("th", { scope: "col", text: "Release" }), el("th", { scope: "col", text: "Premises" })]);
    STATUSES.forEach(function (st) { hr.appendChild(el("th", { scope: "col", text: st.key })); });
    t.appendChild(el("thead", {}, [hr]));
    var tb = el("tbody");
    rows.forEach(function (r) {
      var tr = el("tr", {}, [el("th", { scope: "row", text: r.label }), el("td", { text: String(r.total) })]);
      STATUSES.forEach(function (st) { tr.appendChild(el("td", { text: String(r[st.slug]) })); });
      tb.appendChild(tr);
    });
    t.appendChild(tb);
  }

  function cssColor(v) {
    var name = v.slice(4, -1);
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function renderMap(points, s) {
    if (typeof L === "undefined") { $("map").textContent = "The map could not be loaded."; return; }
    if (!points.length) { $("map").textContent = "No coordinates available yet."; return; }
    var map = L.map("map", { scrollWheelZoom: false });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors"
    }).addTo(map);
    var layers = {}, all = [];
    STATUSES.forEach(function (st) { layers[st.key] = L.layerGroup().addTo(map); });
    function paint() {
      STATUSES.forEach(function (st) {
        layers[st.key].eachLayer(function (m) { m.setStyle({ color: cssColor(st.color), fillColor: cssColor(st.color) }); });
      });
    }
    points.forEach(function (p) {
      var st = BY_KEY[p.status];
      if (!st) return;
      var m = L.circleMarker([p.lat, p.lon], { radius: 7, weight: 2, fillOpacity: .75 });
      m.bindPopup(el("div", {}, [el("strong", { text: p.postcode }), el("br"), p.status]));
      m.addTo(layers[st.key]);
      all.push([p.lat, p.lon]);
    });
    paint();
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", paint);
    map.fitBounds(all, { padding: [24, 24], maxZoom: 17 });

    var counts = {};
    points.forEach(function (p) { counts[p.status] = (counts[p.status] || 0) + 1; });
    STATUSES.forEach(function (st) {
      var b = el("button", { type: "button", "aria-pressed": "true" }, [
        el("span", { class: "swatch", style: "--sc:" + st.color }), st.key + " (" + (counts[st.key] || 0) + ")"]);
      b.addEventListener("click", function () {
        var on = b.getAttribute("aria-pressed") !== "true";
        b.setAttribute("aria-pressed", String(on));
        if (on) layers[st.key].addTo(map); else map.removeLayer(layers[st.key]);
      });
      $("legend").appendChild(b);
    });
    var missing = s.total_premises - points.length;
    $("map-note").textContent = missing > 0
      ? missing + (missing === 1 ? " premises is" : " premises are") + " not shown because Ordnance Survey has no coordinates yet."
      : "";
  }

  Promise.all([getJSON("data/summary.json"), getText("data/history.csv"), getJSON("data/points.json"), getJSON("data/last_check.json").catch(function () { return null; })])
    .then(function (r) {
      var s = r[0];
      renderMeta(s, r[3]); renderHeadline(s); renderGis(s); renderPostcodes(s); renderDefs();
      renderChart(parseCSV(r[1]));
      renderMap(r[2], s);
    })
    .catch(function () {
      $("meta").textContent = "Sorry, the data could not be loaded. Please try again later.";
    });
})();
