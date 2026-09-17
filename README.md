# International AI Law — Database, App and Tracker

*Deutsche Fassung: [README.de.md](README.de.md)*

A structured database of AI regulation across 50 jurisdictions, a searchable
app generated from it, and a monitoring service that polls official sources
twice a day.

Not a collection of links but a model of the field: statutes, the individual
provisions inside them, the decisions that hang off those provisions, the
commentary that argues about them — and, cutting across all of it, the
unsettled legal questions around which the material sorts itself.

The app is generated from the database (`python3 build/build.py`, then open
`app/index.html` through a local server) and therefore cannot fall behind the
data.

## The app

![Instruments with the jurisdiction tree and the running figures](docs/bilder/01-regelwerke.png)

The starting view: 861 instruments, filterable by jurisdiction (grouped
supranational first, then by continent), by subject axis and by status.

![A controversy with its opposing positions](docs/bilder/02-streitstand.png)

A controversy — the unsettled question, the positions that contradict each
other, the courts that hold them, and the decisions each position rests on.
This is what the rest of the structure exists for.

![The world grid as a map](docs/bilder/03-weltkarte.png)

The world grid: 87 states, by state of legislation or by how far this
database has got with them. Micro-states are drawn as dots so that a special
path is not missed because the country is small.

![Case law with source and verification badges](docs/bilder/04-rechtsprechung.png)

Case law. Every entry says whether it rests on an official full text and
whether it has been checked against the primary document — 418 decisions, 257
with an official citation, 50 held only by a legal database, 111 with no full
text at all.

![All decisions on one provision, across jurisdictions](docs/bilder/06-vorschriften.png)

The norm level: filtering by a single provision — here 17 U.S.C. § 107 —
returns every decision that turns on it, across jurisdictions. This is the
access that a list of statutes cannot give.

![Coverage matrix, subject axes against jurisdictions](docs/bilder/05-matrix.png)

The coverage matrix. Empty cells are not an omission but the work queue.

## Holdings

| | |
|---|---|
| Instruments | **861** across 50 jurisdictions |
| Procedural documents | **2040**, 71 % with an official address, 51 % checked against the document |
| Individual provisions | **2068**, 665 of them with wording and an official link |
| Decisions | **418**, 61 % with official full text |
| Controversies | **24** with 194 opposing positions |
| Commentary | **558** titles |
| Deadlines | **295** with advance warning and calendar export |
| World grid | **87** states surveyed |

## The six levels

**Instrument** (`Regelwerk`) — statute, regulation or bill, with its
procedural status, its commencement date (checked against the official text
for 606 of 861), its staged dates of application and its procedural
documents.

**Provision** (`Vorschrift`) — the single norm as an object in its own right.
That is what makes "everything on Art. 50 AI Act" or "everything on § 44b
UrhG" answerable across all jurisdictions at once. 665 provisions carry the
wording and an official link; the rest are references, there to link and
filter by.

**Decision** (`Entscheidung`) — parties, docket number, facts, holding,
operative reasoning and citation. Anything not checked against the document
itself carries a verification note saying what is missing.

**Controversy** (`Streitstand`) — the unsettled question, with the positions
that contradict each other, the courts that hold them, the arguments that
carry them, and a forecast of how it will be resolved.

**Commentary** (`Literatur`) — with the central thesis, an assessment, and
links to the controversies it bears on.

**Deadline** (`Frist`) — cut-off dates with an official citation and advance
warning.

## The three rules everything hangs on

1. **`volltext_url` only for official full text.** Press coverage, law firm
   pages and tracker portals belong in `sekundaerquelle_url`.
2. **A gap is better than an invented citation.** Anything unchecked carries
   `verifiziert: false` and a note saying why. 1850 open points are named
   explicitly in the entries.
3. **The controversy is the yield, not the decision.**

## Layout

```
schema/     taxonomy, data model, validator
data/       the database — this is what gets maintained
build/      generates app data, search index and calendar feed from data/
app/        the interface
tracker/    source register, polling, deadline warnings, notification
docs/       scope and limits, access routes to the sources
```

## Pipeline

```bash
python3 schema/validate.py      # vocabulary, ids, dead references, schema check
python3 build/fremdumlaut.py    # umlauts corrupted in either direction
python3 build/quellenart.py     # grade the reliability of every citation
python3 build/build.py          # app/data.json and app/fristen.ics
python3 build/guete.py          # official backing, component by component
python3 build/abdeckung.py      # maturity per jurisdiction
```

## Self-checks

The database checks itself. `validate.py` enforces the controlled vocabulary,
catches duplicate and dead ids and instruments that are referenced but never
recorded — and reports fields that appear in the data but not in the schema.
That last check was written after an unnoticed drift in a field name had made
seven resolution forecasts invisible.

`fremdumlaut.py` finds foreign-language words mangled by an earlier umlaut
heuristic — "Doe" turned into "Dö", "Due" into "Dü", "Caesars" into "Cäsars"
— checking against a German and an English dictionary in both directions.

`quellenart.py` grades every reference as official, database, secondary or
missing, and makes visible where a reliable citation is absent.

## Monitoring

`tracker/watch.py` polls the sources listed in `tracker/quellen.yaml`,
`literatur.py` searches publication profiles, `fristen.py` warns about
expiring cut-off dates. Runs twice daily on GitHub Actions.
`pruefe_quellen.py` checks monthly which source has quietly died.

## State

The holdings are work in progress and say for themselves where they are thin:
111 decisions without a reliable citation, 255 instruments without a checked
commencement date, and continuous monitoring for only twelve of the 50
jurisdictions recorded. The measured error rate when commencement dates were
checked against the official text was 17 % — read anything unchecked with
that rate in mind.

`docs/OVERVIEW.md` sets out scope and limits in detail.
