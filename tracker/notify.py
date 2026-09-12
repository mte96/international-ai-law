#!/usr/bin/env python3
"""Benachrichtigung aufs Handy.

Kanaele, in dieser Reihenfolge, alle optional per Umgebungsvariable:
  NTFY_TOPIC     ntfy.sh - kostenlos, quelloffen, App fuer iOS und Android
  PUSHOVER_TOKEN + PUSHOVER_USER  - 5 USD einmalig, sehr zuverlaessig
  WEBHOOK_URL    beliebiger Endpunkt, bekommt JSON

Ohne gesetzte Variable wird nur auf die Konsole geschrieben - der Tracker
laeuft dann trotzdem und schreibt seinen Eingang in die Dateien.
"""
import json, os, sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def _post(url, daten, header=None, roh=False):
    koerper = daten if roh else json.dumps(daten).encode()
    kopf = {"Content-Type": "text/plain; charset=utf-8" if roh else "application/json"}
    kopf.update(header or {})
    try:
        with urlopen(Request(url, data=koerper, headers=kopf), timeout=15) as r:
            return 200 <= r.status < 300
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        print(f"  Versand fehlgeschlagen ({url.split('/')[2]}): {e}", file=sys.stderr)
        return False

def sende(titel, text, url=None, tag="ki-recht", prioritaet="normal"):
    gesendet = []

    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        server = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
        kopf = {"Title": titel.encode("utf-8").decode("latin-1", "replace"),
                "Tags": "scales", "Priority": {"hoch": "high", "normal": "default",
                                               "leise": "low"}.get(prioritaet, "default")}
        if url: kopf["Click"] = url
        if os.environ.get("NTFY_TOKEN"):
            kopf["Authorization"] = f"Bearer {os.environ['NTFY_TOKEN']}"
        if _post(f"{server}/{topic}", text.encode(), kopf, roh=True):
            gesendet.append("ntfy")

    pt, pu = os.environ.get("PUSHOVER_TOKEN"), os.environ.get("PUSHOVER_USER")
    if pt and pu:
        from urllib.parse import urlencode
        d = {"token": pt, "user": pu, "title": titel, "message": text,
             "priority": {"hoch": 1, "normal": 0, "leise": -1}.get(prioritaet, 0)}
        if url: d["url"] = url
        if _post("https://api.pushover.net/1/messages.json", urlencode(d).encode(),
                 {"Content-Type": "application/x-www-form-urlencoded"}, roh=True):
            gesendet.append("pushover")

    hook = os.environ.get("WEBHOOK_URL")
    if hook and _post(hook, {"titel": titel, "text": text, "url": url, "tag": tag}):
        gesendet.append("webhook")

    print(f"[{'+'.join(gesendet) if gesendet else 'nur Konsole'}] {titel}")
    if not gesendet:
        print(text)
    return bool(gesendet)

if __name__ == "__main__":
    sende(sys.argv[1] if len(sys.argv) > 1 else "Testmeldung",
          sys.argv[2] if len(sys.argv) > 2 else "Der Tracker kann senden.")
