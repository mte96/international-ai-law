#!/usr/bin/env python3
"""Spielt gepruefte Feldkorrekturen ein - aber nur, wenn der alte Wert passt.

    python3 build/einspielen_korrekturen.py _korrekturen/uk_a.yaml [...]
    python3 build/einspielen_korrekturen.py --pruefen _korrekturen/*.yaml

Format der Korrekturdatei:

    korrekturen:
      - datei: data/normen/verzeichnis.yaml
        gattung: normen            # der oberste Schluessel in der Zieldatei
        id: uk-osa-2023-s-143
        feld: thema
        alt: 'der Text, der jetzt dort steht'
        neu: 'der berichtigte Text'
        grund: 'warum'

Steht in `neu` das Wort __LOESCHEN__, wird das Listenelement entfernt statt
ersetzt. Das geht nur bei Listen - ein Skalarfeld auf leer zu setzen waere
ein anderer Eingriff und muss von Hand geschehen.

Der Sinn liegt im Feld `alt`: Trifft es den derzeitigen Wert nicht Zeichen
fuer Zeichen, wird NICHTS geschrieben. So kann eine Korrektur nicht auf
einen Bestand laufen, der sich seit ihrer Erarbeitung geaendert hat, und
kein Agent kann versehentlich etwas anderes ueberschreiben als das, was er
gelesen hat. Ist `feld` eine Liste, wird das Element ersetzt, das `alt`
exakt entspricht - kommt es dort mehr als einmal vor, ist das ein Fehler.
"""
import sys, yaml, datetime
from pathlib import Path
from collections import defaultdict

argv = [a for a in sys.argv[1:] if not a.startswith("--")]
nur_pruefen = "--pruefen" in sys.argv
if not argv:
    sys.exit(__doc__)

R = Path(__file__).resolve().parent.parent
korrekturen = []
for p in argv:
    d = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or {}
    for k in d.get("korrekturen") or []:
        k["_quelle"] = Path(p).name
        korrekturen.append(k)

PFLICHT = ("datei", "gattung", "id", "feld", "alt", "neu", "grund")
fehler, treffer = [], []
geladen = {}

for k in korrekturen:
    fehlt = [f for f in PFLICHT if not str(k.get(f, "")).strip()]
    if fehlt:
        fehler.append(f"{k.get('_quelle')}/{k.get('id')}: Pflichtfelder fehlen: {fehlt}"); continue
    if k["neu"] == "__LOESCHEN__" and not isinstance(
            (next((e for e in (geladen.get(k["datei"]) or {}).get(k["gattung"], [])
                   if isinstance(e, dict) and e.get("id") == k["id"]), {}) or {}).get(k["feld"]), list):
        pass  # Pruefung folgt weiter unten, wenn der Wert geladen ist
    if k["alt"] == k["neu"]:
        fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: alt und neu sind gleich"); continue

    datei = R / k["datei"]
    if not datei.exists():
        fehler.append(f"{k['_quelle']}/{k['id']}: Datei fehlt: {k['datei']}"); continue
    if k["datei"] not in geladen:
        geladen[k["datei"]] = yaml.safe_load(datei.read_text(encoding="utf-8"))
    doc = geladen[k["datei"]]
    if k["gattung"] not in doc:
        fehler.append(f"{k['_quelle']}/{k['id']}: Gattung '{k['gattung']}' nicht in {k['datei']}"); continue

    eintrag = next((e for e in doc[k["gattung"]] if isinstance(e, dict) and e.get("id") == k["id"]), None)
    if eintrag is None:
        fehler.append(f"{k['_quelle']}/{k['id']}: id nicht gefunden"); continue
    if k["feld"] not in eintrag:
        fehler.append(f"{k['_quelle']}/{k['id']}: Feld '{k['feld']}' nicht vorhanden"); continue

    wert = eintrag[k["feld"]]
    if isinstance(wert, (datetime.date, datetime.datetime)):
        # Datumsfelder: alt und neu stehen als ISO-Zeichenkette in der Patchdatei.
        if str(wert)[:10] != str(k["alt"])[:10]:
            fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: alt trifft nicht "
                          f"(dort {wert}, erwartet {k['alt']})"); continue
        try:
            neu_datum = datetime.date.fromisoformat(str(k["neu"])[:10])
        except ValueError:
            fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: neu ist kein ISO-Datum"); continue
        treffer.append((k, eintrag, "datum", neu_datum))
    elif isinstance(wert, list):
        n = sum(1 for x in wert if x == k["alt"])
        if n == 0:
            fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: alt steht nicht in der Liste"); continue
        if n > 1:
            fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: alt steht {n}x in der Liste"); continue
        treffer.append((k, eintrag, wert.index(k["alt"]),
                        "loeschen" if k["neu"] == "__LOESCHEN__" else None))
    elif isinstance(wert, str):
        if k["neu"] == "__LOESCHEN__":
            fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: __LOESCHEN__ geht nur bei Listen"); continue
        if wert != k["alt"]:
            fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: alt trifft nicht "
                          f"(dort {len(wert)} Zeichen, erwartet {len(k['alt'])})"); continue
        treffer.append((k, eintrag, None, None))
    else:
        fehler.append(f"{k['_quelle']}/{k['id']}.{k['feld']}: Feldtyp {type(wert).__name__}"); continue

