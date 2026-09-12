#!/usr/bin/env python3
"""Prueft die Datenbasis gegen Taxonomie und Schema.
Laeuft in der CI und lokal vor jedem Commit."""
import collections
import sys, glob, datetime, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
tax = yaml.safe_load((ROOT / "schema/taxonomie.yaml").read_text())

JUR = {j["id"] for j in tax["jurisdiktionen"]}
SUB = {s["id"] for s in tax["subjurisdiktionen"]}
THEMEN = {t["id"] for t in tax["themenachsen"]}
STATUS_R = {s["id"] for s in tax["statuswerte"]["regelwerk"]}
STATUS_V = {s["id"] for s in tax["statuswerte"]["verfahren"]}
LIT_TYP = {s["id"] for s in tax["literatur"]["typen"]}
LIT_PRIO = {s["id"] for s in tax["literatur"]["prioritaeten"]}
LIT_ZUGANG = {s["id"] for s in tax["literatur"]["zugang"]}
DOKTYP = {d["id"] for d in tax["dokumenttypen"]}
KONTINENTE = {k["id"] for k in tax["kontinente"]}

# Jede Rechtsordnung braucht einen Kontinent: die Auswahl in der App ist
# danach gegliedert. Ohne Zuordnung faellt sie aus jeder Gruppe heraus und
# ist nicht mehr waehlbar - ein Feld ohne Pruefung laeuft irgendwann mit
# einem falschen Wert ein und niemand merkt es.
_tax_fehler = []
for _j in tax["jurisdiktionen"]:
    _k = _j.get("kontinent")
    if not _k:
        _tax_fehler.append(f"taxonomie: '{_j['id']}' ohne kontinent")
    elif _k not in KONTINENTE:
        _tax_fehler.append(f"taxonomie: '{_j['id']}' hat unbekannten kontinent '{_k}'")

# --- Commit-Kennungen in den Workflows -------------------------------
# In der alten GitHub-Schreibweise <name>@users.noreply.github.com liest
# GitHub den <name> als Kontonamen und schreibt den Commit diesem Konto zu.
# Eine frei gewaehlte Kennung landet damit bei einem echten, fremden Menschen
# - genau das ist hier passiert. Erlaubt ist nur die numerische Adresse des
# Actions-Bots oder eine, die mit der eigenen Kontonummer beginnt.
_ERLAUBT = re.compile(r"^\d+\+[\w\[\]-]+@users\.noreply\.github\.com$")
for _wf in sorted(glob.glob(str(ROOT / ".github/workflows/*.yml"))):
    for _nr, _z in enumerate(Path(_wf).read_text().split("\n"), 1):
        for _adr in re.findall(r"[\w.+\[\]-]+@users\.noreply\.github\.com", _z):
            if not _ERLAUBT.match(_adr):
                _tax_fehler.append(
                    f"{Path(_wf).name}:{_nr}: Commit-Kennung '{_adr}' ist keine "
                    f"numerische Noreply-Adresse - sie wird einem fremden Konto "
                    f"zugeordnet. Erlaubt: <id>+<name>@users.noreply.github.com")

fehler, warnungen, offen = list(_tax_fehler), [], {}
ids_gesehen = {}

def lade(muster):
    for pfad in sorted(glob.glob(str(ROOT / muster), recursive=True)):
        try:
            doc = yaml.safe_load(Path(pfad).read_text())
        except yaml.YAMLError as e:
            fehler.append(f"{pfad}: YAML nicht lesbar - {e}")
            continue
        if doc:
            yield pfad, doc

def pruefe_id(pfad, eid):
    if not eid:
        fehler.append(f"{pfad}: Eintrag ohne id")
    elif eid in ids_gesehen:
        fehler.append(f"{pfad}: id '{eid}' doppelt (auch in {ids_gesehen[eid]})")
    else:
        ids_gesehen[eid] = pfad

for pfad, doc in lade("data/regelwerke/**/*.yaml"):
    for rw in doc.get("regelwerke", []):
        pruefe_id(pfad, rw.get("id"))
        n = rw.get("id", "?")
        if rw.get("jurisdiktion") not in JUR:
            fehler.append(f"{n}: unbekannte jurisdiktion '{rw.get('jurisdiktion')}'")
        if rw.get("subjurisdiktion") and rw["subjurisdiktion"] not in SUB:
            fehler.append(f"{n}: unbekannte subjurisdiktion '{rw['subjurisdiktion']}'")
        if rw.get("status") not in STATUS_R:
            fehler.append(f"{n}: unbekannter status '{rw.get('status')}'")
        for t in rw.get("themenachsen") or []:
            if t not in THEMEN:
                fehler.append(f"{n}: unbekannte themenachse '{t}'")
        if not rw.get("themenachsen"):
            warnungen.append(f"{n}: keine themenachse gesetzt")
        for d in rw.get("dokumente") or []:
            if d.get("typ") and d["typ"] not in DOKTYP:
                warnungen.append(f"{n}: unbekannter dokumenttyp '{d['typ']}'")
            if not d.get("url"):
                warnungen.append(f"{n}: Dokument '{str(d.get('titel'))[:40]}' ohne url")

