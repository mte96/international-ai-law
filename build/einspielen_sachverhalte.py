#!/usr/bin/env python3
"""Spielt Sachverhalte aus _research/ in die Entscheidungen ein.

    python3 build/einspielen_sachverhalte.py _research/360_sachverhalte.yaml

Setzt nur `sachverhalt` und `sachverhalt_quelle`. Alles andere bleibt.
Ueberschreibt einen vorhandenen Sachverhalt nicht.
"""
import sys, yaml
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(__doc__)
R = Path(__file__).resolve().parent.parent
q = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
neu = {u["id"]: u for u in q.get("urteile") or [] if u.get("sachverhalt")}

gesetzt = schon = unbekannt = 0
offen = set(neu)
for p in sorted((R / "data/urteile").glob("*.yaml")):
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    dirty = False
    for u in d.get("urteile") or []:
        n = neu.get(u.get("id"))
        if not n:
            continue
        offen.discard(u["id"])
        if u.get("sachverhalt"):
            schon += 1
            continue
        u["sachverhalt"] = n["sachverhalt"]
        if n.get("sachverhalt_quelle"):
            u["sachverhalt_quelle"] = n["sachverhalt_quelle"]
        gesetzt += 1
        dirty = True
    if dirty:
        p.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n"
                     + yaml.dump(d, allow_unicode=True, sort_keys=False, width=100,
                                 default_flow_style=False), encoding="utf-8")
print(f"{gesetzt} Sachverhalte gesetzt, {schon} schon vorhanden, {len(offen)} ids unbekannt")
if offen:
    print("  NICHT GEFUNDEN:", ", ".join(sorted(offen)[:8]))
