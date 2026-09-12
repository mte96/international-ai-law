#!/usr/bin/env python3
"""Stellt Umlaute in Textfeldern der Datenbasis her.

Rohrecherchen kommen teils ohne Umlaute zurueck ("Marktueberwachung").
Frueher lief das ueber Regeln und Ausnahmelisten - und erzeugte aus
"Moskauer" ein "Moskaür". Jetzt entscheidet ein deutsches Woerterbuch:

  1. Ist das Wort schon ein gueltiges deutsches Wort? Dann anfassen wir es
     nicht ("Moskauer", "Quelle", "neue", "Steuer", "zuerst").
  2. Sonst werden alle Umlaut-Varianten gebildet und die erste genommen,
     die im Woerterbuch steht ("Marktueberwachung" -> "Marktüberwachung").
  3. Steht keine drin, bleibt das Original stehen (englische Woerter,
     Eigennamen, Aktenzeichen).

Das Woerterbuch ist hunspell de_DE ueber spylls; es kennt Komposita.
Fehlt es, arbeitet das Skript nicht und meldet das - lieber gar keine
Umlaute als falsche.

    python3 build/umlaute.py            # data/ bearbeiten
    python3 build/umlaute.py --pruefen  # nur berichten, nichts aendern
"""
import itertools, re, sys
from pathlib import Path
import yaml

# Felder, deren Inhalt niemals angefasst wird: ids, URLs, Kennungen,
# kontrolliertes Vokabular.
TABU = {"id","url","feed_url","eli","celex","doi","isbn","ssrn_id","quelle","api_doku_url",
        "verfahrensnummer","ecli","aktenzeichen","typ","status","jurisdiktion","sprache",
        "themenachsen","bezug_regelwerke","bezug_urteile","fristen","monitoring_quellen",
        "instanzenzug","exzerpt_datei","typ_original","volltext_url","zusammenfassung_url",
        "lektuere","angebote","streitstaende","urteile","literatur","regelwerke","normen",
        "bezug_streitstaende","auch_erfasst_in","_literatur","profil","dienste",
        "quelle_tracker","openalex_id","subjurisdiktion","subjurisdiktionen","parent",
        "jurisdiktionen","art","prioritaet","lesestatus","zugang","bedeutung","instanz",
        "kategorie","format","normen_verzeichnis","regelwerk","urteil"}

try:
    from spylls.hunspell import Dictionary
    WB = Dictionary.from_files("/usr/share/hunspell/de_DE")
except Exception as e:                                   # pragma: no cover
    sys.exit(f"Deutsches Woerterbuch nicht verfuegbar ({e}).\n"
             "  apt-get install hunspell-de-de && pip install spylls --break-system-packages")

_bekannt = {}
def bekannt(w):
    """Auch die kleingeschriebene Form pruefen: am Satzanfang steht ein
    Substantiv gross, ein Adjektiv aber ebenfalls - das Woerterbuch kennt
    nur eine der beiden Formen."""
    if w not in _bekannt:
        try:
            _bekannt[w] = WB.lookup(w) or (w[:1].isupper() and WB.lookup(w.lower()))
        except Exception:
            _bekannt[w] = False
    return _bekannt[w]

PAAR = {"ae": "ä", "oe": "ö", "ue": "ü", "ss": "ß"}

def varianten(w):
    """Alle Kombinationen ersetzbarer Stellen, laengste Ersetzung zuerst."""
    stellen = [m.start() for m in re.finditer(r"[aouAOU][eE]|ss", w)]
    if not stellen or len(stellen) > 5: return []
    aus = []
    for wieviele in range(len(stellen), 0, -1):
        for wahl in itertools.combinations(stellen, wieviele):
            neu, versatz = w, 0
            for i in wahl:
                p = neu[i-versatz:i-versatz+2]
                ers = PAAR.get(p.lower())
                if not ers: continue
                if p[0].isupper(): ers = ers.upper()
                neu = neu[:i-versatz] + ers + neu[i-versatz+2:]
                versatz += 1
            if neu != w: aus.append(neu)
    return aus

ZURUECK = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}

def rueckvarianten(w):
    """Alle Kombinationen, bei denen Umlaute wieder ausgeschrieben werden."""
    stellen = [m.start() for m in re.finditer(r"[äöüßÄÖÜ]", w)]
    if not stellen or len(stellen) > 5: return []
    aus = []
    for wieviele in range(1, len(stellen)+1):
        for wahl in itertools.combinations(stellen, wieviele):
            neu, versatz = w, 0
            for i in wahl:
                z = neu[i+versatz]
                ers = ZURUECK.get(z.lower())
                if not ers: continue
                if z.isupper(): ers = ers.capitalize()
                neu = neu[:i+versatz] + ers + neu[i+versatz+1:]
                versatz += 1
            if neu != w: aus.append(neu)
    return aus

def repariere(w):
    """Ein Umlaut, den es im Deutschen nicht gibt, kommt von einer
    frueheren Fehlkonvertierung: 'Moskaür' war einmal 'Moskauer'."""
    if len(w) < 4 or not re.search(r"[äöüßÄÖÜ]", w): return w
    if bekannt(w): return w
    for k in rueckvarianten(w):
        if bekannt(k): return k
    return w

def wort(w):
    w = repariere(w)
    if len(w) < 4 or not re.search(r"[aouAOU][eE]|ss", w): return w
    if bekannt(w): return w                     # schon richtig - nicht anfassen
    for k in varianten(w):
        if bekannt(k): return k
    return w                                    # nichts Besseres gefunden

def text(s):
    if not isinstance(s, str) or "://" in s: return s
    teile = re.split(r"(https?://\S+)", s)
    for i in range(0, len(teile), 2):
        teile[i] = re.sub(r"[A-Za-zÄÖÜäöüß]{4,}", lambda m: wort(m.group(0)), teile[i])
    return "".join(teile)

geaendert = []
def geh(o, schluessel=None):
    if isinstance(o, dict):
        def tabu(k, v):
            if k not in TABU: return False
            if isinstance(v, list): return not any(isinstance(x, (dict, list)) for x in v)
            return True
        return {k: (v if tabu(k, v) else geh(v, k)) for k, v in o.items()}
    if isinstance(o, list): return [geh(x, schluessel) for x in o]
    if isinstance(o, str):
        neu = text(o)
        if neu != o: geaendert.append((o[:60], neu[:60]))
        return neu
    return o

if __name__ == "__main__":
    nur_pruefen = "--pruefen" in sys.argv
    root = Path(__file__).resolve().parent.parent
    for p in sorted((root / "data").rglob("*.yaml")):
        doc = yaml.safe_load(p.read_text())
        if not doc: continue
        neu = geh(doc)
        if not nur_pruefen:
            p.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n" +
                         yaml.dump(neu, allow_unicode=True, sort_keys=False, width=100))
    print(f"{len(geaendert)} Textstellen {'zu ändern' if nur_pruefen else 'geändert'}")
    for a, b in geaendert[:12]:
        print(f"   {a!r}\n-> {b!r}")
