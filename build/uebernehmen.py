#!/usr/bin/env python3
"""Uebernimmt Aenderungen aus der veroeffentlichten Seite in die Datenbasis.

    python3 build/uebernehmen.py <artefakt.html> [--schreiben]

Der Montagslauf arbeitet an der veroeffentlichten Seite, nicht am Repo.
Ohne diesen Rueckweg laufen beide auseinander, und der naechste Bau aus
den YAML-Dateien wuerde seine Arbeit ueberschreiben.

Ohne --schreiben wird nur berichtet. Neue Eintraege landen in
data/<gattung>/montagslauf.yaml, geaenderte werden an Ort und Stelle
ergaenzt. Felder, die nur lokal stehen, bleiben unberuehrt.
"""
import sys, json, glob, yaml, datetime
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(__doc__)
R = Path(__file__).resolve().parent.parent
schreiben = "--schreiben" in sys.argv

h = Path(sys.argv[1]).read_text(encoding="utf-8")
i = h.index("window.__DATEN = ") + len("window.__DATEN = ")
A = json.loads(h[i:h.index("</script>", i)].rstrip().rstrip(";"))

GATTUNGEN = [
    ("regelwerke", "data/regelwerke/**/*.yaml", "data/regelwerke/montagslauf.yaml"),
    ("urteile",    "data/urteile/**/*.yaml",    "data/urteile/montagslauf.yaml"),
    ("literatur",  "data/literatur/**/*.yaml",  "data/literatur/montagslauf.yaml"),
    ("fristen",    "data/fristen/**/*.yaml",    "data/fristen/montagslauf.yaml"),
    ("streitstaende", "data/streitstaende/**/*.yaml", "data/streitstaende/montagslauf.yaml"),
    ("normen",     "data/normen/*.yaml",        "data/normen/montagslauf.yaml"),
]
# Felder, die der Bau erzeugt - die gehoeren nicht in die Datenbasis zurueck.
FLUECHTIG = {"_tage", "_titel", "_such", "quelle_art"}


def vergleichbar(x):
    if isinstance(x, (datetime.date, datetime.datetime)):
        return str(x)
    if isinstance(x, dict):
        return {k: vergleichbar(v) for k, v in x.items()}
    if isinstance(x, list):
        return [vergleichbar(v) for v in x]
    return x


gesamt_neu = gesamt_geaendert = 0
for gattung, muster, neuablage in GATTUNGEN:
    # Wo steht welcher Eintrag?
    heimat, lokal = {}, {}
    for p in sorted((R).glob(muster.replace("data/", "data/"))):
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for e in d.get(gattung) or []:
            if e.get("id"):
                heimat[e["id"]] = p
                lokal[e["id"]] = e
    kunst = {e["id"]: e for e in A.get(gattung) or [] if e.get("id")}

    neu = [i2 for i2 in kunst if i2 not in lokal]
    aenderungen = {}          # pfad -> {id -> {feld: wert}}
    for i2, a in kunst.items():
        if i2 not in lokal:
            continue
        l = vergleichbar(lokal[i2])
        diff = {k: v for k, v in a.items()
                if k not in FLUECHTIG and not k.startswith("_") and v != l.get(k)}
        if diff:
            aenderungen.setdefault(heimat[i2], {})[i2] = diff

    n_geaendert = sum(len(v) for v in aenderungen.values())
    if not neu and not n_geaendert:
        continue
    print(f"\n=== {gattung}: {len(neu)} neu, {n_geaendert} geaendert")
    for i2 in neu:
        print(f"   NEU  {i2}")
    for pfad, eintraege in sorted(aenderungen.items()):
        for i2, diff in sorted(eintraege.items()):
            print(f"   AEND {i2:44} {', '.join(sorted(diff))[:80]}")
    gesamt_neu += len(neu)
    gesamt_geaendert += n_geaendert

    if not schreiben:
        continue

    for pfad, eintraege in aenderungen.items():
        d = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
        for e in d.get(gattung) or []:
            if e.get("id") in eintraege:
                e.update(eintraege[e["id"]])
        pfad.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n"
                        + yaml.dump(d, allow_unicode=True, sort_keys=False,
                                    width=100, default_flow_style=False),
                        encoding="utf-8")
    if neu:
        p = R / neuablage
        d = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
        d = d or {}
        d.setdefault(gattung, []).extend(kunst[i2] for i2 in neu)
        p.write_text("# Aus dem Montagslauf uebernommen (build/uebernehmen.py).\n"
                     + yaml.dump(d, allow_unicode=True, sort_keys=False,
                                 width=100, default_flow_style=False),
                     encoding="utf-8")

print(f"\n{gesamt_neu} neue, {gesamt_geaendert} geaenderte Eintraege"
      + ("" if schreiben else "  (nur Bericht - mit --schreiben uebernehmen)"))
