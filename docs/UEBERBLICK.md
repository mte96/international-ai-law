# Was hier gebaut worden ist

*English version: [OVERVIEW.md](OVERVIEW.md)*

Stand: 12. September 2026

## In einem Absatz

Eine strukturierte Datenbasis zum internationalen KI-Recht, aus der eine
durchsuchbare App gebaut wird, mit einem Beobachtungsdienst, der zweimal
täglich amtliche Quellen abruft. Nicht eine Sammlung von Links, sondern ein
Modell des Rechtsgebiets: Gesetze, die einzelnen Vorschriften darin,
Entscheidungen, die daran hängen, Literatur, die sie kommentiert — und quer
über allem die ungeklärten Rechtsfragen, an denen sich das Material sortiert.

## Der Bestand

| | |
|---|---|
| Regelwerke | **861** aus 50 Rechtsordnungen |
| Verfahrensdokumente | **2040**, 71 % mit amtlicher Adresse, 51 % am Dokument geprüft |
| Einzelvorschriften (Normebene) | **2068** |
| Entscheidungen | **418**, davon 223 von hoher Bedeutung |
| Streitstände | **24** mit **194** Positionen |
| Literatur | **558** Titel, 84 % verlinkt |
| Fristen | **295** Rechtsfristen, zu 87 % amtlich belegt |
| Weltraster | **87** Staaten gesichtet |

## Die sechs Ebenen

Das Besondere ist nicht die Menge, sondern dass die Ebenen miteinander
verbunden sind.

**1. Regelwerk** — ein Gesetz, eine Verordnung, ein Entwurf. Mit
Verfahrensstand, Inkrafttreten (bei 606 von 861 am amtlichen Text geprüft),
gestaffelten Anwendungsdaten, Regelungsschwerpunkten und den
Verfahrensdokumenten.

**2. Vorschrift** — die einzelne Norm als eigenständiges Objekt. Das ist der
Zugriff, den kein Tracker und keine Kanzleiübersicht bietet: „alles zu
§ 44b UrhG" oder „alles zu Art. 50 KI-VO" über alle Rechtsordnungen hinweg.
**Einschränkung, die man kennen muss:** Von den 2068 Vorschriften tragen nur
**665** einen eigenen Inhalt und einen amtlichen Textlink. Die übrigen 1403
sind Verweise — id, Regelwerk, Bezeichnung, Thema — und taugen zum Verknüpfen
und Filtern, nicht zum Lesen.

**3. Entscheidung** — mit Rubrum, Aktenzeichen, Tenor, tragenden Gründen und
der Fundstelle. 61 % führen einen amtlichen Volltext, bei hoher Bedeutung
72 %; weitere 12 % hängen an einer Rechtsdatenbank, die den Text führt, aber
nicht die Urschrift ist. Was nicht am Dokument geprüft ist, trägt einen Prüfvermerk, der sagt,
was fehlt.

**4. Streitstand** — die ungeklärte Rechtsfrage, mit den einander
widersprechenden Positionen, den Gerichten, die sie vertreten, den tragenden
Argumenten und einer Auflösungsprognose. **Das ist der eigentliche Ertrag.**
Eine Entscheidung ist ein Datum; ein Streitstand ist eine Einsicht.

**5. Literatur** — mit Kernthese, eigener Bewertung und Verknüpfung zu den
Streitständen, die sie berührt.

**6. Frist** — Stichtage mit amtlicher Fundstelle, Vorwarnung und
Kalenderausgabe.

## Wofür es taugt

**Eine Frage rechtsordnungsübergreifend beantworten.** „Wie wird die
Verletzung eines maschinenlesbaren Nutzungsvorbehalts behandelt?" —
Italien kriminalisiert sie (Art. 26 Legge 132/2025), Kasachstan macht sie
formatscharf (XML, JSON, RDF, CSV, YAML), Deutschland streitet vor dem BGH
darüber, was „maschinenlesbar" heißt. Das steht in einem Streitstand
nebeneinander, mit Fundstellen.

**Den Stand einer Frage in fünf Minuten erfassen.** Wer hat entschieden, wer
nicht, was ist anhängig, wann fällt die Entscheidung — und woran man es
erkennen wird.

**Belegen statt behaupten.** Jeder Eintrag führt eine Fundstelle oder sagt,
dass ihm eine fehlt. Für eine Veröffentlichung, einen Vortrag oder ein Video
ist das die Grundlage, ohne die alles andere Behauptung bleibt.

**Nichts verpassen.** 51 aktive Quellen werden zweimal täglich abgerufen,
29 Literaturprofile durchsucht, Fristen mit Vorwarnung gemeldet.

## Wie gut es ist — ehrlich

**Stark:** die Verknüpfung der Ebenen; die Belegdichte bei den
Rechtsfristen (87 % amtlich) und bei den Entscheidungen hoher Bedeutung
(76 %); die Streitstände; die Breite (50 Rechtsordnungen, darunter zwölf,
die in westlichen Übersichten nicht vorkommen); und dass jeder Eintrag
sagt, was ihm fehlt — 1850 benannte offene Punkte sind kein Mangel, sondern
das Gegenteil eines geglätteten Bestandes.

