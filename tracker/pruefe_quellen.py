#!/usr/bin/env python3
"""Ruft jede aktive Quelle einmal an und schreibt einen Zustandsbericht.
Eine Quelle, die nichts mehr liefert, faellt sonst nie auf - sie meldet
einfach nie wieder etwas, und das sieht aus wie Ruhe.

Mit --alle werden auch abgeschaltete Quellen angerufen. Das ist der Weg,
um Kandidaten zu erproben: Eintrag mit aktiv: false anlegen, hier laufen
lassen, und nur die auf aktiv: true setzen, die Eintraege liefern.
Gemeldet wird trotzdem nur, was unter den AKTIVEN auffaellig ist."""
import sys, time
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
from watch import hole, parse_auto

ROOT = Path(__file__).resolve().parent.parent
konf = yaml.safe_load((ROOT / "tracker/quellen.yaml").read_text())
zeilen, kaputt = [], []
alle = "--alle" in sys.argv
liste = konf["quellen"] if alle else [x for x in konf["quellen"] if x.get("aktiv")]

for q in liste:
    t0 = time.time()
    try:
        text = hole(q["feed_url"], timeout=20)
        items = parse_auto(text, q["format"], q["feed_url"])
        n = len(items) if items else 0
        stand = "ok" if n else "LEER"
        if not n and q.get("aktiv"): kaputt.append(f"{q['id']} (0 Einträge)")
    except Exception as e:
        n, stand = 0, f"FEHLER {type(e).__name__}"
        if q.get("aktiv"): kaputt.append(f"{q['id']} ({type(e).__name__})")
    an = "aktiv" if q.get("aktiv") else "aus"
    zeilen.append(f"| {q['id']} | {q['jurisdiktion']} | {q['format']} | {an} | {stand} | {n} | {time.time()-t0:.1f}s |")

n_aktiv = sum(1 for x in liste if x.get("aktiv"))
bericht = ["# Quellenbericht", f"\nStand: {time.strftime('%Y-%m-%d')}",
           f"\n{len(zeilen)} Quellen angerufen ({n_aktiv} aktiv), "
           f"davon {len(kaputt)} aktive auffällig.\n",
           "| Quelle | Jur. | Format | Schalter | Zustand | Einträge | Dauer |",
           "|---|---|---|---|---|---|---|"] + zeilen
(ROOT / "tracker/quellenbericht.md").write_text("\n".join(bericht) + "\n")
print("\n".join(bericht[:6]))

if kaputt:
    from notify import sende
    sende(f"{len(kaputt)} Quellen auffällig",
          "\n".join(f"• {k}" for k in kaputt[:15]), tag="quellen", prioritaet="normal")
