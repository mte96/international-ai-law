#!/usr/bin/env python3
"""Sucht neue Fachliteratur über offene Schnittstellen und meldet Treffer.

Fragt OpenAlex, Semantic Scholar, arXiv, CrossRef und die Deutsche
Nationalbibliothek ab. Alle Dienste sind ohne Registrierung nutzbar;
OpenAlex und CrossRef bevorzugen eine Kontaktadresse im User-Agent
(Umgebungsvariable KONTAKT_MAIL), die sie mit höheren Limits belohnen.

Aufruf:
    python3 tracker/literatur.py                # faellige Profile
    python3 tracker/literatur.py --alle         # alle Profile
    python3 tracker/literatur.py --trocken      # zeigen, nichts speichern
    python3 tracker/literatur.py --profil ID    # ein Profil
    python3 tracker/literatur.py --seit 2026-01 # nur ab diesem Monat
"""
import argparse, json, os, re, sys, time
import datetime as dt
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import yaml

ROOT = Path(__file__).resolve().parent.parent
TR = ROOT / "tracker"
ZUSTAND = TR / "literatur_zustand.json"
EINGANG = TR / "eingang"
MAIL = os.environ.get("KONTAKT_MAIL", "")
UA = f"ai-law-literatur/1.0 (privates Rechtsmonitoring{'; mailto:'+MAIL if MAIL else ''})"

def hole(url, timeout=30):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def json_hole(url):
    try:
        return json.loads(hole(url))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        return {"_fehler": f"{type(e).__name__}: {e}"}

# ------------------------------------------------------------------ Dienste
def openalex(begriffe, seit, limit=25):
    """250 Mio. Werke, keine Registrierung, sehr gute Metadaten."""
    q = urlencode({
        "search": begriffe,
        "filter": f"from_publication_date:{seit}-01,type:article|preprint|book|book-chapter",
        "per-page": limit, "sort": "relevance_score:desc",
        **({"mailto": MAIL} if MAIL else {}),
    })
    d = json_hole(f"https://api.openalex.org/works?{q}")
    if "_fehler" in d: return [], d["_fehler"]
    out = []
    for w in d.get("results", []):
        ort = (w.get("primary_location") or {})
        quelle = (ort.get("source") or {}).get("display_name") or ""
        oa = (w.get("open_access") or {})
        out.append({
            "titel": w.get("title") or "",
            "autoren": [a.get("author", {}).get("display_name","")
                        for a in (w.get("authorships") or [])][:8],
            "jahr": w.get("publication_year"),
            "datum": w.get("publication_date") or "",
            "fundstelle": quelle,
            "doi": (w.get("doi") or "").replace("https://doi.org/",""),
            "openalex_id": (w.get("id") or "").rsplit("/",1)[-1],
            "url": oa.get("oa_url") or ort.get("landing_page_url") or "",
            "zugang": "open-access" if oa.get("is_oa") else "verlagsseite",
            "zitationen": w.get("cited_by_count", 0),
            "typ": {"article":"aufsatz","preprint":"working-paper",
                    "book":"monografie","book-chapter":"aufsatz"}.get(w.get("type"),"aufsatz"),
            "abstract": entpacke_abstract(w.get("abstract_inverted_index")),
            "dienst": "openalex",
        })
    return out, None

def entpacke_abstract(idx):
    """OpenAlex liefert Abstracts als invertierten Index."""
    if not isinstance(idx, dict): return ""
    positionen = {}
    for wort, stellen in idx.items():
        for s in stellen: positionen[s] = wort
    return " ".join(positionen[k] for k in sorted(positionen))[:1200]

