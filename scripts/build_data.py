"""Baut die Kartendaten aus einer Schul-Liste.

Eingabe (vorerst): data/import/mymaps.txt (Export der bisherigen Google-My-Maps-Karte)
  Zeile 1:  "P <plz> <plz> ..."               registrierte Schulen (nur PLZ)
  weitere:  "S|<name>|<adresse>|<lng>,<lat>"   Partnerschulen mit Vertrag
Später ersetzt scripts/sync_backend.py diese Datei durch die Daten aus dem Backend.

Ausgabe:
  data/schulen.json  GeoJSON: Partnerschulen (t="p") und registrierte Schulen je PLZ (t="r")
  data/kreise.json   GeoJSON: Landkreise mit Anzahl Schulen (c) für die rosa Einfärbung
  data/plz.json      PLZ-Mittelpunkte für die Suche
"""
import csv
import json
import os
import re
import sys

from shapely.geometry import Point, shape, mapping
from shapely.prepared import prep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "ref")

# Schulen ohne Adresse und Koordinaten im Export: Ortsmitte als Näherung
MANUELL = {
    "Zukunftscampus Karlshorst": (13.5280, 52.4830),
    "Grundschule Ost Landshut": (12.1640, 48.5420),
}


def load_plz():
    plz = {}
    with open(os.path.join(REF, "plz_geocoord.csv"), newline="") as f:
        for row in csv.DictReader(f):
            key = row.get("") or row.get("plz")
            plz[key.zfill(5)] = (round(float(row["lng"]), 5), round(float(row["lat"]), 5))
    return plz


def plz_coord(plz, z):
    """PLZ-Mittelpunkt; für neue oder fehlende PLZ der Mittelpunkt benachbarter PLZ."""
    if z in plz:
        return plz[z]
    for n in (4, 3):
        near = [c for k, c in plz.items() if k[:n] == z[:n]]
        if near:
            return (round(sum(c[0] for c in near) / len(near), 5), round(sum(c[1] for c in near) / len(near), 5))
    return None


def parse_import(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    reg = lines[0].split()[1:]
    partners = []
    for line in lines[1:]:
        if not line.startswith("S|"):
            continue
        body = line[2:]
        name_addr, _, ll = body.rpartition("|")
        name, _, addr = name_addr.rpartition("|") if name_addr.count("|") >= 1 else (name_addr, "", "")
        partners.append({"name": name.strip(), "addr": addr.strip(), "ll": ll.strip()})
    return reg, partners


def clean_name(name, addr):
    # "Schule X, Straße 1, 12345 Ort" -> Name "Schule X", Ort "Ort"
    text = addr or name
    m = re.search(r"\b(\d{5})\s+([^,]+)", text)
    plz, ort = (m.group(1), m.group(2).strip()) if m else ("", "")
    short = re.sub(r",\s*[^,]*,\s*\d{5}\s+[^,]+$", "", name)  # ", Straße 1, 12345 Ort" am Ende
    short = re.sub(r",\s*\d{5}\s+[^,]+$", "", short).strip()   # ", 12345 Ort" am Ende
    return short, plz, ort


def main(src):
    plz = load_plz()
    reg, partners = parse_import(src)

    feats = []
    missing = []
    seen = set()
    for p in partners:
        name, pz, ort = clean_name(p["name"], p["addr"])
        coord = None
        if p["ll"]:
            lng, lat = p["ll"].split(",")
            coord = (round(float(lng), 5), round(float(lat), 5))
        elif pz and plz_coord(plz, pz):
            coord = plz_coord(plz, pz)
        elif name in MANUELL:
            coord = MANUELL[name]
        if not coord:
            missing.append(p["name"])
            continue
        key = (name.lower(), round(coord[0], 3), round(coord[1], 3))
        if key in seen:  # doppelte Einträge
            continue
        seen.add(key)
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": list(coord)},
                      "properties": {"t": "p", "n": name, "o": ort, "z": pz}})

    counts = {}
    for z in reg:
        z = z.zfill(5)
        counts[z] = counts.get(z, 0) + 1
    for z, n in sorted(counts.items()):
        c = plz_coord(plz, z)
        if not c:
            missing.append("PLZ " + z)
            continue
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": list(c)},
                      "properties": {"t": "r", "z": z, "k": n}})

    # Landkreise
    kreise = json.load(open(os.path.join(REF, "kreise_bkg.geojson"), encoding="utf-8"))  # © GeoBasis-DE / BKG (VG250)
    polys = []
    for f in kreise["features"]:
        if f["properties"].get("GF") != 4:  # nur Landflächen
            continue
        g = shape(f["geometry"]).simplify(0.012, preserve_topology=True)
        name = f["properties"]["GEN"]
        if f["properties"].get("BEZ", "").startswith("Kreisfreie"):
            name += " (Stadt)"
        polys.append({"g": g, "pg": prep(g), "name": name, "c": 0, "p": 0})
    for ft in feats:
        pt = Point(ft["geometry"]["coordinates"])
        add = ft["properties"].get("k", 1)
        for k in polys:
            if k["pg"].contains(pt):
                k["c"] += add
                if ft["properties"]["t"] == "p":
                    k["p"] += 1
                break

    def rnd(geom):
        m = mapping(geom)

        def r(c):
            if isinstance(c[0], (list, tuple)):
                return [r(x) for x in c]
            return [round(c[0], 3), round(c[1], 3)]
        m["coordinates"] = r(m["coordinates"])
        return m

    kfeats = [{"type": "Feature", "geometry": rnd(k["g"]), "properties": {"n": k["name"], "c": k["c"], "p": k["p"]}}
              for k in polys]

    out = os.path.join(ROOT, "data")
    meta = {"partner": sum(1 for f in feats if f["properties"]["t"] == "p"), "registriert": sum(counts.values())}
    json.dump({"type": "FeatureCollection", "meta": meta, "features": feats},
              open(os.path.join(out, "schulen.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"type": "FeatureCollection", "features": kfeats},
              open(os.path.join(out, "kreise.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({z: [c[0], c[1]] for z, c in sorted(plz.items())},
              open(os.path.join(out, "plz.json"), "w"), separators=(",", ":"))
    print("Partnerschulen:", meta["partner"], "| registriert:", meta["registriert"], "in", len(counts), "PLZ")
    print("ohne Ort:", missing)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "import", "mymaps.txt"))