**Schwach:**

- **111 Entscheidungen ohne belastbare Fundstelle** (26 %), davon 38 von
  hoher Bedeutung. Ursache sind fast immer gesperrte Gerichtsportale.
- **255 Regelwerke ohne geprüftes Inkrafttreten.** Die gemessene Fehlerquote
  bei der Prüfung lag bei **17 %** — von 166 geprüften Daten waren 29 falsch
  oder erfunden. Was ungeprüft ist, ist mit dieser Quote zu lesen.
- **Der Tracker beobachtet nur zwölf von 50 Rechtsordnungen.** Für die
  übrigen 38 gibt es keine laufende Beobachtung; sie altern.
- **Die Vollständigkeit ist bei den zuletzt erfassten Rechtsordnungen
  unsicher.** Die Recherche im September lief ohne Suchmaschine, allein über
  direkt angesteuerte Portale.
- **Das Weltraster ist nur zu 22 % amtlich belegt** — es ist eine Landkarte,
  keine Prüfung, und war nie als eine gedacht.
- **Die Normebene ist zu 68 % leer.** 1403 von 2068 Vorschriften sind bloße
  Verweise ohne Text und ohne Link. Wer aus der Datenbasis heraus eine
  Vorschrift lesen will, kann das bei 665 tun.
- **Der Bestand speichert Analyse, nicht Erzählung.** `ergebnis` (405
  Einträge, im Mittel 710 Zeichen) und `eigene_bewertung` (1004, 733 Zeichen)
  tragen die Substanz; einen ausgeschriebenen Sachverhalt führen 160
  Einträge, einen förmlichen Leitsatz 23. Für ein erzählendes Format ist der
  Sachverhalt je Fall aus dem Volltext nachzulesen; der Volltextlink ist
  bei 61 % der Entscheidungen da.

**Was der Reifegrad je Rechtsordnung nicht sagt:** Er misst, ob die sechs
Ebenen tragen, nicht welchen Anteil der Grundmenge wir haben. Niemand kennt
die Grundmenge. „Nigeria 50 %" heißt: die Regelwerke stehen und sind belegt,
Entscheidungen und Normebene fehlen. Es heißt nicht, dass die Hälfte der
nigerianischen KI-Gesetze fehlt.

## Die Werkzeuge

**Prüfung:** `schema/validate.py` (Vokabular, ids, tote Verweise),
`build/fremdumlaut.py` (verfälschte Umlaute in beide Sprachrichtungen),
`build/quellenart.py` (Belastbarkeit jeder Fundstelle),
`build/guete.py` (amtliche Absicherung je Bestandteil),
`build/abdeckung.py` (Reifegrad je Rechtsordnung).

**Bau:** `build/build.py` (Datenbasis → App-Daten),
`build/artifact.py` (App-Daten → eigenständige Seitendatei),
`build/aus_artifact.py` (Seitendatei → Bestandteile, für Sitzungen ohne Repo),
`build/uebernehmen.py` (Seitendatei → Datenbasis, schließt den Rückweg).

**Einspielen:** `build/einspielen.py` (Recherchedatei → Datenbasis),
`build/einspielen_inkrafttreten.py`, `build/einspielen_streitstaende.py`
(prüft jede id, bevor irgendetwas geschrieben wird).

**Beobachtung:** `tracker/watch.py` (Quellen), `tracker/literatur.py`
(Profile), `tracker/fristen.py` (Vorwarnung), `tracker/pruefe_quellen.py`
(Selbsttest), Benachrichtigung über ntfy. Läuft über GitHub Actions,
06:00 und 18:00 UTC.

**Automatik:** ein wöchentlicher Lauf, der den Bestand aktuell hält, ohne
ihn zu verbreitern.

## Wo es liegt

- **Das Repo:** die YAML-Datenbasis in `data/`, das Datenmodell in
  `schema/`, die Werkzeuge in `build/`, der Beobachtungsdienst in
  `tracker/`.
- **Die App:** wird mit `build/build.py` aus `app/` gebaut und über einen
  lokalen Server geöffnet; sie trägt Daten, Stile und Logik in sich.
- **Die Zugangswege** zu den Gerichts- und Amtsportalen stehen in
  `docs/ZUGANGSWEGE.md` — welche tragen, welche sperren und wie.

## Die drei Regeln, an denen alles hängt

1. **`volltext_url` nur bei amtlichem Volltext.** Presse, Kanzleiseiten und
   Trackerportale gehören in `sekundaerquelle_url`.
2. **Lieber eine Lücke als eine erfundene Fundstelle.** Was nicht geprüft
   ist, trägt `verifiziert: false` und einen Prüfvermerk, der sagt, warum.
3. **Der Streitstand ist der Ertrag, nicht die Entscheidung.** Wer nur
   sammelt, baut ein Archiv. Wer sortiert, baut ein Werk.
