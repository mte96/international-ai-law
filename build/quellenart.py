#!/usr/bin/env python3
"""Zaehlt, worauf die Fundstellen der Entscheidungen zeigen.

Bis zum 17.09.2026 traf diese Datei die Einstufung selbst, ueber rund 250
regulaere Ausdruecke. Das ging zweimal schief: eine neu erfasste
Rechtsordnung hatte ihr Amtsblatt noch nicht in der Liste, und ein
amtlicher Link wurde entwertet. Umgekehrt zaehlten
`courtlistener.com/docket/`, `indiankanoon.org` und `canlii.org` als
amtlich - das sind Datenbanken, und 21 Entscheidungen standen deshalb mit
einer Fundstelle da, die keine ist.

Die Einstufung steht jetzt an einer Stelle: `build/quellenklasse.py`,
host-basiert statt mustergestuetzt. Diese Datei zaehlt nur noch.

Sie schreibt auch nichts mehr in `data/`. `quelle_art` ist kein
gepflegtes Feld, sondern eine Ableitung aus der Adresse - es wird beim
Bau erzeugt (`build/build.py`). Ein abgeleiteter Wert, der doppelt
gefuehrt wird, ist ein Wert, der irgendwann auseinanderlaeuft.
"""
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quellenklasse import klasse

ROOT = Path(__file__).resolve().parent.parent
REIHE = ("amtlich", "urheber", "datenbank", "sekundaer", "fehlt")


def zaehle(muster, feld):
    zaehler, liste = Counter(), []
    for p in sorted((ROOT / muster).parent.rglob(Path(muster).name)):
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        for schluessel in d:
            if not isinstance(d[schluessel], list):
                continue
            for e in d[schluessel]:
                if not isinstance(e, dict) or "id" not in e:
                    continue
                a = klasse(e.get(feld))
                zaehler[a] += 1
                if a in ("sekundaer", "datenbank"):
                    liste.append((a, e["id"], str(e.get(feld))))
    return zaehler, liste


def drucke(titel, zaehler):
    gesamt = sum(zaehler.values()) or 1
    print(f"\n{titel} ({gesamt})")
    for a in REIHE:
        if zaehler[a]:
            print(f"  {zaehler[a]:>4} ({zaehler[a]*100//gesamt:>2}%)  {a}")


if __name__ == "__main__":
    z, liste = zaehle("data/urteile/*.yaml", "volltext_url")
    drucke("Entscheidungen nach volltext_url", z)
    ohne = z["sekundaer"] + z["fehlt"] + z["datenbank"]
    print(f"\n{z['sekundaer'] + z['fehlt']} Entscheidungen ohne Fundstelle, "
          f"{z['datenbank']} nur ueber eine Datenbank - zusammen {ohne} ohne "
          f"amtlichen Volltext.")
    if liste and "--zeigen" in sys.argv:
        print()
        for a, i, u in liste[:40]:
            print(f"  {a:10s} {i:44s} {u[:70]}")
    # Exit 0 auch bei Befunden: das ist ein Bericht, kein Waechter.
    # Geprueft wird in schema/validate.py.
