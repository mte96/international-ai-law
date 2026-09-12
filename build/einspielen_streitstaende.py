#!/usr/bin/env python3
"""Spielt Streitstaende und Zuordnungen aus _research/ in kern.yaml ein.

    python3 build/einspielen_streitstaende.py _research/341_streitstaende_a.yaml

Erwartet `streitstaende` (neue) und `ergaenzungen` (Zuordnungen zu
bestehenden). Prueft JEDE id gegen den Bestand, bevor etwas geschrieben
wird - in einem Projekt, das gegen Halluzinationen anschreibt, ist die
erfundene id der peinlichste Fehler.
"""
import sys, glob, yaml
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(__doc__)
R = Path(__file__).resolve().parent.parent
q = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
KERN = R / "data/streitstaende/kern.yaml"
kern = yaml.safe_load(KERN.read_text(encoding="utf-8"))


def ids(muster, schluessel):
    s = set()
    for p in R.glob(muster):
        for e in (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get(schluessel) or []:
            if e.get("id"):
                s.add(e["id"])
    return s


U = ids("data/urteile/**/*.yaml", "urteile")
N = ids("data/normen/*.yaml", "normen")
L = ids("data/literatur/**/*.yaml", "literatur")
RW = ids("data/regelwerke/**/*.yaml", "regelwerke")
S = {s["id"] for s in kern["streitstaende"]}

fehler = []
for s in q.get("streitstaende") or []:
    if s["id"] in S:
        fehler.append(f"{s['id']}: gibt es schon")
    for p in s.get("positionen") or []:
        for u in p.get("urteile") or []:
            if u not in U:
                fehler.append(f"{s['id']} / {p.get('position')}: unbekanntes Urteil '{u}'")
    for feld, menge, name in (("normen", N, "Vorschrift"), ("bezug_literatur", L, "Titel"),
                              ("regelwerke", RW, "Regelwerk"),
                              ("bezug_streitstaende", S | {x["id"] for x in q.get("streitstaende") or []}, "Streitstand")):
        for x in s.get(feld) or []:
            if x not in menge:
                fehler.append(f"{s['id']}: unbekannte(s) {name} '{x}'")
    if len(s.get("positionen") or []) < 2:
        fehler.append(f"{s['id']}: weniger als zwei Positionen")

for e in q.get("ergaenzungen") or []:
    if e["id"] not in S:
        fehler.append(f"Ergaenzung: unbekannter Streitstand '{e['id']}'")
    for u in e.get("urteile") or []:
        if u not in U:
            fehler.append(f"Ergaenzung {e['id']}: unbekanntes Urteil '{u}'")

if fehler:
    print(f"{len(fehler)} Fehler - es wird nichts geschrieben:")
    for f in fehler[:30]:
        print("  ", f)
    sys.exit(1)

neu = 0
for s in q.get("streitstaende") or []:
    kern["streitstaende"].append(s)
    neu += 1

zug = pos_neu = 0
for e in q.get("ergaenzungen") or []:
    ziel = next(s for s in kern["streitstaende"] if s["id"] == e["id"])
    ziel.setdefault("positionen", [])
    treffer = next((p for p in ziel["positionen"] if p.get("position") == e.get("position")), None)
    if treffer is None:
        treffer = {"position": e.get("position"), "gericht": e.get("gericht", ""),
                   "begruendung": e.get("begruendung", ""), "urteile": []}
        ziel["positionen"].append(treffer)
        pos_neu += 1
    da = set(treffer.get("urteile") or [])
    for u in e.get("urteile") or []:
        if u not in da:
            treffer.setdefault("urteile", []).append(u)
            da.add(u); zug += 1
    ziel["letzte_pruefung"] = "2026-09-07"

KERN.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n"
                + yaml.dump(kern, allow_unicode=True, sort_keys=False, width=100,
                            default_flow_style=False), encoding="utf-8")
print(f"{neu} neue Streitstaende, {pos_neu} neue Positionen, {zug} Urteile zugeordnet")
