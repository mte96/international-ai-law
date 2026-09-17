#!/usr/bin/env python3
"""Erzeugt aus data/ die App-Daten, den Suchindex und den Kalenderfeed.
Aufruf: python3 build/build.py"""
import json, datetime, hashlib, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"

def iso(o):
    if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
    if isinstance(o, dict): return {k: iso(v) for k, v in o.items()}
    if isinstance(o, list): return [iso(v) for v in o]
    return o

def lade(unterordner, schluessel):
    out = []
    for p in sorted((ROOT / "data" / unterordner).rglob("*.yaml")):
        doc = yaml.safe_load(p.read_text())
        if doc and schluessel in doc:
            out.extend(doc[schluessel] or [])
    return iso(out)

tax = iso(yaml.safe_load((ROOT / "schema/taxonomie.yaml").read_text()))
regelwerke = lade("regelwerke", "regelwerke")
urteile    = lade("urteile", "urteile")
literatur  = lade("literatur", "literatur")
fristen    = lade("fristen", "fristen")
streitstaende = lade("streitstaende", "streitstaende")
angebote      = lade("lernen", "angebote")
curriculum    = lade("lernen", "curriculum")
nebenstraenge = lade("lernen", "nebenstraenge")
normen        = lade("normen", "normen")
weltraster    = lade("weltraster", "laender")
sonderwege    = lade("weltraster", "sonderwege")

# --- Suchindex: ein flacher Textblob je Eintrag ----------------------
SUCHFELDER = {
    "regelwerk": ["kurztitel","offizieller_titel","fundstelle","celex","verfahrensnummer",
                  "status_detail","kurzbeschreibung","regelungsschwerpunkte","offene_punkte",
                  "eigene_bewertung"],
    "urteil":    ["gericht","aktenzeichen","ecli","kernfrage","sachverhalt","ergebnis",
                  "anspruchsgrundlage","eigene_bewertung","parteien","quelle_tracker","normen"],
    "streitstand": ["titel","frage","stand","aufloesung","eigene_bewertung","positionen"],
    "literatur": ["titel","autoren","fundstelle","eigene_bewertung","kernthese","normen"],
}

def blob(e, *felder):
    teile = []
    for f in felder:
        v = e.get(f)
        if isinstance(v, str): teile.append(v)
        elif isinstance(v, list):
            teile += [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in v]
        elif isinstance(v, dict): teile.append(json.dumps(v, ensure_ascii=False))
    return re.sub(r"\s+", " ", " ".join(teile)).lower()

# Der Suchindex entsteht im Browser (siehe app.js) - ihn mitzuliefern
# wuerde den gesamten Textbestand ein zweites Mal uebertragen.

# --- Fristen anreichern ----------------------------------------------
heute = datetime.date.today()
rw_titel = {r["id"]: r.get("kurztitel", r["id"]) for r in regelwerke}
def _parteien(u):
    """parteien steht mal als {klaeger, beklagter}, mal als freier Text.
    Beides ist brauchbar; ein Abbruch des ganzen Baus ist es nicht."""
    p = u.get("parteien")
    if isinstance(p, dict):
        s = f'{p.get("klaeger","")} ./. {p.get("beklagter","")}'.strip(" ./")
    else:
        s = str(p or "").strip()
    return s or u.get("gericht") or u["id"]


u_titel = {u["id"]: _parteien(u) for u in urteile}
for f in fristen:
    try:
        d = datetime.date.fromisoformat(str(f["datum"])[:10])
        f["_tage"] = (d - heute).days
    except Exception:
        f["_tage"] = None
    f["_regelwerk_titel"] = (rw_titel.get(f.get("regelwerk"))
                             or u_titel.get(f.get("urteil")) or "")
fristen.sort(key=lambda f: (f["_tage"] is None, f["_tage"] if f["_tage"] is not None else 0))

# --- Rueckverweise ---------------------------------------------------
# Die Daten tragen nur eine Richtung: Literatur nennt das Urteil, das sie
# bespricht. Fuer die App wird die Gegenrichtung gebraucht - an einem
# Urteil soll stehen, wer es besprochen hat.
def rueckverweis(quelle, feld, ziel, zielfeld):
    index = {}
    for e in quelle:
        for ref in e.get(feld) or []:
            index.setdefault(ref, []).append(e["id"])
    for z in ziel:
        treffer = index.get(z["id"])
        if treffer: z[zielfeld] = treffer

rueckverweis(literatur, "bezug_urteile",     urteile,    "_besprochen_von")
rueckverweis(literatur, "bezug_regelwerke",  regelwerke, "_literatur")
rueckverweis(urteile,   "bezug_regelwerke",  regelwerke, "_urteile")
rueckverweis(literatur, "bezug_streitstaende", streitstaende, "_literatur")

