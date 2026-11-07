# LifeTeachUs Partnerschul-Karte

Die Karte auf [lifeteachus.org/ubersicht-partnerschulen](https://www.lifeteachus.org/ubersicht-partnerschulen).

- **Partnerschulen** mit Vertrag erscheinen mit dem Partnerschulsiegel.
- **Schulen im Onboarding** erscheinen als rosa Farbeimer auf dem PLZ-Mittelpunkt, ohne Namen.
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
| `data/kreise.json` | Landkreise mit Anzahl Schulen |
| `data/plz.json` | PLZ-Mittelpunkte für die Suche |
| `scripts/build_data.py` | Baut die Dateien in `data/` |
| `scripts/sync_backend.py` | Liest die Schulen nachts aus dem Backend |
| `.github/workflows/abgleich.yml` | Startet den Abgleich jede Nacht |

## Quellen

- Kartenhintergrund: [OpenFreeMap](https://openfreemap.org), © [OpenMapTiles](https://www.openmaptiles.org), Daten © [OpenStreetMap](https://www.openstreetmap.org/copyright)
- Landkreise: © GeoBasis-DE / BKG (VG250), aufbereitet von [opendatalab-de](https://github.com/opendatalab-de/simple-geodata-selector)
- PLZ-Mittelpunkte: [WZB plz_geocoord](https://github.com/WZBSocialScienceCenter/plz_geocoord)

## Datenschutz

Die Karte setzt keine Cookies. Beim Laden werden Programmcode und Kartendaten von GitHub Pages und die Hintergrundkarte von OpenFreeMap abgerufen. Registrierte Schulen erscheinen nur als PLZ-Gebiet ohne Namen; Name und Ort zeigt die Karte nur bei Partnerschulen mit Vertrag.

## Nächtlicher Abgleich

Der Workflow `abgleich.yml` läuft jede Nacht. Sobald die Secrets `LTU_API_URL` und `LTU_API_TOKEN` sowie die Variable `LTU_SCHOOLS_QUERY` hinterlegt sind, liest `scripts/sync_backend.py` die Schulen aus dem Backend. Danach baut `scripts/build_data.py` die Kartendaten neu. Ohne diese Angaben bleibt der letzte Stand online.
