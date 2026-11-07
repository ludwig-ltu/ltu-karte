# LifeTeachUs Partnerschul-Karte

Die Karte auf [lifeteachus.org/ubersicht-partnerschulen](https://www.lifeteachus.org/ubersicht-partnerschulen).

- **Partnerschulen** mit Vertrag erscheinen mit dem Partnerschulsiegel.
- **Registrierte Schulen** erscheinen als rosa Farbeimer auf dem PLZ-Mittelpunkt, ohne Namen.
- **Landkreise** werden rosa, je mehr Schulen dort dabei sind.
- Suche nach Postleitzahl und „In meiner Nähe“ mit Liste der Partnerschulen im Umkreis von 25 km.

## Einbindung in Webflow

```html
<div id="ltu-karte"></div>
<script src="https://ludwig-ltu.github.io/ltu-karte/karte.js" defer></script>
```

## Aufbau

| Datei | Inhalt |
|---|---|
| `karte.js`, `karte.css` | Die Karte (MapLibre GL, Hintergrund von OpenFreeMap) |
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
