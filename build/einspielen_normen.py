#!/usr/bin/env python3
"""Spielt gefuellte Vorschriften aus _research/ in das Verzeichnis ein.

    python3 build/einspielen_normen.py _research/350_normen_eu.yaml

Setzt nur inhalt, amtlicher_text_url, jurisdiktion und via. id, regelwerk,
bezeichnung und thema bleiben unberuehrt - wer die aendern will, tut das
von Hand und mit Vermerk.
"""
import sys, yaml
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(__doc__)
R = Path(__file__).resolve().parent.parent
Z = R / "data/normen/verzeichnis.yaml"
ziel = yaml.safe_load(Z.read_text(encoding="utf-8"))
nach_id = {n["id"]: n for n in ziel["normen"]}

q = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
UEBERNEHMEN = ("inhalt", "amtlicher_text_url", "jurisdiktion", "via")
gesetzt = ueberschrieben = unbekannt = 0
fehlend = []
for n in q.get("normen") or []:
    z = nach_id.get(n.get("id"))
    if z is None:
        unbekannt += 1
        fehlend.append(n.get("id"))
        continue
    neu = False
    for k in UEBERNEHMEN:
        if n.get(k) in (None, "", []):
            continue
        if z.get(k) and z[k] != n[k]:
            ueberschrieben += 1
        if not z.get(k):
            neu = True
        z[k] = n[k]
    gesetzt += 1 if neu else 0

Z.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n"
             + yaml.dump(ziel, allow_unicode=True, sort_keys=False, width=100,
                         default_flow_style=False), encoding="utf-8")
mit = sum(1 for n in ziel["normen"] if n.get("inhalt"))
print(f"{gesetzt} Vorschriften ergaenzt, {ueberschrieben} Felder ueberschrieben, "
      f"{unbekannt} unbekannte ids")
if fehlend:
    print("  NICHT GEFUNDEN:", ", ".join(fehlend[:10]))
print(f"Bestand jetzt: {mit} von {len(ziel['normen'])} Vorschriften mit Inhalt "
      f"({100*mit//len(ziel['normen'])} %)")
