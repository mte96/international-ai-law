#!/usr/bin/env python3
"""Findet fremdsprachige Woerter, die eine fruehere Umlaut-Heuristik
verfaelscht hat: 'Doe' wurde zu 'Doe' -> 'Do' + 'e' -> 'Dö', 'Caesars'
zu 'Caesars' -> 'Cäsars', 'does' zu 'dös'.

Ein Treffer liegt vor, wenn das Wort im Deutschen unbekannt ist, seine
Rueckuebersetzung (ä->ae, ö->oe, ü->ue) aber im Englischen bekannt ist
oder auf der Namensliste steht.

    python3 build/fremdumlaut.py            # nur berichten
    python3 build/fremdumlaut.py --aendern  # ersetzen

Braucht spylls und die Woerterbuecher de_DE und en_US:
    pip install spylls
    apt-get install hunspell-de-de hunspell-en-us
Fehlt eines von beiden, meldet das Programm das und endet ohne Fehler —
die uebrigen Pruefungen sollen daran nicht scheitern.
"""
import re, sys, glob, os

WB_PFAD = os.environ.get("HUNSPELL_PFAD", "/usr/share/hunspell")
try:
    from spylls.hunspell import Dictionary
    DE = Dictionary.from_files(f"{WB_PFAD}/de_DE")
    EN = Dictionary.from_files(f"{WB_PFAD}/en_US")
except ImportError:
    print("spylls ist nicht installiert - Pruefung uebersprungen "
          "(pip install spylls)")
    sys.exit(0)
except FileNotFoundError as e:
    print(f"Woerterbuch nicht gefunden ({e}) - Pruefung uebersprungen "
          f"(apt-get install hunspell-de-de hunspell-en-us)")
    sys.exit(0)
_c = {}


def kennt(wb, w):
    k = (id(wb), w)
    if k not in _c:
        _c[k] = wb.lookup(w) or wb.lookup(w.lower()) or wb.lookup(w.capitalize())
    return _c[k]


TR = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})

# Eigennamen und Fachbegriffe, die kein Woerterbuch kennt.
NAMEN = {
    "Dö": "Doe", "Cäsars": "Caesars", "Cäsar": "Caesar", "curiä": "curiae",
    "Curiä": "Curiae", "Revenü": "Revenue", "Jä": "Jae", "Säed": "Saed",
    "Jöl": "Joel", "Pasüngos": "Pasuengos", "Misäl": "Misael",
    "Michäl": "Michael", "Rafäl": "Rafael", "Isräl": "Israel",
    "Manül": "Manuel", "Samül": "Samuel", "Danül": "Daniel",
    "Nathanül": "Nathanael", "Gabriül": "Gabriel", "Emanül": "Emanuel",
    "Chlöe": "Chloe", "Zoë": "Zoe", "Renä": "Renae", "Aimä": "Aimee",
    "Renü": "Renue", "Avenü": "Avenue", "Venü": "Venue", "Issü": "Issue",
    "Tissü": "Tissue", "Valü": "Value", "Argü": "Argue", "Rescü": "Rescue",
    "Statü": "Statue", "Virtü": "Virtue", "Continü": "Continue",
    "Pursü": "Pursue", "Quü": "Queue", "Tobiä": "Tobiae",
    # Am 07.09.2026 von zwei Rechercheagenten gefunden
    "Dü": "Due", "Reü": "Reue", "Gräber": None, "Guangzhoür": "Guangzhouer",
    "Fö": None,   # mehrdeutig: FoE, FOE oder Foe - am Eintrag klaeren

    "püde": "puede", "jüz": "juez", "taggenaü": "taggenaue",
    "Klickvergüting": "Klickverguetung", "Samülson": "Samuelson",
}

# Woerter, die echtes Deutsch sind und zufaellig eine englische
# Rueckuebersetzung haben - niemals anfassen.
TABU = {"über", "Über", "für", "Für", "möge", "Möge", "böse", "Böse",
        "hüte", "Hüte", "süß", "müde", "Müde", "möbel", "Möbel",
        "füge", "Füge", "würde", "Würde", "größe", "Größe"}


def treffer(w):
    # Zwei Zeichen genuegen: "Due" wurde zu "Dü", "Doe" zu "Dö".
    if w in TABU or len(w) < 2:
        return None
    if w in NAMEN:
        # None heisst: mehrdeutig, nur melden, nicht ersetzen.
        # "Gräber" ist echtes Deutsch und zugleich der verfaelschte
        # Nachname Graeber - das muss ein Mensch entscheiden.
        return NAMEN[w]
    if not re.search(r"[äöüÄÖÜ]", w) or kennt(DE, w):
        return None
    r = w.translate(TR)
    if r == w:
        return None
    # Ganz grossgeschriebene Kuerzel: DOE, nicht DOe. Die Umschrift macht
    # aus Ö ein Oe, das zweite Zeichen muss mitwandern.
    if w.isupper():
        r = r.upper()
    # Die Rueckuebersetzung ist ein bekanntes Wort - egal in welcher
    # Sprache. "Reü" -> "Reue" ist deutsch, "Dü" -> "Due" englisch;
    # beides ist derselbe Schaden.
    if kennt(EN, r) or kennt(DE, r):
        return r
    return None


def main():
    aendern = "--aendern" in sys.argv
    gefunden, dateien = {}, 0
    pfade = (glob.glob("data/**/*.yaml", recursive=True)
             + glob.glob("lernen/**/*.yaml", recursive=True)
             + glob.glob("tracker/**/*.yaml", recursive=True))
    for p in pfade:
        t = alt = open(p, encoding="utf-8").read()
        for w in sorted(set(re.findall(r"[A-Za-zÄÖÜäöüß]{2,}", t)), key=len, reverse=True):
            r = treffer(w)
            if r:
                gefunden.setdefault(w, [r, 0])
                n = len(re.findall(r"\b" + re.escape(w) + r"\b", t))
                gefunden[w][1] += n
                if aendern:
                    t = re.sub(r"\b" + re.escape(w) + r"\b", r, t)
        if aendern and t != alt:
            open(p, "w", encoding="utf-8").write(t)
            dateien += 1
    for w, (r, n) in sorted(gefunden.items(), key=lambda kv: -kv[1][1]):
        print(f"  {n:4d}x  {w}  ->  {r}")
    print(f"\n{len(gefunden)} Wortformen, {sum(v[1] for v in gefunden.values())} Stellen"
          + (f", {dateien} Dateien geaendert" if aendern else " (nur Bericht)"))


main()
