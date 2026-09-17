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

# =====================================================================
# Ab hier die Pruefungen, die der Pruefbericht vom 10./11.09.2026
# vermisst hat (Abschnitt 3.6): von 40 Regelwerksfeldern fasste diese
# Datei 17 an, die Pflichtfeldlisten nie, die Typen nie, die
# verschachtelten Felder nie. Der Schaden war messbar: die frueher
# aktive Umlaut-Heuristik hat vier Fristen- und vierzehn
# Literaturverweise unbrauchbar gemacht ("oecd" -> "oecd" mit o-Umlaut),
# und niemand hat es bemerkt, weil genau diese Felder ausgelassen waren.
#
# Grundsatz: Ein Feld ohne Pruefung laeuft irgendwann mit einem falschen
# Wert ein. Neue Felder gehoeren ins Schema, neue Werte in die Taxonomie,
# und beides wird hier abgefragt.
# =====================================================================

# Der Bestand einmal einlesen, statt fuer jede Pruefung neu ueber die
# 140 Dateien zu laufen.
BESTAND = {s: [] for s in _GATT}
for _pfad, _doc in lade("data/**/*.yaml"):
    for _s in _GATT:
        for _e in _doc.get(_s) or []:
            if isinstance(_e, dict):
                BESTAND[_s].append((_pfad, _e))

_IDS = {s: {e.get("id") for _p, e in E} for s, E in BESTAND.items()}


def _kurz(pfad):
    return str(Path(pfad).relative_to(ROOT))


# --- Pflichtfelder ------------------------------------------------------
# Standen seit je in schema.yaml und wurden nie abgefragt. Neun Fristen
# ohne `datum` sind so durchgelaufen: build.py setzt ihnen `_tage: null`,
# die Kalenderdatei laesst sie aus, und in der App stehen sie als Karte
# ohne Termin - eine Frist, die keine ist.
for _s, _gatt in _GATT.items():
    _pflicht = (_schema.get(_gatt) or {}).get("pflichtfelder") or []
    for _pfad, _e in BESTAND[_s]:
        for _p in _pflicht:
            if _e.get(_p) not in (None, "", [], {}):
                continue
            # Eine Frist ohne Termin ist keine Luecke, wenn der Eintrag
            # selbst sagt, dass kein Termin veroeffentlicht ist. Was statt
            # dessen bekannt ist, steht in datum_hinweis. Bisher stand in
            # solchen Faellen das Wort "offen" im Datumsfeld - eine
            # Zeichenkette, die durch jede Pruefung fiel.
            if _gatt == "frist" and _p == "datum" and _e.get("datum_offen") is True:
                if not _e.get("datum_hinweis"):
                    warnungen.append(f"{_e.get('id','?')}: datum_offen gesetzt, "
                                     f"aber kein datum_hinweis - was ist statt "
                                     f"des Termins bekannt?")
                continue
            fehler.append(f"{_e.get('id', _kurz(_pfad))}: Pflichtfeld "
                          f"'{_p}' fehlt oder ist leer ({_gatt})")

# --- Datumsfelder muessen Daten sein ------------------------------------
# YAML liest 2026-09-17 als Datum und "2026-09-17 (im Eintrag stand ...)"
# als Zeichenkette. Beides steht im selben Feld, und nichts hat den
# Unterschied gemeldet: build.py rechnet die Restlaufzeit nur fuer echte
# Daten, die Fristenpruefung oben ueberspringt Zeichenketten
# (isinstance-Abfrage), die Kalenderdatei laesst sie aus. Eine Frist mit
# Datum als Text ist unsichtbar, ohne dass irgendwo etwas rot wird.
# Wo ein Datum unsicher ist, gehoert die Unsicherheit in `pruefvermerk`,
# nicht als Klammerzusatz in das Datumsfeld.
_DATUMSFELDER = {"datum", "letzte_pruefung"}
_re_teildatum = re.compile(r"\d{4}(-\d{2})?")


