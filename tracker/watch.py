#!/usr/bin/env python3
"""Ruft die Quellen aus quellen.yaml ab, erkennt Neues und meldet es.

Aufruf:
    python3 tracker/watch.py              # alle faelligen Quellen
    python3 tracker/watch.py --alle       # Intervalle ignorieren
    python3 tracker/watch.py --trocken    # nichts senden, nichts speichern
    python3 tracker/watch.py --quelle ID  # nur eine Quelle

Beim ersten Lauf einer Quelle wird nur der Zustand gespeichert und NICHTS
gemeldet - sonst kaeme die gesamte Historie als Benachrichtigung an.
"""
import argparse, hashlib, json, re, sys, time, os
import datetime as dt
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import yaml

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "tracker"
ZUSTAND = TR / "zustand.json"
EINGANG = TR / "eingang"
UA = "ai-law-tracker/1.0 (+privates Rechtsmonitoring; Kontakt via Repo)"

def lade_zustand():
    if ZUSTAND.exists():
        try: return json.loads(ZUSTAND.read_text())
        except json.JSONDecodeError: pass
    return {"quellen": {}}

def hole(url, timeout=25):
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*",
                                "Accept-Language": "de,en;q=0.8"})
    with urlopen(req, timeout=timeout) as r:
        roh = r.read()
    for kodierung in ("utf-8", "latin-1"):
        try: return roh.decode(kodierung)
        except UnicodeDecodeError: continue
    return roh.decode("utf-8", "replace")

# ---------------------------------------------------------------- Parser
def parse_feed(text):
    """RSS und Atom, ohne externe Abhaengigkeit."""
    import xml.etree.ElementTree as ET
    try: baum = ET.fromstring(text.encode("utf-8", "replace"))
    except ET.ParseError:
        return None
    NS = {"a": "http://www.w3.org/2005/Atom"}
    treffer = []
    for it in baum.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"): continue
        def feld(*namen):
            for n in namen:
                e = it.find(n) if "}" not in n else None
                if e is None: e = it.find(f"{{http://www.w3.org/2005/Atom}}{n}")
                if e is None: e = it.find(n)
                if e is not None and (e.text or e.get("href")):
                    return (e.text or e.get("href") or "").strip()
            return ""
        link = feld("link")
        if not link:
            for e in it.iter():
                if e.tag.split("}")[-1] == "link" and e.get("href"):
                    link = e.get("href"); break
        treffer.append({
            "titel": re.sub(r"<[^>]+>", " ", feld("title"))[:400].strip(),
            "url": link,
            "datum": feld("pubDate", "published", "updated", "date")[:32],
            "text": re.sub(r"<[^>]+>", " ", feld("description", "summary", "content"))[:900].strip(),
            "kennung": feld("guid", "id") or link,
        })
    return treffer

def parse_html(text, basis):
    """Uebersichtsseiten ohne Feed. Jeder Link mit brauchbarem Text zaehlt als
    Eintrag; die Auswahl trifft danach der Stichwortfilter. Grob, aber es ist
    der einzige Weg zu Amtsseiten, die keinen Feed fuehren - in China und in
    Singapur fuehrt keine einzige erreichbare Amtsseite einen."""
    from urllib.parse import urljoin
    import html as _html
    treffer, gesehen = [], set()
    for m in re.finditer(r"<a\b[^>]*?href=([\"'])(.*?)\1[^>]*>(.*?)</a>", text, re.I | re.S):
        href, innen = m.group(2), m.group(3)
        titel = _html.unescape(re.sub(r"<[^>]+>", " ", innen))
        titel = re.sub(r"\s+", " ", titel).strip()
        if len(titel) < 8 or len(titel) > 300: continue
        if href.startswith(("#", "javascript:", "mailto:", "tel:")): continue
        url = urljoin(basis, _html.unescape(href.strip()))
        if not url.startswith("http") or url in gesehen: continue
        gesehen.add(url)
        # Datum aus der Umgebung des Links, wenn es dort steht.
        umfeld = text[m.end():m.end()+220]
        d = re.search(r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}\s+\w+\s+20\d{2})", umfeld)
        treffer.append({"titel": titel[:400], "url": url,
                        "datum": d.group(1) if d else "", "text": "", "kennung": url})
        if len(treffer) >= 200: break
    return treffer

