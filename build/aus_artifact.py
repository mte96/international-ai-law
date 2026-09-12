#!/usr/bin/env python3
"""Zerlegt eine veröffentlichte Artifact-Seite wieder in ihre Bestandteile
und baut sie daraus neu zusammen.

Die veröffentlichte Seite trägt alles in sich: Daten, Stile und Logik.
Damit ist sie selbst der Speicher — eine Session ohne Repo kann sie lesen,
die Daten ändern und die Seite neu veröffentlichen.

    python3 build/aus_artifact.py zerlegen  seite.html  ordner/
    python3 build/aus_artifact.py bauen     ordner/     seite_neu.html
"""
import json, re, sys
from pathlib import Path

MARKE_DATEN = "window.__DATEN = "

def zerlegen(seite: Path, ziel: Path):
    html = seite.read_text()
    ziel.mkdir(parents=True, exist_ok=True)

    m = re.search(r"<script>window\.__DATEN = (\{.*?\});</script>", html, re.S)
    if not m:
        sys.exit("Kein Datenblock gefunden — ist das eine Seite dieses Projekts?")
    daten = json.loads(m.group(1))
    (ziel / "data.json").write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")))

    stile = re.search(r"<style>\n(.*?)\n</style>", html, re.S)
    (ziel / "style.css").write_text(stile.group(1) if stile else "")

    skripte = re.findall(r"<script>\n(.*?)\n</script>", html, re.S)
    (ziel / "app.js").write_text(skripte[-1] if skripte else "")

    kopf = html[:m.start()]
    koerper = re.sub(r"<script>window\.__DATEN.*", "", kopf, flags=re.S)
    koerper = re.sub(r"<style>.*?</style>", "<!--STILE-->", koerper, flags=re.S)
    (ziel / "geruest.html").write_text(koerper)

    s = daten.get("statistik", {})
    print(f"Zerlegt nach {ziel}/")
    print(f"  data.json      {len(json.dumps(daten))//1024} KB — "
          f"{s.get('regelwerke',0)} Regelwerke, {s.get('urteile',0)} Entscheidungen, "
          f"{s.get('literatur',0)} Titel, {s.get('streitstaende',0)} Streitstände")
    print(f"  style.css      {len(stile.group(1))//1024 if stile else 0} KB")
    print(f"  app.js         {len(skripte[-1])//1024 if skripte else 0} KB")
    print(f"  geruest.html   {len(koerper)//1024} KB")

def bauen(quelle: Path, ziel: Path):
    daten = json.loads((quelle / "data.json").read_text())
    geruest = (quelle / "geruest.html").read_text()
    css = (quelle / "style.css").read_text()
    js  = (quelle / "app.js").read_text()
    seite = geruest.replace("<!--STILE-->", f"<style>\n{css}\n</style>")
    seite += (f"<script>{MARKE_DATEN}"
              f"{json.dumps(daten, ensure_ascii=False, separators=(',', ':'))};</script>\n"
              f"<script>\n{js}\n</script>\n")
    ziel.write_text(seite)
    print(f"Gebaut: {ziel} ({len(seite)//1024} KB)")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    befehl, a, b = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    {"zerlegen": lambda: zerlegen(a, b), "bauen": lambda: bauen(a, b)}.get(
        befehl, lambda: sys.exit(f"Unbekannt: {befehl}"))()
