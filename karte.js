/* LifeTeachUs Partnerschul-Karte
 * Einbindung: <div id="ltu-karte"></div><script src="https://<pages>/karte.js" defer></script>
 * Daten: data/schulen.json, data/kreise.json, data/plz.json (werden nachts aktualisiert)
 */
(function () {
  var script = document.currentScript;
  var BASE = script ? script.src.replace(/[^\/]*$/, '') : './';
  var ML = BASE + 'vendor/'; // MapLibre GL 4.7.1
  var STYLE = 'https://tiles.openfreemap.org/styles/positron';
  var RADIUS_KM = 25;

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmt(n) { return Number(n).toLocaleString('de-DE'); }
  function loadCss(href) { if (document.querySelector('link[href="' + href + '"]')) return; var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; document.head.appendChild(l); }
  function loadJs(src) { return new Promise(function (ok, no) { if (window.maplibregl) return ok(); var s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = no; document.head.appendChild(s); }); }
  function getJson(u) { return fetch(u, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(u); return r.json(); }); }
  function km(a, b) { var R = 6371, t = Math.PI / 180, dLat = (b[1] - a[1]) * t, dLng = (b[0] - a[0]) * t; var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a[1] * t) * Math.cos(b[1] * t) * Math.sin(dLng / 2) * Math.sin(dLng / 2); return 2 * R * Math.asin(Math.sqrt(x)); }

  function routeLinks(name, c) {
    var q = encodeURIComponent(name);
    return '<a href="https://www.google.com/maps/search/?api=1&amp;query=' + c[1] + ',' + c[0] + '" target="_blank" rel="noopener">Google Maps</a>' +
      '<a href="https://maps.apple.com/?q=' + q + '&amp;ll=' + c[1] + ',' + c[0] + '" target="_blank" rel="noopener">Apple Karten</a>';
  }

  function init(root) {
    if (root.dataset.init) return; root.dataset.init = '1';
    loadCss(ML + 'maplibre-gl.css');
    loadCss(BASE + 'karte.css');

    var wrap = el('div', 'lk');
    var pin = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>';
    wrap.innerHTML =
      '<div class="lk-bar">' +
      '<form class="lk-search" role="search"><input type="text" inputmode="numeric" maxlength="5" placeholder="Postleitzahl eingeben" aria-label="Postleitzahl"><button type="submit">Suchen</button></form>' +
      '<button type="button" class="lk-near">' + pin + 'In meiner Nähe</button>' +
      '<p class="lk-msg" aria-live="polite"></p></div>' +
      '<div class="lk-map"></div>' +
      '<div class="lk-legend"><span><img src="' + BASE + 'img/siegel.png" alt="">Partnerschule</span><span><img src="' + BASE + 'img/eimer.png" alt="">Schule im Onboarding</span><span><i></i>Hier wird es rosa</span></div>' +
      '<p class="lk-stats"></p>' +
      '<div class="lk-list" aria-live="polite"></div>';
    root.innerHTML = ''; root.appendChild(wrap);

    var msg = wrap.querySelector('.lk-msg'), list = wrap.querySelector('.lk-list');
    var mobile = window.matchMedia('(max-width: 767px)').matches;

    Promise.all([loadJs(ML + 'maplibre-gl.js'), getJson(BASE + 'data/schulen.json'), getJson(BASE + 'data/kreise.json')]).then(function (r) {
      var schulen = r[1], kreise = r[2];
      var partner = { type: 'FeatureCollection', features: schulen.features.filter(function (f) { return f.properties.t === 'p'; }) };
      var reg = { type: 'FeatureCollection', features: schulen.features.filter(function (f) { return f.properties.t === 'r'; }) };
      var m = schulen.meta || {};
      var orte = {}; schulen.features.forEach(function (f) { orte[f.properties.z || f.geometry.coordinates.join()] = 1; });
      wrap.querySelector('.lk-stats').textContent = 'LifeTeachUs ist schon an ' + fmt(Object.keys(orte).length) + ' Orten in Deutschland dabei.';

      var map = new maplibregl.Map({
        container: wrap.querySelector('.lk-map'), style: STYLE,
        bounds: [[5.9, 47.3], [15.0, 55.0]], fitBoundsOptions: { padding: mobile ? 8 : 24 }, minZoom: 4, maxZoom: 16,
        maxBounds: [[1, 44.5], [20, 57.5]], cooperativeGestures: true, attributionControl: false,
        locale: {
          'CooperativeGesturesHandler.WindowsHelpText': 'Strg + Scrollen zum Zoomen der Karte',
          'CooperativeGesturesHandler.MacHelpText': '⌘ + Scrollen zum Zoomen der Karte',
          'CooperativeGesturesHandler.MobileHelpText': 'Karte mit zwei Fingern bewegen',
          'NavigationControl.ZoomIn': 'Hineinzoomen', 'NavigationControl.ZoomOut': 'Herauszoomen', 'NavigationControl.ResetBearing': 'Norden'
        }
      });
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
      wrap.querySelector('.lk-map').appendChild(el('div', 'lk-attr', '© <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> · © <a href="https://www.openmaptiles.org" target="_blank" rel="noopener">OpenMapTiles</a> · © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> · © GeoBasis-DE/BKG'));;

      function img(name, url, ratio) { return map.loadImage(url).then(function (res) { if (!map.hasImage(name)) map.addImage(name, res.data, { pixelRatio: ratio }); }); }

      map.on('load', function () {
        var layers = map.getStyle().layers, firstSymbol;
        layers.forEach(function (l) {
          if (l.type === 'background') map.setPaintProperty(l.id, 'background-color', '#fff8fb');
          else if (l.type === 'fill' && /water/.test(l.id)) map.setPaintProperty(l.id, 'fill-color', '#dce9f0');
          else if (l.type === 'symbol' && /poi|housenumber|aeroway|transit/.test(l.id)) map.setLayoutProperty(l.id, 'visibility', 'none');
          else if (l.type === 'symbol' && l.layout && /"name/.test(JSON.stringify(l.layout['text-field'] || ''))) map.setLayoutProperty(l.id, 'text-field', ['coalesce', ['get', 'name:de'], ['get', 'name']]);
          if (!firstSymbol && (l.type === 'symbol' || /road|highway|transportation|tunnel|bridge|building/.test(l.id))) firstSymbol = l.id;
        });

        map.addSource('kreise', { type: 'geojson', data: kreise });
        map.addLayer({
          id: 'kreise-fill', type: 'fill', source: 'kreise',
          paint: {
            'fill-color': ['step', ['get', 'c'], 'rgba(255,255,255,0)', 1, '#fbd3e1', 3, '#f7b5cc', 6, '#f297b7', 11, '#ec79a2', 26, '#e35b8e'],
            'fill-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.8, 8, 0.55, 10, 0.2, 12, 0.08]
          }
        }, firstSymbol);
        map.addLayer({ id: 'kreise-line', type: 'line', source: 'kreise', paint: { 'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0.5, 10, 1.2], 'line-opacity': ['interpolate', ['linear'], ['zoom'], 5, 0.9, 10, 0.5] } }, firstSymbol);

        Promise.all([img('siegel', BASE + 'img/siegel.png', 3), img('eimer', BASE + 'img/eimer.png', 2)]).then(function () {
          map.addSource('reg', { type: 'geojson', data: reg, cluster: true, clusterRadius: 36, clusterMaxZoom: 10 });
          map.addSource('partner', { type: 'geojson', data: partner, cluster: true, clusterRadius: 42, clusterMaxZoom: 10 });

          map.addLayer({ id: 'reg-cluster', type: 'circle', source: 'reg', minzoom: 7.5, filter: ['has', 'point_count'],
            paint: { 'circle-color': '#ec6f9e', 'circle-radius': ['step', ['get', 'point_count'], 13, 10, 17, 30, 21], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 } });
          map.addLayer({ id: 'reg-count', type: 'symbol', source: 'reg', minzoom: 7.5, filter: ['has', 'point_count'],
            layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-font': ['Noto Sans Bold'], 'text-size': 12 }, paint: { 'text-color': '#fff' } });
          map.addLayer({ id: 'reg-point', type: 'symbol', source: 'reg', minzoom: 7.5, filter: ['!', ['has', 'point_count']],
            layout: { 'icon-image': 'eimer', 'icon-size': ['interpolate', ['linear'], ['zoom'], 8, 0.62, 13, 0.85], 'icon-allow-overlap': true } });

          map.addLayer({ id: 'partner-cluster', type: 'circle', source: 'partner', filter: ['has', 'point_count'],
            paint: { 'circle-color': '#f3ae33', 'circle-radius': ['step', ['get', 'point_count'], 15, 10, 19, 40, 24], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2.5 } });
          map.addLayer({ id: 'partner-count', type: 'symbol', source: 'partner', filter: ['has', 'point_count'],
            layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-font': ['Noto Sans Bold'], 'text-size': 13, 'text-allow-overlap': true }, paint: { 'text-color': '#204d64' } });
          map.addLayer({ id: 'partner-point', type: 'symbol', source: 'partner', filter: ['!', ['has', 'point_count']],
            layout: { 'icon-image': 'siegel', 'icon-size': ['interpolate', ['linear'], ['zoom'], 6, 0.72, 13, 0.95], 'icon-allow-overlap': true } });

          ['partner-cluster', 'reg-cluster'].forEach(function (id) {
            map.on('click', id, function (e) {
              var f = e.features[0], src = id.split('-')[0];
              map.getSource(src).getClusterExpansionZoom(f.properties.cluster_id).then(function (z) { map.easeTo({ center: f.geometry.coordinates, zoom: Math.min(z + 0.3, 14) }); });
            });
          });
          map.on('click', 'partner-point', function (e) {
            var f = e.features[0], p = f.properties, c = f.geometry.coordinates;
            new maplibregl.Popup({ offset: 18, maxWidth: '260px' }).setLngLat(c).setHTML(
              '<div class="lk-pop"><strong>' + esc(p.n) + '</strong><span>Partnerschule' + (p.o ? ' in ' + esc(p.o) : '') + '</span><div class="lk-pop-a">' + routeLinks(p.n + (p.o ? ', ' + p.o : ''), c) + '</div></div>').addTo(map);
          });
          map.on('click', 'reg-point', function (e) {
            var f = e.features[0], p = f.properties;
            new maplibregl.Popup({ offset: 16, maxWidth: '260px' }).setLngLat(f.geometry.coordinates).setHTML(
              '<div class="lk-pop"><strong>Hier wird es rosa</strong><p>Im PLZ-Gebiet ' + esc(p.z) + ' sind Schulen im Onboarding. Mit Material aus dem Media Kit hilfst du mit, die Region zu aktivieren.</p><div class="lk-pop-a"><a href="/media-kit">Zum Media Kit</a><a href="/lifeteachus-champ">Champ werden</a></div></div>').addTo(map);
          });
          map.on('click', 'kreise-fill', function (e) {
            if (map.queryRenderedFeatures(e.point, { layers: ['partner-point', 'partner-cluster', 'reg-point', 'reg-cluster'] }).length) return;
            var p = e.features[0].properties; if (!p.c) return;
            new maplibregl.Popup({ maxWidth: '240px' }).setLngLat(e.lngLat).setHTML(
              '<div class="lk-pop"><strong>' + esc(p.n) + '</strong><p>' + (p.p ? 'Hier sind wir schon mit Partnerschulen dabei' + (p.c > p.p ? ', und weitere Schulen sind im Onboarding.' : '.') : 'Hier sind Schulen im Onboarding. Die Region wird gerade rosa.') + '</p></div>').addTo(map);
          });
          ['partner-point', 'partner-cluster', 'reg-point', 'reg-cluster'].forEach(function (id) {
            map.on('mouseenter', id, function () { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mouseleave', id, function () { map.getCanvas().style.cursor = ''; });
          });
        });
      });

      var here = null;
      function showNear(c, label) {
        if (here) here.remove();
        var dot = el('div'); dot.style.cssText = 'width:18px;height:18px;border-radius:50%;background:#204d64;border:3px solid #fff';
        here = new maplibregl.Marker({ element: dot }).setLngLat(c).addTo(map);
        map.flyTo({ center: c, zoom: 10.5, speed: 1.4 });
        var near = partner.features.map(function (f) { return { f: f, d: km(c, f.geometry.coordinates) }; })
          .filter(function (x) { return x.d <= RADIUS_KM; }).sort(function (a, b) { return a.d - b.d; });
        var regN = reg.features.filter(function (f) { return km(c, f.geometry.coordinates) <= RADIUS_KM; }).length;
        var h = '';
        if (near.length) {
          h += '<h3>' + fmt(near.length) + ' Partnerschule' + (near.length === 1 ? '' : 'n') + ' im Umkreis von ' + RADIUS_KM + ' km' + (label ? ' um ' + esc(label) : '') + '</h3><div class="lk-items">';
          near.slice(0, 8).forEach(function (x) {
            var p = x.f.properties;
            h += '<div class="lk-item"><img src="' + BASE + 'img/siegel.png" alt=""><div><strong>' + esc(p.n) + '</strong><span>' + (p.o ? esc(p.o) + ' · ' : '') + x.d.toFixed(1).replace('.', ',') + ' km</span><div class="lk-pop-a">' + routeLinks(p.n + (p.o ? ', ' + p.o : ''), x.f.geometry.coordinates) + '</div></div></div>';
          });
          h += '</div>';
          if (near.length > 8) h += '<p style="margin-top:12px">Weitere Partnerschulen siehst du auf der Karte.</p>';
        } else {
          var um = label ? ' um ' + esc(label) : '';
          h += regN
            ? '<h3>Hier wird es bald rosa</h3><p>Im Umkreis von ' + RADIUS_KM + ' km' + um + ' sind schon Schulen im Onboarding. Jetzt dabei zu sein lohnt sich: Mit Material aus dem Media Kit hilfst du mit, die Region zu aktivieren. Deine LifeLesson kannst du jederzeit auch online per Video halten.</p>'
            : '<h3>Mach deine Region rosa</h3><p>Im Umkreis von ' + RADIUS_KM + ' km' + um + ' kannst du LifeTeachUs als Erste oder Erster bekannt machen. Im Media Kit findest du Material, mit dem du Schulen in deiner Nähe ansprichst. Deine LifeLesson kannst du jederzeit auch online per Video halten.</p>';
          h += '<div class="lk-cta"><a href="/media-kit">Zum Media Kit</a><a href="/lifeteachus-champ">Champ werden</a><a href="/partnerschulen">Schule vorschlagen</a></div>';
        }
        list.innerHTML = h;
      }

      var plzCache = null;
      wrap.querySelector('.lk-search').addEventListener('submit', function (e) {
        e.preventDefault();
        var v = this.querySelector('input').value.trim();
        if (!/^\d{5}$/.test(v)) { msg.textContent = 'Bitte gib eine fünfstellige Postleitzahl ein.'; return; }
        msg.textContent = '';
        (plzCache ? Promise.resolve(plzCache) : getJson(BASE + 'data/plz.json').then(function (j) { plzCache = j; return j; })).then(function (j) {
          var c = j[v];
          if (!c) { msg.textContent = 'Diese Postleitzahl haben wir nicht gefunden.'; return; }
          showNear(c, v);
        });
      });
      wrap.querySelector('.lk-near').addEventListener('click', function () {
        if (!navigator.geolocation) { msg.textContent = 'Dein Browser kann den Standort nicht bestimmen. Gib einfach deine Postleitzahl ein.'; return; }
        msg.textContent = 'Standort wird bestimmt …';
        navigator.geolocation.getCurrentPosition(function (pos) {
          msg.textContent = '';
          showNear([pos.coords.longitude, pos.coords.latitude], 'deinen Standort');
        }, function () { msg.textContent = 'Standort nicht verfügbar. Gib einfach deine Postleitzahl ein.'; }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
      });
    }).catch(function () {
      wrap.querySelector('.lk-map').innerHTML = '<p style="padding:24px;margin:0">Die Karte konnte gerade nicht geladen werden. Bitte lade die Seite neu.</p>';
    });
  }

  function start() { var r = document.getElementById('ltu-karte'); if (r) init(r); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