def parse_auto(text, format_, url):
    """Eine Antwort auswerten, je nach angekuendigtem Format."""
    if format_ == "json":     return parse_json(text)
    if format_ == "scraping": return parse_html(text, url)
    return parse_feed(text)

TITELFELDER = ("title", "name", "shortTitle", "headline", "caseName", "documentTitle",
               "case_name", "short_title", "titel", "subject", "abstract")
URLFELDER   = ("html_url", "url", "link", "absolute_url", "uri", "pdf_url", "publication_url")
DATUMFELDER = ("publication_date", "date", "dateFiled", "date_filed", "updated_at",
               "lastUpdated", "created", "datum", "publishedDate", "date_created")

def parse_json(text):
    try: d = json.loads(text)
    except json.JSONDecodeError: return None
    # Groesste Liste von Objekten im Dokument suchen
    beste = []
    def geh(o, tiefe=0):
        nonlocal beste
        if tiefe > 5: return
        if isinstance(o, list):
            objekte = [x for x in o if isinstance(x, dict)]
            if len(objekte) > len(beste) and objekte and any(
                    any(k in x for k in TITELFELDER) for x in objekte[:5]):
                beste = objekte
            for x in o[:60]: geh(x, tiefe+1)
        elif isinstance(o, dict):
            for v in o.values(): geh(v, tiefe+1)
    geh(d)
    def erstes(x, felder):
        for f in felder:
            v = x.get(f)
            if isinstance(v, str) and v.strip(): return v.strip()
            if isinstance(v, dict):
                for vv in v.values():
                    if isinstance(vv, str) and vv.strip(): return vv.strip()
        return ""
    return [{
        "titel": erstes(x, TITELFELDER)[:400],
        "url": erstes(x, URLFELDER),
        "datum": erstes(x, DATUMFELDER)[:32],
        "text": (erstes(x, ("abstract","summary","description","excerpt")) or "")[:900],
        "kennung": str(x.get("id") or x.get("uuid") or erstes(x, URLFELDER)
                       or erstes(x, TITELFELDER))[:200],
    } for x in beste[:120]]

