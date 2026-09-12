#!/usr/bin/env python3
"""Spielt eine Recherchedatei aus _research/ in die Datenbasis ein.

    python3 build/einspielen.py _research/300_sea.yaml data/regelwerke/neuland/sea.yaml

Verteilt die Top-Level-Schluessel auf die vorgesehenen Dateien:
  regelwerke -> das als zweites Argument genannte Ziel
  normen     -> data/normen/verzeichnis.yaml
  urteile    -> data/urteile/<basis>.yaml
  fristen    -> data/fristen/<basis>.yaml
Bestehende ids werden nicht ueberschrieben, sondern gemeldet. Mehrfaches
Laufen schadet nicht.
"""
import sys, glob, yaml
from pathlib import Path

if len(sys.argv) < 3:
    sys.exit(__doc__)
R = Path(__file__).resolve().parent.parent
quelle = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
ziel_rw = R / sys.argv[2]
basis = ziel_rw.stem

KOPF = "# Gepflegte Datenbasis. Rohrecherche in _research/.\n"


def vorhandene_ids(muster, schluessel):
    ids = set()
    for p in (R).glob(muster):
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for e in d.get(schluessel) or []:
            if e.get("id"):
                ids.add(e["id"])
    return ids


def schreibe(pfad, schluessel, neu, bekannt):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    alt = yaml.safe_load(pfad.read_text(encoding="utf-8")) if pfad.exists() else None
    alt = alt or {}
    liste = alt.get(schluessel) or []
    da = {e.get("id") for e in liste}
    zugefuegt, doppelt = 0, []
    for e in neu:
        i = e.get("id")
        if not i:
            continue
        if i in da:
            doppelt.append(i)
            continue
        if i in bekannt:
            doppelt.append(i)
            continue
        liste.append(e)
        da.add(i)
        zugefuegt += 1
    alt[schluessel] = liste
    pfad.write_text(KOPF + yaml.dump(alt, allow_unicode=True, sort_keys=False,
                                     width=100, default_flow_style=False),
                    encoding="utf-8")
    return zugefuegt, doppelt


bericht = []
if quelle.get("regelwerke"):
    bekannt = vorhandene_ids("data/regelwerke/**/*.yaml", "regelwerke") - \
              vorhandene_ids(str(ziel_rw.relative_to(R)), "regelwerke")
    n, d = schreibe(ziel_rw, "regelwerke", quelle["regelwerke"], bekannt)
    bericht.append(f"{n} Regelwerke -> {ziel_rw.relative_to(R)}" +
                   (f"  ({len(d)} schon da: {', '.join(d[:6])})" if d else ""))

if quelle.get("normen"):
    p = R / "data/normen/verzeichnis.yaml"
    n, d = schreibe(p, "normen", quelle["normen"], set())
    bericht.append(f"{n} Vorschriften -> data/normen/verzeichnis.yaml" +
                   (f"  ({len(d)} schon da)" if d else ""))

if quelle.get("literatur"):
    # Literatur wird nach der ersten Themenachse abgelegt - so liegen die
    # Titel dort, wo man beim Arbeiten an einem Thema hinsieht.
    bekannt = vorhandene_ids("data/literatur/*.yaml", "literatur")
    nach_achse = {}
    for e in quelle["literatur"]:
        achsen = e.get("themenachsen") or ["governance"]
        nach_achse.setdefault(achsen[0], []).append(e)
    zug, dop = 0, 0
    for achse, titel in sorted(nach_achse.items()):
        pfad = R / f"data/literatur/{achse}.yaml"
        n, d = schreibe(pfad, "literatur", titel,
                        bekannt - vorhandene_ids(f"data/literatur/{achse}.yaml", "literatur"))
        zug += n
        dop += len(d)
    bericht.append(f"{zug} Titel -> data/literatur/ (nach Themenachse verteilt)" +
                   (f"  ({dop} schon da)" if dop else ""))

if quelle.get("urteile"):
    p = R / f"data/urteile/{basis}.yaml"
    bekannt = vorhandene_ids("data/urteile/*.yaml", "urteile") - \
              vorhandene_ids(f"data/urteile/{basis}.yaml", "urteile")
    n, d = schreibe(p, "urteile", quelle["urteile"], bekannt)
    bericht.append(f"{n} Entscheidungen -> data/urteile/{basis}.yaml" +
                   (f"  ({len(d)} schon da)" if d else ""))

if quelle.get("fristen"):
    p = R / f"data/fristen/{basis}.yaml"
    bekannt = vorhandene_ids("data/fristen/*.yaml", "fristen") - \
              vorhandene_ids(f"data/fristen/{basis}.yaml", "fristen")
    n, d = schreibe(p, "fristen", quelle["fristen"], bekannt)
    bericht.append(f"{n} Fristen -> data/fristen/{basis}.yaml" +
                   (f"  ({len(d)} schon da)" if d else ""))

print("\n".join(bericht))
