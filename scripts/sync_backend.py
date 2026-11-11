"""Abgleich mit dem LifeTeachUs-Backend (nur lesend).

Liest zwei Endpunkte der Karten-API:
  $LTU_API_URL/map/schools   -> [{id, title, postalCode, city, verified, createdAt}]  alle aktiven Schulen
  $LTU_API_URL/map/teachers  -> {"<PLZ>": <Anzahl>}                                   aktive LifeTeacher je PLZ

Die Rohdaten landen in .cache/backend.json. Der Ordner wird nicht ins Repo übernommen:
Namen von Schulen ohne Vertrag und LifeTeacher-Zahlen je PLZ bleiben so privat.
scripts/build_data.py macht daraus die öffentlichen Kartendaten (Partnerschulen mit Namen,
alle anderen nur als PLZ-Gebiet, LifeTeacher nur als Summe je Landkreis).

Benötigt die Secrets LTU_API_URL und LTU_API_TOKEN (wird als x-api-key gesendet).
Ohne Secrets bleibt der bisherige Datenstand unverändert. Liefert das Backend einen Fehler
oder auffällig wenige Schulen, bricht der Abgleich ab und die Karte behält den letzten Stand.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = (os.environ.get("LTU_API_URL") or "").rstrip("/")
TOKEN = os.environ.get("LTU_API_TOKEN")
CACHE = os.path.join(ROOT, ".cache", "backend.json")


def get(path):
    req = urllib.request.Request(URL + path, headers={"x-api-key": TOKEN, "Accept": "application/json",
                                                      "User-Agent": "ltu-karte-abgleich"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def previous_partner_count():
    try:
        meta = json.load(open(os.path.join(ROOT, "data", "schulen.json"), encoding="utf-8")).get("meta", {})
        return int(meta.get("partner", 0))
    except (OSError, ValueError):
        return 0


def main():
    if not (URL and TOKEN):
        print("Kein Backend-Zugang hinterlegt, Datenstand bleibt unverändert.")
        return 0
    schools = get("/map/schools")
    teachers = get("/map/teachers")
    if not isinstance(schools, list) or not isinstance(teachers, dict):
        print("Unerwartetes Format vom Backend, Abgleich abgebrochen.")
        return 1
    partner = sum(1 for s in schools if s.get("verified"))
    before = previous_partner_count()
    if before and partner < before * 0.8:
        print("Backend liefert nur %d Partnerschulen (bisher %d), Abgleich abgebrochen." % (partner, before))
        return 1
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump({"schools": schools, "teachers": teachers}, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    print("Schulen aus dem Backend: %d (davon Partnerschulen: %d) | LifeTeacher: %d in %d PLZ"
          % (len(schools), partner, sum(v for v in teachers.values() if isinstance(v, int)), len(teachers)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