# ---------------------------------------------------------------- Lauf
def faellig(quelle, zuletzt, jetzt):
    if not zuletzt: return True
    m = re.match(r"(\d+)\s*([hdm])", str(quelle.get("intervall", "12h")).lower())
    stunden = 12
    if m:
        n, e = int(m.group(1)), m.group(2)
        stunden = n if e == "h" else n*24 if e == "d" else max(1, n//60)
    return (jetzt - zuletzt) >= stunden * 3600 * 0.9

def schluessel(item):
    return hashlib.sha1((item.get("kennung") or item.get("url") or
                         item.get("titel") or "").encode()).hexdigest()[:16]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alle", action="store_true")
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--quelle")
    ap.add_argument("--limit", type=int, default=0, help="hoechstens N Quellen abrufen")
    a = ap.parse_args()

    konf = yaml.safe_load((TR / "quellen.yaml").read_text())
    muster = [re.compile(s, re.I) for s in konf["stichworte"]]
    quellen = [q for q in konf["quellen"] if q.get("aktiv")]
    if a.quelle:
        quellen = [q for q in konf["quellen"] if q["id"] == a.quelle]
        if not quellen: sys.exit(f"Quelle '{a.quelle}' nicht gefunden")

    zustand = lade_zustand()
    jetzt = time.time()
    neu_gesamt, fehler, erstlaeufe, uebersprungen = [], [], [], 0

    for q in quellen:
        z = zustand["quellen"].setdefault(q["id"], {"gesehen": [], "zuletzt": 0, "fehler": 0})
        if not (a.alle or a.quelle) and not faellig(q, z.get("zuletzt", 0), jetzt):
            uebersprungen += 1; continue
        if a.limit and len(neu_gesamt) + len(fehler) >= a.limit: break

        url = q["feed_url"]
        if q.get("auth"):
            key = os.environ.get(f"KEY_{q['id'].upper()}")
            if not key:
                fehler.append((q["id"], "API-Key fehlt (Umgebungsvariable "
                                        f"KEY_{q['id'].upper()})")); continue
            url += ("&" if "?" in url else "?") + f"api_key={key}"

        try:
            text = hole(url)
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            z["fehler"] = z.get("fehler", 0) + 1
            fehler.append((q["id"], f"{type(e).__name__}: {e}")); continue

        items = parse_auto(text, q["format"], url)
        if items is None:
            z["fehler"] = z.get("fehler", 0) + 1
            fehler.append((q["id"], "Antwort nicht lesbar (weder Feed noch JSON)")); continue
        if not items:
            # Ein valider, aber leerer Feed ist verdaechtig, kein Erfolg.
            fehler.append((q["id"], "Feed lieferte null Eintraege - Quelle pruefen"))

        z["fehler"] = 0
        z["zuletzt"] = jetzt
        gesehen = set(z.get("gesehen", []))
        erstlauf = not gesehen

        for it in items:
            s = schluessel(it)
            if s in gesehen: continue
            gesehen.add(s)
            if erstlauf: continue
            heu = f"{it.get('titel','')} {it.get('text','')}"
            if not any(m.search(heu) for m in muster): continue
            neu_gesamt.append({**it, "quelle": q["name"], "quelle_id": q["id"],
                               "jurisdiktion": q["jurisdiktion"], "kategorie": q["kategorie"]})

        z["gesehen"] = list(gesehen)[-1500:]
        if erstlauf: erstlaeufe.append(q["id"])

    # ---------- Ausgabe ----------
    print(f"{len(quellen)-uebersprungen} Quellen abgerufen, {uebersprungen} nicht faellig")
    if erstlaeufe:
        print(f"{len(erstlaeufe)} Erstlaeufe (Zustand gesetzt, nichts gemeldet): "
              f"{', '.join(erstlaeufe[:8])}{' ...' if len(erstlaeufe)>8 else ''}")
    print(f"{len(neu_gesamt)} neue Treffer mit KI-Bezug")
    for f in fehler:
        print(f"  FEHLER {f[0]}: {f[1][:110]}")

    if a.trocken:
        for n in neu_gesamt[:20]:
            print(f"  [{n['jurisdiktion']}] {n['titel'][:100]}")
        return 0

    if neu_gesamt:
        EINGANG.mkdir(exist_ok=True)
        heute = dt.date.today().isoformat()
        datei = EINGANG / f"{heute}.md"
        zeilen = [] if datei.exists() else [f"# Eingang {heute}\n"]
        for n in neu_gesamt:
            zeilen.append(f"\n## {n['titel']}\n")
            zeilen.append(f"- Quelle: {n['quelle']} ({n['jurisdiktion']}, {n['kategorie']})")
            if n.get("datum"): zeilen.append(f"- Datum: {n['datum']}")
            if n.get("url"):   zeilen.append(f"- {n['url']}")
            if n.get("text"):  zeilen.append(f"\n{n['text'][:400]}")
            zeilen.append("")
        with datei.open("a") as f: f.write("\n".join(zeilen))
        print(f"-> {datei.relative_to(ROOT)}")

    ZUSTAND.write_text(json.dumps(zustand, ensure_ascii=False))

    if neu_gesamt:
        sys.path.insert(0, str(TR))
        from notify import sende
        nach_jur = {}
        for n in neu_gesamt: nach_jur.setdefault(n["jurisdiktion"], []).append(n)
        kopf = " · ".join(f"{k.upper()} {len(v)}" for k, v in sorted(nach_jur.items()))
        text = "\n".join(f"• [{n['jurisdiktion'].upper()}] {n['titel'][:90]}"
                         for n in neu_gesamt[:8])
        if len(neu_gesamt) > 8: text += f"\n… und {len(neu_gesamt)-8} weitere"
        sende(f"{len(neu_gesamt)} neue Treffer — {kopf}", text,
              url=neu_gesamt[0].get("url"), tag="eingang")
    return 0

if __name__ == "__main__":
    sys.exit(main())
