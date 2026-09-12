# -*- coding: utf-8 -*-
"""Erzeugt app/weltkarte.json aus dem TopoJSON von world-atlas
(Natural Earth 110m, gemeinfrei; Paket ISC, Mike Bostock).

Projektion: Equal Earth (Savric/Patterson/Jenny 2018) - flaechentreu, damit
kein Land groesser aussieht, als es ist.

Ergebnis je Kennung: d = SVG-Pfad, x/y = Sichtpunkt, klein = zu klein zum
Anklicken (die App setzt dann einen Punkt)."""
import json, math, pycountry, sys

t = json.load(open("package/countries-110m.json"))
sx, sy = t["transform"]["scale"]; tx, ty = t["transform"]["translate"]

def arc(i):
    x = y = 0; out = []
    for dx, dy in t["arcs"][i]:
        x += dx; y += dy; out.append((x*sx+tx, y*sy+ty))
    return out

def ring(idxs):
    pts = []
    for i in idxs:
        seg = arc(~i)[::-1] if i < 0 else arc(i)
        pts.extend(seg if not pts else seg[1:])
    return pts

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
M = math.sqrt(3)/2
def proj(lon, lat):
    lam = math.radians(max(-180, min(180, lon)))
    phi = math.radians(max(-90, min(90, lat)))
    th  = math.asin(max(-1, min(1, M*math.sin(phi))))
    t2, t6, t8 = th*th, th**6, th**8
    x = 2*math.sqrt(3)*lam*math.cos(th)/(3*(9*A4*t8 + 7*A3*t6 + 3*A2*t2 + A1))
    return x, -(A4*th**9 + A3*th**7 + A2*th**3 + A1*th)

def trenne(pts):
    """Natural Earth naeht Russland und Fidschi ueber den 180. Laengengrad
    zusammen. Ungetrennt zieht das in einer pseudozylindrischen Projektion
    einen Balken quer ueber die Karte. Also am Sprung schneiden."""
    stuecke = [[]]
    for i, p in enumerate(pts):
        if i and abs(p[0] - pts[i-1][0]) > 180: stuecke.append([])
        stuecke[-1].append(p)
    return [s for s in stuecke if len(s) >= 4]

def dp(pts, eps):
    if len(pts) < 3: return pts
    dmax = 0.0; idx = 0
    (x1,y1), (x2,y2) = pts[0], pts[-1]
    dx, dy = x2-x1, y2-y1; nn = dx*dx + dy*dy
    for i in range(1, len(pts)-1):
        px, py = pts[i]
        if nn == 0: d = math.hypot(px-x1, py-y1)
        else:
            u = max(0.0, min(1.0, ((px-x1)*dx + (py-y1)*dy)/nn))
            d = math.hypot(px-(x1+u*dx), py-(y1+u*dy))
        if d > dmax: dmax, idx = d, i
    if dmax > eps: return dp(pts[:idx+1], eps)[:-1] + dp(pts[idx:], eps)
    return [pts[0], pts[-1]]

def flaeche(p):
    s = 0.0
    for i in range(len(p)):
        x1,y1 = p[i]; x2,y2 = p[(i+1) % len(p)]
        s += x1*y2 - x2*y1
    return abs(s)/2

EPS      = 0.0018
MIN_INSEL = 0.0004   # kleinere Nebeninseln fallen weg
KLEIN     = 0.0009   # darunter bekommt das Land zusaetzlich einen Punkt

# Laender ohne Polygon im 110m-Datensatz: Sichtpunkt von Hand (Laenge, Breite)
OHNE = {"sg": (103.8, 1.35), "mt": (14.4, 35.9), "bh": (50.6, 26.1),
        "mu": (57.55, -20.3), "lu": (6.13, 49.8)}
NAMEN = {"sg": "Singapore", "mt": "Malta", "bh": "Bahrain",
         "mu": "Mauritius", "lu": "Luxembourg"}

karte = {}
for f in t["objects"]["countries"]["geometries"]:
    fid = f.get("id")
    if not fid: continue
    c = pycountry.countries.get(numeric=str(fid).zfill(3))
    if not c: continue
    code = c.alpha_2.lower()
    if code == "gb": code = "uk"
    polys = f["arcs"] if f["type"] == "MultiPolygon" else [f["arcs"]]
    teile = []; gesamt = 0.0; groesster = (0.0, None)
    for poly in polys:
        for st in trenne(ring(poly[0])):
            aussen = [proj(*p) for p in st]
            a = flaeche(aussen)
            if a < MIN_INSEL: continue
            v = dp(aussen, EPS)
            if len(v) < 4: continue
            teile.append(v); gesamt += a
            if a > groesster[0]: groesster = (a, v)
        for r in poly[1:]:                       # Loecher (Lesotho, Vatikan)
            for st in trenne(ring(r)):
                h = [proj(*p) for p in st]
                if flaeche(h) < MIN_INSEL: continue
                hv = dp(h, EPS)
                if len(hv) >= 4: teile.append(hv)
    if not teile:                                # alles unter der Schwelle:
        aussen = [proj(*p) for p in trenne(ring(polys[0][0]))[0]]  # groebsten Ring behalten
        teile = [dp(aussen, EPS/3)]; gesamt = flaeche(aussen); groesster = (gesamt, teile[0])
    v = groesster[1] or teile[0]
    karte[code] = {
        "d": "".join("M" + "L".join(f"{x:.3f} {y:.3f}" for x, y in p) + "Z" for p in teile),
        "x": round(sum(p[0] for p in v)/len(v), 3),
        "y": round(sum(p[1] for p in v)/len(v), 3),
        "n": f["properties"]["name"],
    }
    if gesamt < KLEIN: karte[code]["klein"] = 1

for code, (lon, lat) in OHNE.items():
    if code in karte: continue
    x, y = proj(lon, lat)
    karte[code] = {"d": "", "x": round(x,3), "y": round(y,3),
                   "n": NAMEN[code], "klein": 1}

xs = [k["x"] for k in karte.values()]; ys = [k["y"] for k in karte.values()]
print(f"{len(karte)} Laender | x {min(xs):.2f}..{max(xs):.2f}  y {min(ys):.2f}..{max(ys):.2f}",
      file=sys.stderr)
print("klein:", sorted(k for k,v in karte.items() if v.get("klein")), file=sys.stderr)
karte.pop("aq", None)          # Antarktis: kein staatliches Recht
aus = {"_quelle": "Natural Earth 1:110m Admin-0 (gemeinfrei) ueber world-atlas 2.0.2 "
                  "(ISC, Mike Bostock); Projektion Equal Earth; erzeugt von build/weltkarte.py",
       "_feld": ["pfad", "x", "y", "name", "klein"]}
for c, v in sorted(karte.items()):
    aus[c] = [v["d"], v["x"], v["y"], v["n"]] + ([1] if v.get("klein") else [])
json.dump(aus, sys.stdout, ensure_ascii=False, separators=(",", ":"))