for pfad, doc in lade("data/urteile/**/*.yaml"):
    for u in doc.get("urteile", []):
        pruefe_id(pfad, u.get("id"))
        n = u.get("id", "?")
        if u.get("jurisdiktion") not in JUR:
            fehler.append(f"{n}: unbekannte jurisdiktion '{u.get('jurisdiktion')}'")
        if u.get("status") not in STATUS_V:
            fehler.append(f"{n}: unbekannter verfahrensstatus '{u.get('status')}'")
        for t in u.get("themenachsen") or []:
            if t not in THEMEN:
                fehler.append(f"{n}: unbekannte themenachse '{t}'")

for pfad, doc in lade("data/literatur/**/*.yaml"):
    for l in doc.get("literatur", []):
        pruefe_id(pfad, l.get("id"))
        # Bisher ungeprueft - dabei sind hier zwei unbekannte Werte
        # eingelaufen, ohne dass die Pruefung etwas gesagt haette.
        for j in l.get("jurisdiktionen") or []:
            if j not in JUR:
                fehler.append(f"{l.get('id')}: unbekannte jurisdiktion '{j}'")
        # Typ, Vorrang und Zugang waren ungeprueft. Dabei liefen zwei
        # Vorrangskalen parallel und 'monografie' neben 'monographie'.
        for feld, erlaubt in (("typ", LIT_TYP), ("prioritaet", LIT_PRIO),
                              ("zugang", LIT_ZUGANG)):
            wert = l.get(feld)
            if wert is not None and wert not in erlaubt:
                fehler.append(f"{l.get('id')}: unbekannter {feld} '{wert}'")

for pfad, doc in lade("data/streitstaende/**/*.yaml"):
    for s in doc.get("streitstaende", []):
        pruefe_id(pfad, s.get("id"))
        n = s.get("id", "?")
        for j in s.get("jurisdiktionen") or []:
            if j not in JUR: fehler.append(f"{n}: unbekannte jurisdiktion '{j}'")
        for t in s.get("themenachsen") or []:
            if t not in THEMEN: fehler.append(f"{n}: unbekannte themenachse '{t}'")
        if len(s.get("positionen") or []) < 1:
            warnungen.append(f"{n}: keine Position erfasst")

for pfad, doc in lade("data/weltraster/**/*.yaml"):
    for l in doc.get("laender", []):
        if l.get("einstufung") not in ("erfasst","pflicht","beobachten","nachrangig"):
            fehler.append(f"{l.get('land')}: unbekannte einstufung '{l.get('einstufung')}'")
        if l.get("status") not in ("gesetz","entwurf","strategie","nichts", None):
            fehler.append(f"{l.get('land')}: unbekannter status '{l.get('status')}'")

for pfad, doc in lade("data/lernen/**/*.yaml"):
    for a in doc.get("angebote", []):
        pruefe_id(pfad, a.get("id"))
    for q in doc.get("curriculum", []):
        pruefe_id(pfad, q.get("id"))
    for n in doc.get("nebenstraenge", []):
        pruefe_id(pfad, n.get("id"))

heute = datetime.date.today()
for pfad, doc in lade("data/fristen/**/*.yaml"):
    for f in doc.get("fristen", []):
        pruefe_id(pfad, f.get("id"))
        d = f.get("datum")
        if isinstance(d, datetime.date) and d < heute and f.get("handlungsbedarf"):
            warnungen.append(f"{f.get('id')}: Frist abgelaufen, Handlungsbedarf noch gesetzt")

# Streitstand-Belege muessen auf erfasste Entscheidungen zeigen
alle = set(ids_gesehen)
for pfad, doc in lade("data/lernen/**/*.yaml"):
    for q in doc.get("curriculum", []):
        for x in (q.get("lektuere") or []) + (q.get("angebote") or []):
            if x not in alle:
                fehler.append(f"{q['id']}: Verweis '{x}' existiert nicht")

for pfad, doc in lade("data/streitstaende/**/*.yaml"):
    for s in doc.get("streitstaende", []):
        for pos in s.get("positionen") or []:
            for u in pos.get("urteile") or []:
                if u not in alle:
                    fehler.append(f"{s['id']}: Beleg '{u}' ist keine erfasste Entscheidung")

