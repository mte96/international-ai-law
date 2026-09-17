const VERSION = "01535fdd29dd";
const CACHE = `ki-recht-${VERSION}`;
// Nur die Huelle. data.json steht ABSICHTLICH nicht hier: es wird ohnehin
// Netz-zuerst geholt und dabei in denselben Zwischenspeicher gelegt. Stuende
// es hier, laedt jedes Geraet die 9 MB beim Einrichten ein zweites Mal.
// weltkarte.json gehoert dazu: die Umrisse aendern sich nicht, und ohne sie
// zeigt die Weltraster-Ansicht offline nur die Liste.
const DATEIEN = ["./", "./index.html", "./style.css", "./app.js",
                 "./weltkarte.json", "./manifest.json", "./icons/icon.svg"];

self.addEventListener("install", e => {
  // Jede Datei einzeln: mit addAll laesst eine einzige fehlende Datei die
  // ganze Installation scheitern, und dann bliebe der alte Worker fuer immer
  // stehen. Was hier durchfaellt, wird spaeter aus dem Netz geholt.
  e.waitUntil(caches.open(CACHE).then(c =>
    Promise.all(DATEIEN.map(d => c.add(d).catch(() => {})))));
});

// KEIN skipWaiting beim Einrichten. Der neue Worker wartet, bis die Seite
// sagt, dass der Benutzer neu laden will - sonst raeumt activate() den
// Zwischenspeicher weg, waehrend die alte Seite noch daraus liest.
self.addEventListener("message", e => {
  if (e.data && e.data.typ === "uebernehmen") self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Netz zuerst, Zwischenspeicher als Rueckfall - fuer ALLES, nicht nur fuer
// data.json.
//
// Vorher stand hier Cache-zuerst fuer die Huelle. Das hatte zur Folge, dass
// index.html, app.js und style.css nie wieder aus dem Netz kamen, solange der
// alte Worker im Amt war: die Seite zeigte auf dem Telefon wochenalten Stand,
// obwohl der Server laengst die neue Fassung auslieferte, und niemand konnte
// das von aussen erkennen. Eine Rechtsdatenbank, die veralteten Stand zeigt,
// ist schlimmer als eine, die etwas langsamer laedt.
//
// Offline bleibt vollstaendig benutzbar: was einmal geladen wurde, liegt im
// Zwischenspeicher und wird ausgeliefert, sobald das Netz nicht antwortet.
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  if (new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(
    fetch(e.request)
      .then(r => {
        if (r && r.ok) {
          const k = r.clone();
          caches.open(CACHE).then(c => c.put(e.request, k));
        }
        return r;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match("./")))
  );
});

// Push: Der Tracker schickt {titel, text, url}
self.addEventListener("push", e => {
  let d = {titel: "KI-Recht", text: "Es hat sich etwas getan.", url: "./"};
  try { if (e.data) d = Object.assign(d, e.data.json()); } catch (_) {
    if (e.data) d.text = e.data.text();
  }
  e.waitUntil(self.registration.showNotification(d.titel, {
    body: d.text,
    icon: "icons/icon-192.png",
    badge: "icons/icon-192.png",
    tag: d.tag || "ki-recht",
    data: {url: d.url},
    requireInteraction: !!d.wichtig,
  }));
});

self.addEventListener("notificationclick", e => {
  e.notification.close();
  const ziel = (e.notification.data && e.notification.data.url) || "./";
  e.waitUntil(clients.matchAll({type: "window", includeUncontrolled: true}).then(ws => {
    for (const w of ws) if ("focus" in w) return w.focus().then(() => w.navigate && w.navigate(ziel));
    return clients.openWindow(ziel);
  }));
});