# Normen ruecklaeufig: welche Eintraege betreffen diese Vorschrift?
normindex = {}
for e in urteile + literatur:
    for nid in e.get("normen") or []:
        normindex.setdefault(nid, []).append(e["id"])
for n in normen:
    n["_eintraege"] = normindex.get(n["id"], [])

# Rechtsprechung und Literatur je Streitstand

prio = {l["id"]: {"pflicht":0,"wichtig":1}.get(l.get("prioritaet"), 2) for l in literatur}
for st in streitstaende:
    st["_literatur"] = sorted(st.get("_literatur") or [], key=lambda i: prio.get(i, 2))

# --- Quellenklasse je Feld -------------------------------------------
# Eine Angabe traegt nur so weit wie die Quelle, an der sie steht. Das
# wusste die App bisher nur fuer Entscheidungen (`quelle_art`); fuer
# Inkrafttretensdaten, Anwendungsdaten, Verfahrensdokumente, Fristen und
# Vorschriften stand daneben nur ein Ja/Nein, das an keine Quelle
# gebunden war. Gemessen am 10.09.2026: 706 Felder mit `verifiziert:
# true` auf einer Kanzleiseite, einem Presseartikel oder Wikipedia.
#
# Die Klasse wird hier erzeugt, nicht in data/ gefuehrt: sie ist eine
# Ableitung aus der Adresse. Ein abgeleiteter Wert, der doppelt gefuehrt
# wird, laeuft irgendwann auseinander - genau das ist `quelle_art`
# passiert, das im Bestand 278 amtliche Fundstellen auswies, wo die
# host-basierte Einstufung 257 zaehlt.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from quellenklasse import klasse as _klasse

_RANG = {"amtlich": 0, "urheber": 1, "datenbank": 2, "sekundaer": 3, "fehlt": 4}


def _beste(klassen):
    """Die beste Quelle, die ein Eintrag hat - so wird er einsortiert."""
    return min(klassen, key=lambda k: _RANG[k], default="fehlt")


for _r in regelwerke:
    _alle = []
    _ik = _r.get("inkrafttreten")
    if isinstance(_ik, dict):
        _ik["_klasse"] = _klasse(_ik.get("quelle"))
        _alle.append(_ik["_klasse"])
    for _a in _r.get("anwendungsdaten") or []:
        if isinstance(_a, dict):
            _a["_klasse"] = _klasse(_a.get("quelle"))
            _alle.append(_a["_klasse"])
    for _d in _r.get("dokumente") or []:
        if isinstance(_d, dict):
            _d["_klasse"] = _klasse(_d.get("url"))
            _alle.append(_d["_klasse"])
    _r["_quellenlage"] = _beste(_alle)

for _u in urteile:
    # Ueberschreibt, was in data/ steht: das Feld ist als abgeleitet
    # ausgewiesen (schema.yaml Z. 112) und wird nicht von Hand gesetzt.
    _u["quelle_art"] = _klasse(_u.get("volltext_url"))

for _f in fristen:
    _f["_klasse"] = _klasse(_f.get("quelle"))

for _n in normen:
    _n["_klasse"] = _klasse(_n.get("amtlicher_text_url"))

# Zaehlwerk fuer den Startbildschirm: was die Datenbasis ueber sich
# selbst sagen darf. "2040 Verfahrensdokumente - verlinkt und geprueft"
# stand bisher im Kennzahlenblock; 577 davon tragen `verifiziert: false`.
def _zaehle_klassen(felder):
    from collections import Counter as _C
    return dict(_C(felder))


_dok_klassen = [_d.get("_klasse", "fehlt") for _r in regelwerke
                for _d in _r.get("dokumente") or [] if isinstance(_d, dict)]
_ik_klassen = [_r["inkrafttreten"]["_klasse"] for _r in regelwerke
               if isinstance(_r.get("inkrafttreten"), dict)]
_quellenlage = {
    "dokumente": _zaehle_klassen(_dok_klassen),
    "inkrafttreten": _zaehle_klassen(_ik_klassen),
    "urteile": _zaehle_klassen([_u["quelle_art"] for _u in urteile]),
    "fristen": _zaehle_klassen([_f["_klasse"] for _f in fristen]),
    "regelwerke_ohne_amtlich": sum(
        1 for _r in regelwerke if _r["_quellenlage"] not in ("amtlich", "urheber")),
}

