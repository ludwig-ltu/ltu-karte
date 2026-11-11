"""Baut die Kartendaten aus einer Schul-Liste.

Eingabe:
  .cache/backend.json  Live-Daten aus dem Backend (scripts/sync_backend.py), wenn vorhanden
  sonst data/import/mymaps.txt (Export der früheren Google-My-Maps-Karte)
    Zeile 1:  "P <plz> <plz> ..."               registrierte Schulen (nur PLZ)
    weitere:  "S|<name>|<adresse>|<lng>,<lat>"   Partnerschulen mit Vertrag

Partnerschulen haben im Backend nur PLZ und Ort. Ihre Position merkt sich
data/ref/partner_koordinaten.json (Schul-ID -> Koordinate). Neue Partnerschulen übernehmen beim
ersten Lauf die bisherige Position von der Karte (gleicher Name oder einzige Schule in der PLZ),
sonst den PLZ-Mittelpunkt, bei mehreren Schulen in einer PLZ leicht versetzt.

Ausgabe:
  data/schulen.json  GeoJSON: Partnerschulen (t="p") und registrierte Schulen je PLZ (t="r")
  data/kreise.json   GeoJSON: Landkreise mit Anzahl Schulen (c), Partnerschulen (p) und LifeTeacher (l)
  data/plz.json      PLZ-Mittelpunkte für die Suche
"""
import csv
import json
import math
import os
import re
import sys
import unicodedata

