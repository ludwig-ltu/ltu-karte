# LifeTeachUs Partnerschul-Karte

Die Karte auf [lifeteachus.org/ubersicht-partnerschulen](https://www.lifeteachus.org/ubersicht-partnerschulen).

- **Partnerschulen** mit Vertrag erscheinen mit dem Partnerschulsiegel.
- **Schulen im Onboarding** („Bald dabei“) erscheinen als pulsierender rosa Punkt auf dem PLZ-Mittelpunkt, ohne Namen.
- **Landkreise** werden rosa, je mehr Schulen dort dabei sind.
- Suche nach Postleitzahl und „In meiner Nähe“ mit Liste der Partnerschulen im Umkreis von 25 km. Ist dort noch keine dabei, führt die Karte zum Media Kit, um die Region zu aktivieren.

## Einbindung in Webflow

```html
<div id="ltu-karte"></div>
<script src="https://ludwig-ltu.github.io/ltu-karte/karte.js" defer></script>
```

Mit eigenem Ausschnitt (z. B. Kampagnenseiten): `<div id="ltu-karte" data-center="48.78, 9.18" data-zoom="9"></div>`

## Aufbau

| Datei | Inhalt |
|---|---|
| `karte.js`, `karte.css` | Die Karte (Hintergrund von OpenFreeMap) |
| `vendor/` | MapLibre GL 4.7.1, selbst gehostet |
| `data/schulen.json` | Partnerschulen und registrierte PLZ-Gebiete |
| `data/kreise.json` | Landkreise mit Anzahl Schulen und LifeTeacher |
| `data/plz.json` | PLZ-Mittelpunkte für die Suche |
| `data/ref/partner_koordinaten.json` | Feste Position je Partnerschule (Schul-ID) |
| `scripts/build_data.py` | Baut die Dateien in `data/` |
| `scripts/sync_backend.py` | Liest Schulen und LifeTeacher aus dem Backend |
| `.github/workflows/abgleich.yml` | Startet den Abgleich stündlich |

## Quellen

- Kartenhintergrund: [OpenFreeMap](https://openfreemap.org), © [OpenMapTiles](https://www.openmaptiles.org), Daten © [OpenStreetMap](https://www.openstreetmap.org/copyright)
- Landkreise: © GeoBasis-DE / BKG (VG250), aufbereitet von [opendatalab-de](https://github.com/opendatalab-de/simple-geodata-selector)
- PLZ-Mittelpunkte: [WZB plz_geocoord](https://github.com/WZBSocialScienceCenter/plz_geocoord)

## Datenschutz

Die Karte setzt keine Cookies. Beim Laden werden Programmcode und Kartendaten von GitHub Pages und die Hintergrundkarte von OpenFreeMap abgerufen. Registrierte Schulen erscheinen nur als PLZ-Gebiet ohne Namen; Name und Ort zeigt die Karte nur bei Partnerschulen mit Vertrag.

## Abgleich mit dem Backend

Der Workflow `abgleich.yml` läuft stündlich von etwa 6 bis 22 Uhr und lässt sich unter „Actions“ auch von Hand starten („Run workflow“). `scripts/sync_backend.py` liest zwei Endpunkte der Karten-API:

- `/map/schools`: alle aktiven Schulen, `verified: true` = Partnerschule
- `/map/teachers`: aktive LifeTeacher je PLZ

Dafür braucht das Repo unter Settings › Secrets and variables › Actions zwei Secrets: `LTU_API_URL` (Basis-URL inklusive `/prod`) und `LTU_API_TOKEN` (wird als `x-api-key` gesendet). Der Token steht nur dort, nie im Code.

Öffentlich im Repo und auf der Karte landen nur Partnerschulen mit Name und Ort, alle anderen Schulen als PLZ-Gebiet ohne Namen und LifeTeacher als Summe je Landkreis. Die Rohdaten bleiben im Zwischenordner `.cache/`, der nicht ins Repo übernommen wird. Liefert das Backend einen Fehler oder deutlich weniger Partnerschulen als bisher, bricht der Abgleich ab und die Karte behält den letzten Stand.

Partnerschulen haben im Backend nur PLZ und Ort. Beim ersten Abgleich übernimmt jede Partnerschule ihre bisherige Position von der Karte (gleicher Name oder einzige Partnerschule in der PLZ), neue Partnerschulen sitzen auf dem PLZ-Mittelpunkt, bei mehreren in einer PLZ leicht versetzt. Eine Position lässt sich in `data/ref/partner_koordinaten.json` von Hand korrigieren und bleibt dann erhalten.