daten = {
    "erzeugt": heute.isoformat(),
    "suchfelder": SUCHFELDER,
    "taxonomie": {
        "jurisdiktionen": tax["jurisdiktionen"],
        "kontinente": tax["kontinente"],
        "subjurisdiktionen": tax["subjurisdiktionen"],
        "themenachsen": tax["themenachsen"],
        "statuswerte": tax["statuswerte"],
        "dokumenttypen": tax["dokumenttypen"],
    },
    "regelwerke": regelwerke, "urteile": urteile,
    "literatur": literatur, "fristen": fristen,
    "streitstaende": streitstaende,
    "angebote": angebote, "curriculum": curriculum,
    "nebenstraenge": nebenstraenge, "normen": normen,
    "weltraster": weltraster, "sonderwege": sonderwege,
    "statistik": {
        "regelwerke": len(regelwerke), "urteile": len(urteile),
        "literatur": len(literatur), "fristen": len(fristen),
        "streitstaende": len(streitstaende),
        "angebote": len(angebote), "normen": len(normen),
        "laender_beobachtet": len(weltraster),
        "laender_erfasst": sum(1 for l in weltraster if l.get("einstufung")=="erfasst"),
        "literatur_pflicht": sum(1 for l in literatur if l.get("prioritaet") == "pflicht"),
        "literatur_frei": sum(1 for l in literatur
                              if l.get("zugang") in ("open-access","ssrn","repositorium")),
        "urteile_hoch": sum(1 for u in urteile if u.get("bedeutung") == "hoch"),
        "urteile_unverifiziert": sum(1 for u in urteile if u.get("verifiziert") is False),
        "urteile_amtlich": sum(1 for u in urteile if u.get("quelle_art") == "amtlich"),
        "quellenlage": _quellenlage,
        "dokumente": sum(len(r.get("dokumente") or []) for r in regelwerke),
        "jurisdiktionen_belegt": len({r.get("jurisdiktion") for r in regelwerke}),
    },
}
APP.mkdir(exist_ok=True)
roh = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
(APP / "data.json").write_text(roh)

# --- Cache-Version fuer den Service Worker ---------------------------
# Gehasht wird die Huelle, NICHT data.json. data.json aendert sich jeden Tag,
# weil build.py die Restlaufzeit jeder Frist als _tage einbackt. Haengt die
# Cache-Version daran, bekommt jedes Geraet taeglich einen neuen Cache-Namen
# und laedt die ganze App noch einmal - ueber Mobilfunk rund 9 MB fuer nichts.
# Die Huelle aendert sich nur, wenn jemand wirklich an der App gearbeitet hat.
# sw.js selbst bleibt aussen vor: darin steht die Version.
HUELLE = ["index.html", "app.js", "style.css", "weltkarte.json",
          "manifest.json", "icons/icon.svg"]
_h = hashlib.sha256()
for _name in HUELLE:
    _p = APP / _name
    _h.update(_name.encode())
    _h.update(_p.read_bytes() if _p.exists() else b"")
version = _h.hexdigest()[:12]
sw = APP / "sw.js"
if sw.exists():
    sw.write_text(re.sub(r'const VERSION = "[^"]*"', f'const VERSION = "{version}"', sw.read_text()))

# --- ICS-Kalenderfeed fuer alle Fristen -------------------------------
def esc(s): return str(s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\;").replace("\n", "\\n")
zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AI-LAW//Fristen//DE",
          "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:KI-Recht Fristen",
          "X-WR-TIMEZONE:UTC"]
for f in fristen:
    if not f.get("kalender_sync") or not f.get("datum"): continue
    d = str(f["datum"])[:10].replace("-", "")
    titel = f"{(f.get('jurisdiktion') or '').upper()}: {f.get('beschreibung') or ''}"[:120]
    besch = " ".join(filter(None, [f.get("beschreibung"), f.get("adressat"),
                                    f.get("handlungsbedarf"), f.get("quelle")]))
    zeilen += ["BEGIN:VEVENT", f"UID:{f['id']}@ai-law", f"DTSTAMP:{heute.strftime('%Y%m%d')}T000000Z",
               f"DTSTART;VALUE=DATE:{d}", f"SUMMARY:{esc(titel)}", f"DESCRIPTION:{esc(besch)}",
               "BEGIN:VALARM", "TRIGGER:-P30D", "ACTION:DISPLAY",
               f"DESCRIPTION:{esc('In 30 Tagen: ' + titel)}", "END:VALARM", "END:VEVENT"]
zeilen.append("END:VCALENDAR")
(APP / "fristen.ics").write_text("\r\n".join(zeilen))

s = daten["statistik"]
print(f"{s['regelwerke']} Regelwerke, {s['dokumente']} Dokumente, {s['fristen']} Fristen, "
      f"{s['urteile']} Entscheidungen ({s['urteile_hoch']} von hoher Bedeutung, "
      f"{s['urteile_unverifiziert']} unverifiziert), {s['streitstaende']} Streitstände, "
      f"{s['literatur']} Literatur, {s['angebote']} Lernangebote, "
      f"{s['normen']} Vorschriften")
print(f"data.json {len(roh)//1024} KB | Version {version}")
naechste = [f for f in fristen if f.get("_tage") is not None and f["_tage"] >= 0][:3]
for f in naechste:
    print(f"  in {f['_tage']:>4} Tagen: {str(f.get('beschreibung'))[:70]}")
