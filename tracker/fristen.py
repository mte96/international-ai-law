#!/usr/bin/env python3
"""Prueft die Fristen der Datenbasis und meldet, was in den Vorwarnzeitraum faellt.
Laeuft taeglich. Meldet eine Frist nur einmal je Vorwarnstufe."""
import json, sys
import datetime as dt
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
MERK = ROOT / "tracker" / "gemeldete_fristen.json"

fristen = []
for p in sorted((ROOT / "data" / "fristen").rglob("*.yaml")):
    d = yaml.safe_load(p.read_text()) or {}
    fristen += d.get("fristen") or []

gemeldet = json.loads(MERK.read_text()) if MERK.exists() else {}
heute = dt.date.today()
faellig = []

for f in fristen:
    try: datum = dt.date.fromisoformat(str(f["datum"])[:10])
    except Exception: continue
    tage = (datum - heute).days
    if tage < 0: continue
    for stufe in sorted(f.get("vorwarnung_tage") or [90, 30, 7], reverse=True):
        if tage <= stufe:
            marke = f"{f['id']}@{stufe}"
            if marke not in gemeldet:
                faellig.append((tage, stufe, f)); gemeldet[marke] = heute.isoformat()
            break

if "--trocken" not in sys.argv:
    MERK.write_text(json.dumps(gemeldet, ensure_ascii=False, indent=1))

if not faellig:
    print("Keine Frist im Vorwarnzeitraum."); sys.exit(0)

# Nach Restlaufzeit, dann Vorwarnstufe. Ohne key vergleicht sort bei
# gleichem Paar die Fristen selbst - und Woerterbuecher sind nicht
# vergleichbar. Das faellt erst auf, wenn zwei Fristen auf denselben Tag
# und dieselbe Stufe fallen.
faellig.sort(key=lambda e: (e[0], e[1]))
zeilen = [f"• in {t} Tagen ({str(f['datum'])[:10]}): {f.get('beschreibung','')[:110]}"
          for t, _, f in faellig]
titel = (f"Frist in {faellig[0][0]} Tagen" if len(faellig) == 1
         else f"{len(faellig)} Fristen — naechste in {faellig[0][0]} Tagen")
print(titel); print("\n".join(zeilen))

if "--trocken" not in sys.argv:
    sys.path.insert(0, str(ROOT / "tracker"))
    from notify import sende
    sende(titel, "\n".join(zeilen), tag="frist",
          prioritaet="hoch" if faellig[0][0] <= 7 else "normal")