from shapely.geometry import Point, shape, mapping
from shapely.prepared import prep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "data", "ref")
BACKEND = os.path.join(ROOT, ".cache", "backend.json")
KOORD = os.path.join(REF, "partner_koordinaten.json")

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


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower().replace("ß", "ss"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def clean_plz(z):
    z = re.sub(r"\s+", "", str(z or ""))
    return z if re.fullmatch(r"\d{5}", z) else None  # nur deutsche PLZ


def offset(coord, i):
    """Mehrere Schulen ohne eigene Position in einer PLZ: auf einem kleinen Kreis verteilen (ca. 300 m)."""
    if i == 0:
        return coord
    a = i * 2.39996  # goldener Winkel
    r = 0.0027 * math.sqrt(i)
    return (round(coord[0] + r * math.cos(a) / 0.62, 5), round(coord[1] + r * math.sin(a), 5))


def load_mymaps(src, plz):
    reg, partners = parse_import(src)
    out, missing = [], []
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
        out.append({"name": name, "ort": ort, "plz": pz, "coord": coord})
    return reg, out, {}, missing


def load_backend(plz):
    raw = json.load(open(BACKEND, encoding="utf-8"))
    try:
        known = json.load(open(KOORD, encoding="utf-8"))
    except (OSError, ValueError):
        known = {}
    # bisherige Positionen von der Karte, um neue IDs beim ersten Lauf zuzuordnen
    by_name, by_plz = {}, {}
    try:
        for f in json.load(open(os.path.join(ROOT, "data", "schulen.json"), encoding="utf-8"))["features"]:
            pr = f["properties"]
            if pr.get("t") == "p":
                c = tuple(f["geometry"]["coordinates"])
                by_name[norm(pr.get("n"))] = c
                by_plz.setdefault(pr.get("z"), []).append(c)
    except (OSError, ValueError, KeyError):
        pass

    reg, partners, missing, used, claimed = [], [], [], {}, {tuple(v) for v in known.values()}
    for s in sorted(raw["schools"], key=lambda s: (s.get("createdAt") or "", s.get("id") or "")):
        z = clean_plz(s.get("postalCode"))
        if not z:
            missing.append("PLZ %r" % s.get("postalCode"))
            continue
        if not s.get("verified"):
            reg.append(z)
            continue
        sid, name = s.get("id"), (s.get("title") or "").strip()
        coord = tuple(known[sid]) if sid in known else None
        if not coord:
            coord = by_name.get(norm(name))
            if coord in claimed:
                coord = None
            if not coord and len(by_plz.get(z, [])) == 1 and by_plz[z][0] not in claimed:
                coord = by_plz[z][0]
            if not coord and name in MANUELL:
                coord = MANUELL[name]
            if not coord:
                base = plz_coord(plz, z)
                if not base:
                    missing.append(name)
                    continue
                coord = offset(base, used.get(z, 0))
                while coord in claimed:  # Platz schon belegt
                    used[z] = used.get(z, 0) + 1
                    coord = offset(base, used[z])
                used[z] = used.get(z, 0) + 1
            claimed.add(coord)
        known[sid] = [round(coord[0], 5), round(coord[1], 5)]
        partners.append({"name": name, "ort": (s.get("city") or "").strip(), "plz": z, "coord": tuple(known[sid])})

    active = {s.get("id") for s in raw["schools"] if s.get("verified")}
    known = {k: v for k, v in sorted(known.items()) if k in active}
    json.dump(known, open(KOORD, "w", encoding="utf-8"), separators=(",", ":"))

    teachers = {}
    for k, v in (raw.get("teachers") or {}).items():
        z = clean_plz(k)
        if z and isinstance(v, int) and v > 0:
            teachers[z] = teachers.get(z, 0) + v
    return reg, partners, teachers, missing


def main(src):
    plz = load_plz()
    if src is None and os.path.exists(BACKEND):
        reg, partners, teachers, missing = load_backend(plz)
        print("Quelle: Backend")
    else:
        reg, partners, teachers, missing = load_mymaps(src or os.path.join(ROOT, "data", "import", "mymaps.txt"), plz)
        print("Quelle: mymaps.txt")

    feats = []
    seen = set()
    for p in partners:
        coord = p["coord"]
        key = (p["name"].lower(), round(coord[0], 3), round(coord[1], 3))
        if key in seen:  # doppelte Einträge
            continue
        seen.add(key)
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": list(coord)},
                      "properties": {"t": "p", "n": p["name"], "o": p["ort"], "z": p["plz"]}})

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
        polys.append({"g": g, "pg": prep(g), "name": name, "c": 0, "p": 0, "l": 0})

    def kreis(coord):
        pt = Point(coord)
        for k in polys:
            if k["pg"].contains(pt):
                return k
        return None

    for ft in feats:
        k = kreis(ft["geometry"]["coordinates"])
        if k:
            k["c"] += ft["properties"].get("k", 1)
            if ft["properties"]["t"] == "p":
                k["p"] += 1
    # LifeTeacher nur als Summe je Landkreis, nie je PLZ
    for z, n in teachers.items():
        c = plz_coord(plz, z)
        k = kreis(c) if c else None
        if k:
            k["l"] += n

    def rnd(geom):
        m = mapping(geom)

        def r(c):
            if isinstance(c[0], (list, tuple)):
                return [r(x) for x in c]
            return [round(c[0], 3), round(c[1], 3)]
        m["coordinates"] = r(m["coordinates"])
        return m

    kfeats = [{"type": "Feature", "geometry": rnd(k["g"]),
               "properties": {"n": k["name"], "c": k["c"], "p": k["p"], "l": k["l"]}} for k in polys]

    out = os.path.join(ROOT, "data")
    meta = {"partner": sum(1 for f in feats if f["properties"]["t"] == "p"), "registriert": sum(counts.values()),
            "lifeteacher": sum(k["l"] for k in polys)}
    json.dump({"type": "FeatureCollection", "meta": meta, "features": feats},
              open(os.path.join(out, "schulen.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"type": "FeatureCollection", "features": kfeats},
              open(os.path.join(out, "kreise.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({z: [c[0], c[1]] for z, c in sorted(plz.items())},
              open(os.path.join(out, "plz.json"), "w"), separators=(",", ":"))
    print("Partnerschulen:", meta["partner"], "| registriert:", meta["registriert"], "in", len(counts), "PLZ")
    print("ohne Ort:", missing)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
