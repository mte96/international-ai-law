#!/usr/bin/env python3
"""Misst, wie gut der Bestand durch amtliche Quellen gesichert ist.

Legt denselben Massstab an alle Bestandteile an: Fuehrt der hinterlegte
Verweis zum amtlichen Dokument, zu einer Rechtsdatenbank, zu etwas
Sekundaerem — oder fehlt er?

    python3 build/guete.py            # Bericht
    python3 build/guete.py --knapp    # nur die Kopfzahlen
"""
import sys, glob, collections
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quellenklasse import klasse as art   # Einstufung an einer Stelle, s. quellenklasse.py

ROOT = Path(__file__).resolve().parent.parent


def lade(muster, schluessel):
    for p in sorted(ROOT.glob(muster)):
        for e in (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get(schluessel) or []:
            yield e


def balken(z, gesamt, breite=34):
    if not gesamt:
        return ""
    voll = round(z["amtlich"] / gesamt * breite)
    db = round(z["datenbank"] / gesamt * breite)
    rest = breite - voll - db
    return "█" * voll + "▓" * db + "░" * max(rest, 0)


def zeile(name, z, gesamt):
    if not gesamt:
        return
    a = z["amtlich"] * 100 // gesamt
    print(f"  {name:<26} {balken(z, gesamt)}  {a:>3}%  amtlich   "
          f"({z['amtlich']}/{gesamt}, Datenbank {z['datenbank']}, "
          f"sekundaer {z['sekundaer']}, ohne {z['fehlt']})")


def zaehle(urls):
    z = collections.Counter({"amtlich": 0, "datenbank": 0, "sekundaer": 0, "fehlt": 0})
    for u in urls:
        z[art(u)] += 1
    return z


print("\nGUETE DES BESTANDES — amtliche Absicherung")
print("=" * 78)
print("  █ amtlich   ▓ Rechtsdatenbank   ░ sekundaer oder ohne Verweis\n")

# --- Regelwerke: die Dokumente sind der Beleg -------------------------
rw = list(lade("data/regelwerke/**/*.yaml", "regelwerke"))
dok = [d.get("url") for r in rw for d in (r.get("dokumente") or [])]
z_dok = zaehle(dok)
zeile("Verfahrensdokumente", z_dok, len(dok))
ohne_dok = len([r for r in rw if not (r.get("dokumente") or [])])
mit_amtlich = len([r for r in rw
                   if any(art(d.get("url")) == "amtlich" for d in (r.get("dokumente") or []))])
print(f"  {'Regelwerke mit Beleg':<26} {mit_amtlich}/{len(rw)} tragen mindestens ein "
      f"amtliches Dokument; {ohne_dok} ohne jedes Dokument")

# --- Entscheidungen ---------------------------------------------------
ur = list(lade("data/urteile/**/*.yaml", "urteile"))
z_ur = zaehle([u.get("volltext_url") for u in ur])
zeile("Entscheidungen", z_ur, len(ur))
hoch = [u for u in ur if u.get("bedeutung") == "hoch"]
zeile("  davon hohe Bedeutung", zaehle([u.get("volltext_url") for u in hoch]), len(hoch))

# --- Fristen ----------------------------------------------------------
# Zwei Arten mit verschiedenen Massstaeben: Bei einer Rechtsfrist ist die
# amtliche Quelle der Beleg, bei einer Bewerbungs- oder Veranstaltungsfrist
# ist die Seite des Veranstalters selbst die Primaerquelle.
recht, termin = [], []
for pf in sorted(ROOT.glob("data/fristen/**/*.yaml")):
    posten = (yaml.safe_load(pf.read_text(encoding="utf-8")) or {}).get("fristen") or []
    # Alles in lernen.yaml ist Kurs- oder Veranstaltungstermin, unabhaengig vom typ.
    ziel = termin if pf.name == "lernen.yaml" else recht
    for f in posten:
        (termin if f.get("typ") == "einreichung" else ziel).append(f)
fr = recht + termin
zeile("Rechtsfristen", zaehle([f.get("quelle") for f in recht]), len(recht))
z_te = zaehle([f.get("quelle") for f in termin])
print(f"  {'Termin- und Bewerbungsfristen':<26} "
      f"{(len(termin)-z_te['fehlt'])*100//max(len(termin),1):>3}%  verlinkt   "
      f"({len(termin)-z_te['fehlt']}/{len(termin)}; hier ist der Veranstalter die Quelle)")

# --- Literatur --------------------------------------------------------
li = list(lade("data/literatur/**/*.yaml", "literatur"))
z_li = zaehle([l.get("url") for l in li])
print(f"  {'Literatur':<26} {balken(z_li, len(li))}  "
      f"{(len(li)-z_li['fehlt'])*100//len(li):>3}%  verlinkt   "
      f"({len(li)-z_li['fehlt']}/{len(li)}; bei Literatur ist der Verlag die Quelle, "
      f"nicht ein Amt)")

# --- Weltraster und Lernangebote -------------------------------------
we = list(lade("data/weltraster/*.yaml", "laender"))
zeile("Weltraster", zaehle([w.get("url") for w in we]), len(we))
le = list(lade("data/lernen/*.yaml", "angebote"))
if le:
    z_le = zaehle([a.get("url") for a in le])
    print(f"  {'Lernangebote':<26} {balken(z_le, len(le))}  "
          f"{(len(le)-z_le['fehlt'])*100//len(le):>3}%  verlinkt   ({len(le)-z_le['fehlt']}/{len(le)})")

if "--knapp" in sys.argv:
    sys.exit()

# --- Pruefstand der Entscheidungen ------------------------------------
print("\n" + "=" * 78)
print("PRUEFSTAND DER ENTSCHEIDUNGEN")
print("=" * 78)
v = len([u for u in ur if u.get("verifiziert")])
zw = len([u for u in ur if u.get("zweifelhaft")])
vh = len([u for u in hoch if u.get("verifiziert")])
gold = len([u for u in hoch if u.get("verifiziert") and art(u.get("volltext_url")) == "amtlich"])
print(f"  am Dokument geprueft            {v:>4}/{len(ur)}  ({v*100//len(ur)} %)")
print(f"  davon hohe Bedeutung            {vh:>4}/{len(hoch)}  ({vh*100//len(hoch)} %)")
print(f"  amtlich belegt UND geprueft     {gold:>4}/{len(hoch)}  ({gold*100//len(hoch)} %)"
      f"   <- zitierfaehig")
print(f"  als zweifelhaft gekennzeichnet  {zw:>4}")

# --- Schwaechste Stellen ---------------------------------------------
print("\n" + "=" * 78)
print("WO ES FEHLT — Entscheidungen hoher Bedeutung ohne amtliche Fundstelle")
print("=" * 78)
luecke = [u for u in hoch if art(u.get("volltext_url")) != "amtlich"]
nach_jur = collections.Counter(u.get("jurisdiktion") for u in luecke)
for j, n in nach_jur.most_common():
    ids = [u["id"] for u in luecke if u.get("jurisdiktion") == j]
    print(f"  {j:<4} {n:>2}   {', '.join(ids[:4])}{' ...' if len(ids) > 4 else ''}")
print(f"\n  {len(luecke)} von {len(hoch)}")