def arxiv(begriffe, seit, limit=15):
    """Fuer die technisch-regulatorische Schnittstelle (cs.CY, cs.AI)."""
    q = quote(f'all:"{begriffe}" AND (cat:cs.CY OR cat:cs.AI OR cat:cs.LG)')
    try:
        xml = hole(f"http://export.arxiv.org/api/query?search_query={q}"
                   f"&sortBy=submittedDate&sortOrder=descending&max_results={limit}")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        return [], f"{type(e).__name__}: {e}"
    import xml.etree.ElementTree as ET
    NS = {"a": "http://www.w3.org/2005/Atom"}
    try: baum = ET.fromstring(xml)
    except ET.ParseError as e: return [], f"XML: {e}"
    out = []
    for e in baum.findall("a:entry", NS):
        t = lambda p: (e.findtext(p, "", NS) or "").strip()
        datum = t("a:published")[:10]
        if datum < f"{seit}-01": continue
        out.append({
            "titel": re.sub(r"\s+"," ", t("a:title")),
            "autoren": [a.findtext("a:name","",NS) for a in e.findall("a:author", NS)][:8],
            "jahr": int(datum[:4]) if datum[:4].isdigit() else None,
            "datum": datum, "fundstelle": "arXiv preprint",
            "doi": t("a:doi"), "url": t("a:id"),
            "zugang": "open-access", "typ": "working-paper",
            "abstract": re.sub(r"\s+"," ", t("a:summary"))[:1200],
            "zitationen": 0, "dienst": "arxiv",
        })
    return out, None

def crossref(begriffe, seit, limit=20):
    q = urlencode({"query.bibliographic": begriffe, "rows": limit,
                   "filter": f"from-pub-date:{seit}-01",
                   "sort": "relevance", **({"mailto": MAIL} if MAIL else {})})
    d = json_hole(f"https://api.crossref.org/works?{q}")
    if "_fehler" in d: return [], d["_fehler"]
    out = []
    for w in (d.get("message", {}) or {}).get("items", []):
        teile = (w.get("published", {}) or {}).get("date-parts", [[None]])[0]
        out.append({
            "titel": " ".join(w.get("title") or []),
            "autoren": [f"{a.get('family','')}, {a.get('given','')}".strip(", ")
                        for a in (w.get("author") or [])][:8],
            "jahr": teile[0] if teile else None,
            "datum": "-".join(f"{x:02d}" if i else str(x) for i,x in enumerate(teile) if x),
            "fundstelle": " ".join(w.get("container-title") or []),
            "doi": w.get("DOI",""), "url": w.get("URL",""),
            "zugang": "verlagsseite", "typ": "aufsatz",
            "abstract": re.sub(r"<[^>]+>","", w.get("abstract") or "")[:1200],
            "zitationen": w.get("is-referenced-by-count", 0), "dienst": "crossref",
        })
    return out, None

def dnb(begriffe, limit=20):
    """Deutsche Nationalbibliothek, SRU — findet Dissertationen und Monografien."""
    q = urlencode({"version":"1.1","operation":"searchRetrieve",
                   "query": f'WOE="{begriffe}"', "recordSchema":"MARC21-xml",
                   "maximumRecords": limit})
    try:
        xml = hole(f"https://services.dnb.de/sru/dnb?{q}")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        return [], f"{type(e).__name__}: {e}"
    import xml.etree.ElementTree as ET
    try: baum = ET.fromstring(xml)
    except ET.ParseError as e: return [], f"XML: {e}"
    M = "{http://www.loc.gov/MARC21/slim}"
    out = []
    for rec in baum.iter(f"{M}record"):
        felder = {}
        for df in rec.findall(f"{M}datafield"):
            tag = df.get("tag")
            for sf in df.findall(f"{M}subfield"):
                felder.setdefault(f"{tag}{sf.get('code')}", []).append(sf.text or "")
        titel = " : ".join(felder.get("245a",[]) + felder.get("245b",[]))
        if not titel: continue
        jahr = next((int(m.group()) for f in felder.get("264c",[])
                     if (m := re.search(r"\d{4}", f))), None)
        out.append({
            "titel": titel.strip(),
            "autoren": felder.get("100a",[]) + felder.get("700a",[])[:6],
            "jahr": jahr, "datum": str(jahr or ""),
            "fundstelle": " ".join(felder.get("264b",[])[:1]) or "Deutsche Nationalbibliothek",
            "isbn": (felder.get("020a") or [""])[0],
            "url": (felder.get("856u") or [""])[0],
            "zugang": "bibliothek", "typ": "dissertation" if any(
                "diss" in f.lower() for f in felder.get("502a",[])) else "monografie",
            "abstract": "", "zitationen": 0, "dienst": "dnb",
        })
    return out, None

DIENSTE = {"openalex": openalex, "arxiv": arxiv, "crossref": crossref, "dnb": dnb}

