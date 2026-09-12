#!/usr/bin/env python3
"""Baut aus der App eine Einzeldatei fuer die Artifact-Vorschau.
Alles inline, kein Service Worker, Theme ueber data-theme (Artifact-Konvention)."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"

html = (APP / "index.html").read_text()
css  = (APP / "style.css").read_text()
js   = (APP / "app.js").read_text()
daten = (APP / "data.json").read_text()

# Artifact stempelt data-theme, die App nutzt data-thema
css = css.replace('data-thema="hell"', 'data-theme="light"').replace('data-thema="dunkel"', 'data-theme="dark"')
js  = js.replace('dataset.thema', 'dataset.theme').replace('"thema"', '"theme"') \
        .replace('r.dataset.theme==="dunkel"', 'r.dataset.theme==="dark"') \
        .replace('dunkelJetzt ? "hell" : "dunkel"', 'dunkelJetzt ? "light" : "dark"')

# Daten inline statt fetch
js = re.sub(r'fetch\("data\.json"\)\.then\(r=>r\.json\(\)\)\.then\(d=>\{',
            'Promise.resolve(window.__DATEN).then(d=>{', js)
js = re.sub(r'if\("serviceWorker" in navigator\)\s*\n\s*addEventListener\("load".*?\);', '', js, flags=re.S)
js = js.replace('<a href="fristen.ics" download>Fristen als Kalender</a>', '')

# Kopfbereich zwischen <body> und </body> herausloesen
koerper = re.search(r"<body>(.*)</body>", html, re.S).group(1)
koerper = re.sub(r'<script src="app\.js"></script>', "", koerper)
koerper = koerper.replace('<a href="fristen.ics" download>Fristen als Kalender</a>',
    '<span>Vorschaustand — die installierbare App mit Push entsteht beim Deploy</span>')

seite = f"""<title>KI-Recht Monitor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;450;500;600;700&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap">
<style>
{css}
/* Vorschau laeuft ohne Browser-Chrome im Artifact-Rahmen */
.kopf{{padding-top:0}}
.filter{{top:var(--kopfh)}}
</style>
{koerper}
<script>window.__DATEN = {daten};</script>
<script>
{js}
</script>
"""
ziel = ROOT / "docs" / "vorschau.html"
ziel.write_text(seite)
print(f"{ziel.relative_to(ROOT)} — {len(seite)//1024} KB")