print(f"{len(korrekturen)} Korrekturen gelesen, {len(treffer)} treffen, {len(fehler)} Fehler")
for f in fehler: print(f"  FEHLER  {f}")
if fehler:
    print("\nEs wird nichts geschrieben. Erst die Fehler beheben.")
    sys.exit(1)
if nur_pruefen:
    print("\nNur Pruefung - es wird nichts geschrieben.")
    sys.exit(0)

# Reihenfolge ist hier nicht gleichgueltig: pop() verschiebt jede spaetere
# Position derselben Liste um eins. Deshalb erst alle Ersetzungen, dann die
# Loeschungen, und diese von hinten nach vorn. Ohne das schreibt eine
# Korrektur nach einer Loeschung in den falschen Slot und ueberschreibt ein
# unbeteiligtes Nachbarelement - der Validator merkt es nicht, weil er nur
# ids prueft.
for k, eintrag, idx, ersatz in treffer:
    if ersatz == "loeschen":
        continue
    if idx == "datum": eintrag[k["feld"]] = ersatz
    elif idx is None:  eintrag[k["feld"]] = k["neu"]
    else:              eintrag[k["feld"]][idx] = k["neu"]

for k, eintrag, idx, ersatz in sorted(
        [x for x in treffer if x[3] == "loeschen"],
        key=lambda x: x[2], reverse=True):
    eintrag[k["feld"]].pop(idx)

# Vor dem Schreiben: Zahl der Eintraege und die ids muessen unveraendert sein.
for pfad, doc in geladen.items():
    alt_doc = yaml.safe_load((R / pfad).read_text(encoding="utf-8"))
    for gattung in doc:
        a, b = alt_doc.get(gattung), doc.get(gattung)
        if isinstance(a, list) and isinstance(b, list):
            ia = [e.get("id") for e in a if isinstance(e, dict)]
            ib = [e.get("id") for e in b if isinstance(e, dict)]
            if ia != ib:
                sys.exit(f"ABBRUCH: ids in {pfad}/{gattung} haben sich geaendert - nichts geschrieben.")
    (R / pfad).write_text(yaml.dump(doc, allow_unicode=True, sort_keys=False,
                                    width=100, default_flow_style=False), encoding="utf-8")
    print(f"  geschrieben: {pfad}")

nach = defaultdict(int)
for k, *_ in treffer: nach[f"{k['datei']} .{k['feld']}"] += 1
print()
for k, v in sorted(nach.items()): print(f"  {v:>3}x  {k}")
