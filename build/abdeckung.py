#!/usr/bin/env python3
"""Misst je Rechtsordnung, wie vollstaendig sie erfasst ist.

Vollstaendigkeit ist nicht objektiv messbar — niemand kennt die Grundmenge.
Gemessen wird deshalb die *Schichtdichte*: Welche der sechs Ebenen, aus denen
ein belastbares Landesdossier besteht, sind besetzt und wie gut belegt?

  1 Regelwerke      Gesetze, Verordnungen, Entwuerfe
  2 Dokumente       Verfahrensakten dazu, amtlich belegt
  3 Rechtsprechung  Entscheidungen, am Dokument geprueft
  4 Normebene       Zugriff auf Vorschriftenebene statt nur Regelwerksebene
  5 Fristen         Stichtage mit amtlicher Fundstelle
  6 Literatur       Sekundaerliteratur zur Rechtsordnung

Der Prozentwert ist ein Reifegrad, keine Aussage ueber die Grundmenge.
"""
import sys, collections
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quellenart import art

ROOT = Path(__file__).resolve().parent.parent
tax = yaml.safe_load((ROOT / "schema/taxonomie.yaml").read_text(encoding="utf-8"))
NAME = {j["id"]: j["name"] for j in tax["jurisdiktionen"]}
TIER = {j["id"]: j.get("tier", 4) for j in tax["jurisdiktionen"]}


def lade(muster, schluessel):
    for p in sorted(ROOT.glob(muster)):
        for e in (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get(schluessel) or []:
            yield e


rw = list(lade("data/regelwerke/**/*.yaml", "regelwerke"))
ur = list(lade("data/urteile/**/*.yaml", "urteile"))
li = list(lade("data/literatur/**/*.yaml", "literatur"))
fr = list(lade("data/fristen/**/*.yaml", "fristen"))
no = list(lade("data/normen/*.yaml", "normen"))
rw_jur = {r["id"]: r.get("jurisdiktion") for r in rw}

st = collections.defaultdict(lambda: collections.Counter())
for r in rw:
    j = r.get("jurisdiktion")
    st[j]["regelwerke"] += 1
    dok = r.get("dokumente") or []
    st[j]["dok"] += len(dok)
    st[j]["dok_amtlich"] += sum(1 for d in dok if art(d.get("url")) == "amtlich")
for u in ur:
    j = u.get("jurisdiktion")
    st[j]["urteile"] += 1
    if u.get("verifiziert") and art(u.get("volltext_url")) == "amtlich":
        st[j]["urteile_gut"] += 1
for n in no:
    j = rw_jur.get(n.get("regelwerk"))
    if j:
        st[j]["normen"] += 1
for f in fr:
    j = f.get("jurisdiktion")
    st[j]["fristen"] += 1
    if art(f.get("quelle")) == "amtlich":
        st[j]["fristen_amtlich"] += 1
for l in li:
    for j in l.get("jurisdiktionen") or []:
        st[j]["literatur"] += 1


def reife(s):
    """Sechs Ebenen, je bis zu 100/6 Punkte. Voll besetzt heisst nicht
    vollstaendig — es heisst, die Ebene traegt."""
    p = 0.0
    p += min(s["regelwerke"] / 8, 1) * 20                       # Regelwerke
    p += (s["dok_amtlich"] / s["dok"] if s["dok"] else 0) * 20  # Belegdichte
    p += min(s["urteile"] / 10, 1) * 15                         # Rechtsprechung
    p += (s["urteile_gut"] / s["urteile"] if s["urteile"] else 0) * 15  # Pruefstand
    p += min(s["normen"] / 15, 1) * 15                          # Normebene
    p += min(s["fristen"] / 5, 1) * 7.5                         # Fristen
    p += min(s["literatur"] / 15, 1) * 7.5                      # Literatur
    return round(p)


print("\nREIFEGRAD JE RECHTSORDNUNG")
print("=" * 92)
print(f"  {'':4} {'Rechtsordnung':<26} {'Reife':>5}  {'RW':>4} {'Dok':>5} {'amtl':>5} "
      f"{'Urt':>4} {'gut':>4} {'Norm':>5} {'Frist':>5} {'Lit':>4}")
print("-" * 92)
zeilen = sorted(st.items(), key=lambda kv: -reife(kv[1]))
for j, s in zeilen:
    if not j:
        continue
    r = reife(s)
    bal = "█" * (r // 10) + "░" * (10 - r // 10)
    print(f"  T{TIER.get(j,4)}  {NAME.get(j,j)[:26]:<26} {bal} {r:>3}%  "
          f"{s['regelwerke']:>4} {s['dok']:>5} "
          f"{(s['dok_amtlich']*100//s['dok'] if s['dok'] else 0):>4}% "
          f"{s['urteile']:>4} {s['urteile_gut']:>4} {s['normen']:>5} "
          f"{s['fristen']:>5} {s['literatur']:>4}")

print("\n  RW = Regelwerke | Dok = Verfahrensdokumente | amtl = davon amtlich belegt")
print("  Urt = Entscheidungen | gut = amtlich belegt UND geprueft | Norm = Vorschriften")
print("\n  Der Reifegrad misst, ob die sechs Ebenen tragen — nicht, ob die")
print("  Grundmenge erschoepft ist. 100 % heisst: dicht genug zum Arbeiten.")
