#!/usr/bin/env python3
"""Spielt eine Inkrafttretens-Recherche aus _research/ in die Datenbasis ein.

    python3 build/einspielen_inkrafttreten.py _research/220_inkrafttreten_latam.yaml

Erwartet den Schluessel `aenderungen` mit Eintraegen der Form
{id, inkrafttreten, status?, anwendungsdaten?, pruefvermerk?, alter_wert?}
sowie optional `nicht_belegt`. Setzt nur, was dasteht; alles Weitere bleibt.
Laeuft mehrfach ohne Schaden - schon eingespielte Vermerke werden nicht
doppelt angehaengt.
"""
import sys, glob, yaml
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(__doc__)
R = Path(__file__).resolve().parent.parent
quelle = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
aend = {a["id"]: a for a in (quelle.get("aenderungen") or [])}
offen = quelle.get("nicht_belegt") or []

gesetzt, status_geaendert, vermerkt, unbekannt = 0, 0, 0, set(aend)
for p in sorted((R / "data/regelwerke").rglob("*.yaml")):
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    dirty = False
    for r in d.get("regelwerke") or []:
        a = aend.get(r["id"])
        if not a:
            continue
        unbekannt.discard(r["id"])
        if "inkrafttreten" in a:
            r["inkrafttreten"] = a["inkrafttreten"]
            gesetzt += 1
        if a.get("status") and a["status"] != r.get("status"):
            r["status"] = a["status"]
            status_geaendert += 1
        if a.get("anwendungsdaten"):
            r["anwendungsdaten"] = a["anwendungsdaten"]
        if a.get("pruefvermerk"):
            vor = r.get("pruefvermerk") or []
            if not isinstance(vor, list):
                vor = [vor]
            text = a["pruefvermerk"]
            if a.get("alter_wert"):
                text += f" Vorher: {a['alter_wert']}."
            if text not in vor:
                vor.append(text)
                vermerkt += 1
            r["pruefvermerk"] = vor
        dirty = True
    if dirty:
        p.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n"
                     + yaml.dump(d, allow_unicode=True, sort_keys=False, width=100,
                                 default_flow_style=False), encoding="utf-8")

# Was nicht belegt werden konnte, bleibt als offener Punkt am Eintrag stehen
for p in sorted((R / "data/regelwerke").rglob("*.yaml")):
    d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    dirty = False
    for r in d.get("regelwerke") or []:
        for o in offen:
            if o.get("id") != r["id"]:
                continue
            vor = r.get("offene_punkte") or []
            if not isinstance(vor, list):
                vor = [vor]
            text = f"Inkrafttreten nicht belegbar: {o.get('versucht', '')}"
            if text not in vor:
                vor.append(text)
                r["offene_punkte"] = vor
                dirty = True
    if dirty:
        p.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n"
                     + yaml.dump(d, allow_unicode=True, sort_keys=False, width=100,
                                 default_flow_style=False), encoding="utf-8")

print(f"{gesetzt} Inkrafttretensdaten gesetzt, {status_geaendert} Status geaendert, "
      f"{vermerkt} Pruefvermerke, {len(offen)} offene Punkte notiert")
if unbekannt:
    print("NICHT GEFUNDEN:", ", ".join(sorted(unbekannt)))
