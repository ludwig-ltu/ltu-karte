"""Nächtlicher Abgleich mit dem LifeTeachUs-Backend (nur lesend).

Liest Schulen (PLZ, Ort, Name nur bei Vertrag, Vertragsstatus) aus dem Backend und schreibt
data/import/mymaps.txt im selben Format wie der bisherige Export. Danach baut
scripts/build_data.py die Kartendaten neu.

Benötigt die Secrets LTU_API_URL und LTU_API_TOKEN (technischer Zugang, nur Lesezugriff).
Ohne diese Secrets bleibt der bisherige Datenstand unverändert.
"""
import json
import os
import sys
import urllib.request

URL = os.environ.get("LTU_API_URL")
TOKEN = os.environ.get("LTU_API_TOKEN")
QUERY = os.environ.get("LTU_SCHOOLS_QUERY")  # GraphQL-Abfrage, wird beim Anschluss festgelegt


def main():
    if not (URL and TOKEN and QUERY):
        print("Kein Backend-Zugang hinterlegt, Datenstand bleibt unverändert.")
        return 0
    req = urllib.request.Request(URL, data=json.dumps({"query": QUERY}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN})
    data = json.load(urllib.request.urlopen(req, timeout=60))["data"]
    schools = data["schools"]
    reg = sorted({s["zip"] for s in schools if not s.get("contract")})
    lines = ["P " + " ".join(reg)]
    for s in schools:
        if s.get("contract"):
            lines.append("S|%s|%s|" % (s["name"], "%s %s" % (s["zip"], s.get("city", ""))))
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "import", "mymaps.txt")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("Schulen aus dem Backend:", len(schools))
    return 0


if __name__ == "__main__":
    sys.exit(main())