# ------------------------------------------------------------------ Lauf
def schluessel(t):
    if t.get("doi"): return "doi:" + t["doi"].lower()
    if t.get("openalex_id"): return "oa:" + t["openalex_id"]
    return "t:" + re.sub(r"\W+","", (t.get("titel") or "").lower())[:60]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alle", action="store_true")
    ap.add_argument("--trocken", action="store_true")
    ap.add_argument("--profil")
    ap.add_argument("--seit", default=None, help="JJJJ-MM, Standard: vor 6 Monaten")
    a = ap.parse_args()

    konf = yaml.safe_load((TR / "literatur_profile.yaml").read_text())
    profile = konf["profile"]
    if a.profil:
        profile = [p for p in profile if p["id"] == a.profil]
        if not profile: sys.exit(f"Profil '{a.profil}' nicht gefunden")

    seit = a.seit or (dt.date.today() - dt.timedelta(days=185)).strftime("%Y-%m")
    zustand = json.loads(ZUSTAND.read_text()) if ZUSTAND.exists() else {"gesehen": [], "profile": {}}
    gesehen = set(zustand.get("gesehen", []))
    jetzt = time.time()
    neu, fehler, uebersprungen = [], [], 0

    for p in profile:
        letzte = zustand["profile"].get(p["id"], 0)
        if not (a.alle or a.profil) and (jetzt - letzte) < 6*24*3600:
            uebersprungen += 1; continue
        erstlauf = not letzte
        for dienstname in p.get("dienste", ["openalex"]):
            fn = DIENSTE.get(dienstname)
            if not fn: continue
            args = (p["suche"],) if dienstname == "dnb" else (p["suche"], seit)
            treffer, fehl = fn(*args)
            if fehl: fehler.append((p["id"], dienstname, fehl)); continue
            for t in treffer:
                s = schluessel(t)
                if s in gesehen: continue
                gesehen.add(s)
                if erstlauf: continue
                neu.append({**t, "profil": p["id"], "themenachsen": p.get("themenachsen", []),
                            "streitstaende": p.get("streitstaende", [])})
            time.sleep(0.4)   # hoeflich bleiben
        zustand["profile"][p["id"]] = jetzt
        if erstlauf: fehler.append((p["id"], "-", "Erstlauf: Zustand gesetzt, nichts gemeldet"))

    print(f"{len(profile)-uebersprungen} Profile abgefragt, {uebersprungen} nicht fällig")
    print(f"{len(neu)} neue Titel")
    for f in fehler[:12]: print(f"  {f[0]} / {f[1]}: {f[2][:90]}")

    if a.trocken:
        for t in neu[:25]:
            print(f"  [{t.get('jahr')}] {t['titel'][:88]}")
            print(f"        {', '.join(t['autoren'][:3])} — {t.get('fundstelle','')[:60]}")
        return 0

    zustand["gesehen"] = list(gesehen)[-8000:]
    ZUSTAND.write_text(json.dumps(zustand, ensure_ascii=False))

    if neu:
        EINGANG.mkdir(exist_ok=True)
        datei = EINGANG / f"{dt.date.today().isoformat()}-literatur.md"
        zeilen = [f"# Neue Literatur {dt.date.today().isoformat()}\n"]
        nach_profil = {}
        for t in neu: nach_profil.setdefault(t["profil"], []).append(t)
        for prof, ts in nach_profil.items():
            zeilen.append(f"\n## {prof}\n")
            for t in ts:
                zeilen.append(f"\n**{t['titel']}**  ")
                zeilen.append(f"{', '.join(t['autoren'][:4])} — {t.get('fundstelle','')} ({t.get('jahr')})  ")
                if t.get("doi"): zeilen.append(f"doi:{t['doi']}  ")
                if t.get("url"): zeilen.append(f"{t['url']}  ")
                if t.get("zitationen"): zeilen.append(f"zitiert: {t['zitationen']}  ")
                if t.get("abstract"): zeilen.append(f"\n> {t['abstract'][:320]}\n")
        datei.write_text("\n".join(zeilen))
        print(f"-> {datei.relative_to(ROOT)}")

        sys.path.insert(0, str(TR))
        from notify import sende
        top = sorted(neu, key=lambda t: -(t.get("zitationen") or 0))[:6]
        text = "\n".join(f"• {t['titel'][:88]}" for t in top)
        if len(neu) > 6: text += f"\n… und {len(neu)-6} weitere"
        sende(f"{len(neu)} neue Titel zum KI-Recht", text, tag="literatur")
    return 0

if __name__ == "__main__":
    sys.exit(main())
