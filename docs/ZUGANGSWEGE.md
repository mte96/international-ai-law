# Zugangswege zu den Rechtsprechungsdatenbanken

Sechs Recherche-Agenten sind im September 2026 an den Gerichtsportalen
gescheitert: robots.txt-Sperren, Captchas, 403er. Der Cloud-Container
kommt an diese Seiten nicht heran. **Der Browser des Bearbeiters kommt
heran.** Dieses Dokument hält fest, welcher Weg wo trägt, damit der
nächste Durchgang nicht wieder suchen muss.

Stand: 7. September 2026.

## Das Grundmuster

1. `tabs_context_mcp` → `tabs_create_mcp` (eigener Tab je Sitzung)
2. `navigate` auf die **Such- oder API-Adresse**, nicht auf die Startseite
3. `get_page_text` für JSON-Antworten, `find` + `scroll_to` + `screenshot`
   für lange Urteile, `javascript_tool` zum Verdichten

**Zwei Fallen des Werkzeugs:**

- `javascript_tool` bricht mit `[BLOCKED: Cookie/query string data]` ab,
  sobald der Code `fetch` mit Abfrageparametern benutzt oder `href`-Werte
  mit Abfrageparametern zurückgibt. Deshalb: **navigieren statt fetchen**,
  und im JavaScript nur Text zurückgeben, keine Adressen.
- `read_page` mit `ref_id` liefert bei Akoma-Ntoso-Seiten oft nur die
  Absatznummer. Der Text steht im Geschwisterelement. `scroll_to` plus
  `screenshot` ist dort zuverlässiger.

## Kenia — trägt vollständig

Die beste Quelle der ganzen Liste.

```
https://new.kenyalaw.org/search/api/documents/?search=<begriff>&nature=Judgment&page=<n>
```

Liefert sauberes JSON: `citation`, `date`, `court`, `outcome`,
`case_number`, `judges`, `expression_frbr_uri` und `highlight.content`
mit dem Treffertext. Volltext unter
`https://new.kenyalaw.org<expression_frbr_uri>`.

- `page_size` wird **ignoriert**; zehn Treffer je Seite, `page` hochzählen.
- `nature` kennt auch `Gazette`, `Bill`, `Act`, `Legal Notice`, `Journal`.
- `ordering=-date` funktioniert.
- Facetten in `facets` geben Gericht, Jahr, Ausgang und Richter als
  Häufigkeiten aus — brauchbar, um den Bestand abzuschätzen, ohne zu blättern.

Befund 07.09.2026: 41 Entscheidungen nennen „artificial intelligence",
15 davon aus 2026. Noch nicht gelaufen: `deepfake`, `algorithm`,
`facial recognition`, `machine learning`, `automated decision`.

## Neuseeland — trägt nach Cloudflare-Prüfung

```
https://www.nzlii.org/cgi-bin/sinosrch.cgi?query=%22artificial+intelligence%22&results=20&meta=%2Fnzlii&mask_path=nz%2Fcases
```

Cloudflare schiebt eine Sicherheitsprüfung vor: **sechs Sekunden warten**
(`computer` mit `action: wait`), dann liefert die Seite die Trefferliste.
Für den Agenten war sie 403.

Volltextadresse ist aus dem Zitat ableitbar:
`[2026] NZHC 1422` → `https://www.nzlii.org/nz/cases/NZHC/2026/1422.html`
(leitet weiter auf `/cgi-bin/viewdoc/...`, das Zitat steht im Seitentitel —
damit ist der Abgleich ohne Volltextabruf möglich). Gerichtskürzel:
`NZHC`, `NZCA`, `NZSC`, `NZEmpC`, `NZERA`, `NZIPT`, `NZIPOPAT`, `NZDT`.

NZLII ist Rechtsdatenbank, nicht Urschrift. Für die Urschrift bleibt
`courtsofnz.govt.nz`, das aber nur ausgewählte Entscheidungen führt.

Befund 07.09.2026: 83 Dokumente, 17 davon ab 2023.

## Südafrika — erreichbar, Suchadresse noch falsch

`saflii.org` antwortet im Browser (für den Agenten 403), aber
`/cgi-bin/sinosrch.cgi?method=auto&query=…&mask_path=za` liefert
**HTTP 500**. Die richtige Suchadresse ist am Suchformular der Seite
abzulesen — SAFLII benutzt eine ältere SINO-Variante als NZLII.
Nächster Schritt: `saflii.org` aufrufen, Formular lesen, Adresse notieren.