# Normebene: Jede Vorschrift muss zu einem erfassten Regelwerk gehoeren,
# und jeder Verweis auf eine Vorschrift muss ins Verzeichnis treffen.
normen_ids = set()
for pfad, doc in lade("data/normen/*.yaml"):
    for n in doc.get("normen", []):
        pruefe_id(pfad, n.get("id"))
        normen_ids.add(n.get("id"))
        if n.get("regelwerk") and n["regelwerk"] not in ids_gesehen:
            fehler.append(f"{n.get('id')}: gehoert zu unbekanntem Regelwerk "
                          f"'{n['regelwerk']}'")
        if not n.get("bezeichnung"):
            warnungen.append(f"{n.get('id')}: ohne bezeichnung")

alle = set(ids_gesehen)
for pfad, doc in lade("data/**/*.yaml"):
    for schluessel in ("regelwerke", "urteile", "literatur", "streitstaende"):
        for e in doc.get(schluessel, []):
            for ref in e.get("normen") or []:
                if ref not in normen_ids:
                    fehler.append(f"{e.get('id')}: normen verweist auf unbekannte "
                                  f"Vorschrift '{ref}'")

for pfad, doc in lade("data/**/*.yaml"):
    for schluessel in ("regelwerke", "urteile", "literatur"):
        for e in doc.get(schluessel, []):
            for feld in ("bezug_urteile", "instanzenzug"):
                for ref in e.get(feld) or []:
                    if ref not in alle:
                        fehler.append(f"{e.get('id')}: {feld} verweist auf unbekannte id '{ref}'")
            # bezug_regelwerke darf auf Regelwerke zeigen, die noch nicht erfasst
            # sind - das ist der Arbeitsvorrat, kein Mangel.
            for ref in e.get("bezug_regelwerke") or []:
                if ref not in alle:
                    offen[ref] = offen.get(ref, 0) + 1

print(f"{len(ids_gesehen)} Einträge geprüft.")
from collections import Counter
# --- Felder gegen das Schema pruefen ------------------------------------
# Das Schema hinkte den Daten wochenlang hinterher: 60 benutzte Felder waren
# nicht beschrieben. Folge war unbemerkter Drift - sieben Streitstaende
# trugen `aufloesungsprognose`, die App liest `aufloesung`, also blieb die
# Prognose unsichtbar. Ein neues Feld ist nicht verboten; es soll nur nicht
# unbemerkt bleiben. Ein Durchgang ueber alle Dateien, nicht sechs.
_schema = yaml.safe_load(open("schema/schema.yaml", encoding="utf-8"))
_GATT = {"regelwerke": "regelwerk", "urteile": "urteil", "literatur": "literatur",
         "fristen": "frist", "streitstaende": "streitstand", "normen": "norm"}
_bekannt = {s: set((_schema.get(g) or {}).get("felder") or {}) for s, g in _GATT.items()}
_neu = {s: collections.Counter() for s in _GATT}
for _pfad, _doc in lade("data/**/*.yaml"):
    for _schluessel, _felder in _bekannt.items():
        if not _felder:
            continue
        for _e in _doc.get(_schluessel) or []:
            for _k in _e:
                if _k not in _felder:
                    _neu[_schluessel][_k] += 1
for _schluessel, _c in _neu.items():
    for _k, _n in _c.most_common():
        warnungen.append(f"{_schluessel}: Feld '{_k}' steht nicht im Schema ({_n}x) "
                         f"- eintragen in schema/schema.yaml oder umbenennen")

# Normadressen: das Feld heisst amtlicher_text_url. Wo eine Datenbank
# drinsteht, ist das kein Fehler, aber es soll sichtbar bleiben.
import sys as _sys
_sys.path.insert(0, "build")
from quellenart import art as _art
_db = [n for _p, _d in lade("data/normen/*.yaml") for n in _d.get("normen") or []
       if n.get("amtlicher_text_url") and _art(n["amtlicher_text_url"]) != "amtlich"]
if _db:
    warnungen.append(f"normen: {len(_db)} Eintraege fuehren unter amtlicher_text_url "
                     f"eine Datenbank statt der Urschrift - fuer eine Veroeffentlichung "
                     f"ist die amtliche Fassung heranzuziehen")

# --- Korrekturgeschichte in Anzeigefeldern --------------------------------
# In der App soll stehen, was gilt - nicht, wie es dorthin gekommen ist.
# "DATUM KORRIGIERT (bisher 08.08.2026)" ist eine Notiz der Pflege und
# gehoert nicht in einen Text, den ein Leser sieht; in fristen.beschreibung
# landet sie sogar im Kalender. Was offen ist, gehoert in offene_punkte,
# was einmal falsch war, nirgendwohin.
import re as _re
_ANZEIGE = {"kurzbeschreibung", "regelungsschwerpunkte", "offene_punkte", "status_detail",
            "eigene_bewertung", "bedeutung_eu_anbieter", "beschreibung", "handlungsbedarf",
            "ergebnis", "leitsatz", "sachverhalt", "kernthese", "inhalt", "thema",
            "fundstelle", "fehlende_belege", "aufloesung", "stand", "frage",
            "bedeutung_begruendung", "quellenlage", "notiz", "was_gilt", "unterfragen"}