def _datum_pruefen(eid, obj, pfad=""):
    if isinstance(obj, dict):
        for _k, _v in obj.items():
            _neu = f"{pfad}.{_k}" if pfad else _k
            if _k in _DATUMSFELDER and _v is not None and not isinstance(_v, datetime.date):
                # Zugelassen ist genau eine Ausnahme: eine ausdruecklich
                # unvollstaendige Angabe, "2022" oder "2022-05". Sie sagt,
                # was bekannt ist, und erfindet keinen Tag - anders als der
                # 1. Januar, der im Bestand elfmal als Platzhalter steht.
                # Alles andere, vor allem ein Datum mit Klammerzusatz, macht
                # aus dem Feld eine Zeichenkette und die Angabe unsichtbar.
                if not _re_teildatum.fullmatch(str(_v)):
                    fehler.append(f"{eid}: '{_neu}' ist kein Datum, sondern "
                                  f"{type(_v).__name__} ({str(_v)[:60]!r}) - ein "
                                  f"erlaeuternder Zusatz gehoert in datum_hinweis, "
                                  f"eine unvollstaendige Angabe lautet '2026' "
                                  f"oder '2026-05'")
            else:
                _datum_pruefen(eid, _v, _neu)
    elif isinstance(obj, list):
        for _x in obj:
            _datum_pruefen(eid, _x, pfad)


for _s in BESTAND:
    for _pfad, _e in BESTAND[_s]:
        _datum_pruefen(_e.get("id", _kurz(_pfad)), _e)

# --- Verweise, die bisher niemand nachgegangen ist ----------------------
# `bezug_regelwerke` darf ins Leere zeigen - das ist der Arbeitsvorrat.
# Die hier genannten Felder duerfen es nicht: sie bezeichnen jeweils ein
# Stueck Bestand, das es geben muss, damit die App eine Karte, einen
# Titel oder einen Rueckweg zeigen kann. Zeigen sie daneben, entsteht
# kein Fehler, sondern eine Luecke, die wie ein Datum aussieht.
_VERWEISE = [
    ("fristen", "regelwerk", "regelwerke"),
    ("fristen", "urteil", "urteile"),
    ("literatur", "bezug_streitstaende", "streitstaende"),
    ("streitstaende", "bezug_streitstaende", "streitstaende"),
    ("urteile", "bezug_streitstaende", "streitstaende"),
    ("streitstaende", "bezug_literatur", "literatur"),
    ("regelwerke", "fristen", "fristen"),
]
for _s, _feld, _ziel in _VERWEISE:
    for _pfad, _e in BESTAND.get(_s, []):
        _w = _e.get(_feld)
        if _w is None:
            continue
        for _ref in ([_w] if isinstance(_w, str) else _w):
            if not isinstance(_ref, str):
                continue
            if _ref not in _IDS[_ziel]:
                fehler.append(f"{_e.get('id','?')}: {_feld} zeigt auf "
                              f"'{_ref}' - kein Eintrag dieser Art im Bestand")

# Freitext in Feldern, die eine id tragen sollen. Kein Fehler - das ist
# Arbeit, nicht Schaden -, aber es soll gezaehlt und sichtbar sein.
# `normen.via` sagt, ueber welchen Rechtsakt eine Vorschrift hereinkam,
# `monitoring_quellen`, welche Trackerquelle sie beobachtet. Beides steht
# heute als Prosa bzw. als Adresse da; die Verbindung Regelwerk<->Tracker
# gibt es deshalb nicht, obwohl 1494 Werte so aussehen.
for _s, _feld, _ziel in (("normen", "via", "regelwerke"),
                         ("normen", "geaendertes_regelwerk", "regelwerke")):
    _frei = [e.get("id") for _p, e in BESTAND[_s]
             if isinstance(e.get(_feld), str) and e[_feld] not in _IDS[_ziel]]
    if _frei:
        warnungen.append(f"normen: {len(_frei)} Eintraege fuehren unter '{_feld}' "
                         f"Freitext statt einer Regelwerk-id - das Schema sieht "
                         f"eine id vor")
_mq = [e.get("id") for _p, e in BESTAND["regelwerke"]
       for q in (e.get("monitoring_quellen") or [])
       if isinstance(q, str) and q.startswith("http")]