## Geprüft am 7.9.2026 abends — drei Sackgassen und eine Korrektur

### Chile: Firewall, kein Captcha
`juris.pjud.cl` (Buscador Unificado) lädt und die Suchmaske ist bedienbar,
aber sobald ein Suchbegriff abgeschickt wird, antwortet der Server mit einer
Fehlerseite und einer Supportnummer, danach mit **„La URL solicitada ha sido
rechazada"**. Das ist eine Web Application Firewall, die das Zugriffsmuster
sperrt — und sie sperrt die **ganze Verbindung**, auch den Bearbeiter, der
selbst tippt. Die Sperre löst sich nach einiger Zeit von selbst.

Kein Umgehungsversuch. Wege daneben, die noch offen sind: der Consejo para
la Transparencia (`cplt.cl`), das Tribunal Constitucional
(`tribunalconstitucional.cl`) und die Fallos destacados auf `pjud.cl`.

### Kasachstan: die Suche, die gesucht wird, gibt es nicht
`office.sud.kz/courtActs/index.xhtml` ist der Банк судебных актов, offen
erreichbar, mit reCAPTCHA vor dem Absenden. Das Captcha ist **nicht** das
Hindernis. Die Maske bietet genau sechs Felder:

    Учетный год · Поиск по ключевому слову · Категория дела ·
    Область · Судебный орган · Результат рассмотрения

Das Feld „Поиск по ключевому слову" trägt intern die id **`edit-participant`**
— es sucht **Verfahrensbeteiligte**, nicht Volltext. Eine Suche nach
„искусственный интеллект" liefert deshalb nichts und die Maske springt
kommentarlos auf den Ausgangszustand zurück. **Eine Volltextsuche über
kasachische Entscheidungen existiert dort nicht.** Das erklärt auch, warum
ein früherer Rechercheagent für „дипфейк" null Treffer meldete.

Bleibender Weg: über `Категория дела` und `Судебный орган` blättern (die
Kategorienliste wird erst nach Wahl des Jahres per AJAX gefüllt), oder über
die Plenumsbeschlüsse des Obersten Gerichts auf `adilet.zan.kz`, die
ohnehin die tragende Rechtsquelle sind.

Nebenbei: Der violette Knopf **„Сбросить параметры поиска"** setzt die Suche
zurück. Der Suchknopf heißt **„Искать по заданным параметрами"** und steht
links daneben — eine Falle, in die man einmal tappt.

### Peru: Justizportal hart zu, Verfassungsgericht offen
`jurisprudencia.pj.gob.pe` antwortet mit **403 Forbidden** samt Transaction
ID, auch im Browser. Sackgasse. `tc.gob.pe` dagegen lädt normal und führt
„JURISPRUDENCIA SISTEMATIZADA" sowie „RESOLUCIONES" — dort weitermachen.

### VAE: der Digital Economy Court ist kein KI-Gericht
`difccourts.ae/rules-decisions/judgments-orders` ist vollständig offen, ohne
Captcha, mit eigenen Abteilungen. Der **Digital Economy Court** hat bis zum
07.09.2026 genau **ein** Verfahren: DEC 001/2025 Techteryx Ltd gegen Aria
Commodities DMCC u.a., zehn Beschlüsse zwischen Mai 2025 und September 2026.
Techteryx ist der Emittent des Stablecoin TrueUSD — es geht um digitale
Vermögenswerte, nicht um KI. Wer dort KI-Rechtsprechung erwartet, sucht
falsch; die einschlägigen Entscheidungen stehen im Court of First Instance
und im Court of Appeal.

### Österreich RIS: offene Schnittstelle, klarer Negativbefund
`data.bka.gv.at/ris/api/v2.6/judikatur` liefert JSON ohne Anmeldung und ohne
Sperre. Parameter: `Applikation` (Justiz, Vwgh, Vfgh, Bvwg, Lvwg, Dsk),
`Suchworte`, `DokumenteProSeite=Fifty`, `Seitennummer`.

Beim Auslesen `document.querySelector('pre').textContent` parsen, nicht
`innerText` — der Viewer kürzt.

Ergebnis für „künstliche Intelligenz": **VwGH 0, VfGH 0, OGH 1** (eine
Entscheidung von 1997, Fehltreffer), **DSB 1** (bereits erfasst),
**BVwG 188** — ganz überwiegend Asylverfahren, in denen der Begriff im
Länderbericht vorkommt. „ChatGPT" beim OGH: 0. Die österreichischen
Höchstgerichte haben keine KI-Rechtsprechung; sie entsteht am BVwG und an
der Datenschutzbehörde.