# Zwei Sorten: Korrekturgeschichte (was einmal falsch war) und Selbstbezug
# (Aussagen ueber die Datenbank statt ueber das Recht). Beides gehoert nicht
# in ein Feld, das ein Leser sieht.
_META = _re.compile(
    r"(KORRIGIERT|BERICHTIGT|GE[ÄA]NDERT AM|WIDERSPRUCH AUFGEL[ÖO]ST|IN DIESER SITZUNG|"
    r"GEGENSTANDSLOS in der bisherigen)")            # nur Grossschreibung: Rufe der Pflege
_META2 = _re.compile(
    r"(war falsch|zuvor falsch|bisher eingetragen|bisher gef[üu]hrte?|fehlerhaft eingetragen|"
    r"Korrektur vom|urspr[üu]nglich stand|der bisherige Eintrag|die bisherige Angabe|"
    r"der zuvor hier eingetragene|in dieser Sitzung|im Bestand|Bestandseintrag|"
    r"der eigene Pr[üu]fvermerk|das Ergebnisfeld|Datenmodell:|schema/taxonomie|schema/schema|"
    r"data/(?:regelwerke|urteile|literatur|fristen|streitstaende|normen|weltraster|lernen)/|"
    r"_research/|STAND\.md|JOURNAL\.md)", _re.I)
# "berichtigt" und "korrigiert" in Kleinschreibung sind Rechtssprache
# (Art. 5 Abs. 1 lit. d DSGVO, FRCP 11(c) safe harbor) und kein Befund.

_meta_treffer = []
for _pfad, _doc in lade("data/**/*.yaml"):
    for _schluessel in _doc:
        if not isinstance(_doc[_schluessel], list):
            continue
        for _e in _doc[_schluessel]:
            if not isinstance(_e, dict):
                continue
            for _k, _v in _e.items():
                if _k not in _ANZEIGE:
                    continue
                _texte = [_v] if isinstance(_v, str) else (
                    [_x for _x in _v if isinstance(_x, str)] if isinstance(_v, list) else [])
                for _tx in _texte:
                    _m = _META.search(_tx) or _META2.search(_tx)
                    if _m:
                        # kein break: ein Feld kann mehrere betroffene Elemente
                        # haben, und wer nur den ersten meldet, laesst die
                        # uebrigen nachruecken - die Pruefung wird nie leer.
                        _meta_treffer.append((_e.get("id"), _k, _m.group(0)))
for _i, _k, _w in _meta_treffer:
    warnungen.append(f"{_i}: Korrekturgeschichte im Anzeigefeld '{_k}' (\u00ab{_w}\u00bb) "
                     f"- gehoert nicht in die App")

# Schemaabweichungen zuerst und vollstaendig - sie sind die einzige
# Warnungsart, die stillschweigend Daten unsichtbar macht.
_wichtig = ("steht nicht im Schema", "Datenbank statt der Urschrift",
            "Korrekturgeschichte im Anzeigefeld")
schema_warn = [w for w in warnungen if any(x in w for x in _wichtig)]
uebrig = [w for w in warnungen if w not in schema_warn]
for w in schema_warn:
    print(f"  SCHEMA   {w}")
kurz = Counter(w.split(":", 1)[1].strip()[:60] for w in uebrig)
for text, n in kurz.most_common(12):
    print(f"  WARNUNG  {text}{f'  ({n}x)' if n > 1 else ''}")
if len(kurz) > 12:
    print(f"  ... und {len(kurz)-12} weitere Warnungsarten")
for f in fehler:
    print(f"  FEHLER   {f}")
if offen:
    top = sorted(offen.items(), key=lambda x: -x[1])
    print(f"\n{len(offen)} referenzierte, aber noch nicht erfasste Regelwerke "
          f"({sum(offen.values())} Verweise) - Arbeitsvorrat:")
    for ref, n in top[:15]:
        print(f"  {n:>2}x  {ref}")
    if len(top) > 15: print(f"  ... und {len(top)-15} weitere")
    Path(ROOT / "data/offener_arbeitsvorrat.yaml").write_text(
        "# Automatisch erzeugt von schema/validate.py.\n"
        "# Diese Regelwerke werden von Entscheidungen referenziert, sind aber\n"
        "# noch nicht erfasst. Reihenfolge nach Zahl der Verweise.\n"
        "offen:\n" + "".join(f"  - {{id: {r}, verweise: {n}}}\n" for r, n in top))


print(f"\n{len(fehler)} Fehler, {len(warnungen)} Warnungen.")
sys.exit(1 if fehler else 0)