if _mq:
    warnungen.append(f"regelwerke: {len(_mq)} Werte in 'monitoring_quellen' sind "
                     f"Adressen statt ids aus tracker/quellen.yaml - die Verbindung "
                     f"Regelwerk<->Tracker besteht damit nicht")

# --- Kontrollierte Vokabeln --------------------------------------------
# Was die App kennt, muss die Datenbasis auch schreiben. `instanz` stand
# 46-mal als "behoerde" mit Umlaut und 13-mal ohne; die App kennt nur die
# Umschrift (app.js 1616), also blieben 46 Eintraege ohne Instanzangabe.
_VOKABELN = [
    ("urteile", "instanz", {i["id"] for i in tax.get("instanzen", [])}),
    ("urteile", "bedeutung", {b["id"] for b in tax.get("bedeutungsstufen", [])}),
    ("urteile", "quelle_art", {q["id"] for q in tax.get("quellenklassen", [])}),
    ("fristen", "typ", {t["id"] for t in tax.get("fristtypen", [])}),
]
for _s, _feld, _erlaubt in _VOKABELN:
    if not _erlaubt:
        fehler.append(f"taxonomie: Vokabular fuer {_s}.{_feld} fehlt")
        continue
    for _pfad, _e in BESTAND[_s]:
        _w = _e.get(_feld)
        if _w is not None and _w not in _erlaubt:
            fehler.append(f"{_e.get('id','?')}: unbekannter Wert fuer "
                          f"'{_feld}': {str(_w)[:60]!r}")

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
            "bedeutung_begruendung", "quellenlage", "notiz", "was_gilt", "unterfragen",
            "begruendung", "quelle_tracker", "datum_hinweis", "position"}
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


def _meta_suchen(eid, obj, pfad=""):
    """Rekursiv, weil die Korrekturgeschichte eine Ebene tiefer sitzt."""
    if isinstance(obj, dict):
        for _k, _v in obj.items():
            _neu = f"{pfad}.{_k}" if pfad else _k
            if _k in _ANZEIGE:
                _texte = [_v] if isinstance(_v, str) else (
                    [_x for _x in _v if isinstance(_x, str)] if isinstance(_v, list) else [])
                for _tx in _texte:
                    _m = _META.search(_tx) or _META2.search(_tx)
                    if _m:
                        # kein break: ein Feld kann mehrere betroffene Elemente
                        # haben, und wer nur den ersten meldet, laesst die
                        # uebrigen nachruecken - die Pruefung wird nie leer.
                        _meta_treffer.append((eid, _neu, _m.group(0)))
            _meta_suchen(eid, _v, _neu)
    elif isinstance(obj, list):
        for _x in obj:
            _meta_suchen(eid, _x, pfad)


for _pfad, _doc in lade("data/**/*.yaml"):
    for _schluessel in _doc:
        if not isinstance(_doc[_schluessel], list):
            continue
        for _e in _doc[_schluessel]:
            if isinstance(_e, dict):
                _meta_suchen(_e.get("id"), _e)
_meta_nach_feld = Counter(_k for _i, _k, _w in _meta_treffer)
for _i, _k, _w in _meta_treffer:
    warnungen.append(f"{_i}: Korrekturgeschichte im Anzeigefeld '{_k}' (\u00ab{_w}\u00bb) "
                     f"- gehoert nicht in die App")
if _meta_treffer:
    print(f"  SCHEMA   Korrekturgeschichte in {len(_meta_treffer)} gerenderten "
          f"Feldern - nach Feld: "
          + ", ".join(f"{_k} {_n}" for _k, _n in _meta_nach_feld.most_common(8)))

# Schemaabweichungen zuerst und vollstaendig - sie sind die einzige
# Warnungsart, die stillschweigend Daten unsichtbar macht.
_wichtig = ("steht nicht im Schema", "Datenbank statt der Urschrift",
            "Freitext statt einer Regelwerk-id", "Adressen statt ids aus tracker",
            "datum_offen gesetzt")
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