### Norwegen Datatilsynet: die ergiebigste Verwaltungspraxis der Runde
`datatilsynet.no` ist vollständig offen, 244 Treffer zu „kunstig
intelligens". Der eigentliche Fund ist die **regulatorische Sandkasse**:
`/regelverk-og-verktoy/rapporter-og-utredninger/rapporter-fra-sandkassa/`
führt **20 abgeschlossene Projekte von Januar 2022 bis Mai 2026**, jedes mit
Abschlussbericht. Alle 20 sind eingespielt.

Das ist ein Bestand, den keine andere Rechtsordnung so offen führt: die
Aufsichtsbehörde denkt konkrete KI-Einsätze durch und schreibt das Ergebnis
auf. Am gewichtigsten: **PrevBOT** (Polizeihochschule, KI-Erkennung von
Grooming in Chats, 20.03.2024) und **Jussboten LawAi** (Rechtsberatung durch
einen Chatbot, 11.12.2024).

### Türkei: Domäne löst nicht auf
`kvkk.gov.tr` und `www.kvkk.gov.tr` antworten mit
**DNS_PROBE_FINISHED_NXDOMAIN**. Ob die Behörde die Domäne gewechselt hat
oder ob es an der Namensauflösung von außen liegt, ist offen. Die vier
Einträge der Datenbasis, die auf kvkk.gov.tr verweisen, sind als
prüfbedürftig markiert. Ersatzweg: Resmî Gazete oder Webarchiv.

### Peru: Verfassungsgericht erreichbar, Suche nicht gefunden
`tc.gob.pe` lädt, `jurisprudencia.tc.gob.pe` löst nicht auf. Die
Volltextsuche ist auf dem Portal nicht auf Anhieb zu finden; das braucht
einen eigenen Durchgang.

## Noch nicht geprüft

| Rechtsordnung | Adresse | Bekanntes Hindernis |
|---|---|---|
| Chile | `juris.pjud.cl` | Captcha (Agent) |
| Chile | `cplt.cl` (Transparenzrat) | ungeprüft |
| Peru | `jurisprudencia.pj.gob.pe`, `tc.gob.pe` | 403 (Agent) |
| Kasachstan | `office.sud.kz` | reCAPTCHA (Agent) |
| Usbekistan | `public.sud.uz` | ONEID-Anmeldung nötig |
| VAE | `difccourts.ae/judgments` | soll erreichbar sein |
| Türkei | `karararama.yargitay.gov.tr` | robots.txt (Agent) |
| Türkei | `kvkk.gov.tr/karar-ozetleri` | robots.txt (Agent) |
| Vietnam | `congbobanan.toaan.gov.vn` | robots.txt (Agent) |
| Thailand | `deka.supremecourt.or.th` | robots.txt (Agent) |
| Malaysia | `ejudgment.kehakiman.gov.my` | HTTP 404 (Agent) |
| Indonesien | `putusan3.mahkamahagung.go.id` | Captcha (Agent) |
| Nigeria | `nigerialii.org` | ungeprüft |
| Österreich | `ris.bka.gv.at/Judikatur` | offen, war nie das Problem |
| Norwegen | `lovdata.no/avgjorelse` | teils offen |

**Captchas löst der Bearbeiter selbst** — das hat bei AustLII und CanLII
schon funktioniert. Vorgehen: Seite aufrufen, im Chat Bescheid geben,
er löst, dann weiterarbeiten.

## Was der Weg gebracht hat (07.09.2026)

- **Wangai u.a. gegen Cabinet Secretary ICT**, [2026] KEHC 5690: „high-risk
  artificial intelligence systems" ist als Anknüpfungspunkt eines Verbots
  zu unbestimmt; statt dessen structural interdict mit Berichtspflicht der
  Regierung. Urteil in der Hauptsache seit 29.06.2026 vorbehalten.
- **Nyanjui gegen Nyanjui**, [2026] KEELC 3088 Ziff. 26: die einschlägige,
  aber völlig unpassende Fundstelle als derselbe Fehler wie die erfundene.
- **A v R**, [2026] NZHC 1422: Namensunterdrückung, weil KI-Plattformen
  gelöschte Informationen weiter ausgeben; Löschanordnungen gegen
  KI-Systeme im Grundsatz möglich, offene Gewichte als Grenze der
  Vollstreckbarkeit.
- Sieben neuseeländische Entscheidungen haben erstmals eine Fundstelle.
