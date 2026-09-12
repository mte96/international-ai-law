# What has been built here

*Deutsche Fassung: [UEBERBLICK.md](UEBERBLICK.md)*

As of 12 September 2026

## In one paragraph

A structured database of international AI law, from which a searchable app is
built, with a monitoring service that polls official sources twice a day. Not
a collection of links but a model of the field: statutes, the individual
provisions inside them, the decisions that hang off those provisions, the
commentary that argues about them — and, cutting across all of it, the
unsettled legal questions around which the material sorts itself.

## The holdings

| | |
|---|---|
| Instruments | **861** across 50 jurisdictions |
| Procedural documents | **2040**, 72 % checked against the document |
| Individual provisions (norm level) | **2068** |
| Decisions | **418**, 223 of them of high importance |
| Controversies | **24** with **194** positions |
| Commentary | **558** titles, 84 % linked |
| Deadlines | **295** legal deadlines, 87 % backed by an official source |
| World grid | **87** states surveyed |

## The six levels

What matters is not the quantity but that the levels are connected to each
other.

**1. Instrument** — a statute, a regulation, a bill. With its procedural
status, its commencement date (checked against the official text for 606 of
861), its staged dates of application, its regulatory focus and its
procedural documents.

**2. Provision** — the single norm as an object in its own right. This is the
access that no tracker and no law firm overview offers: "everything on § 44b
UrhG" or "everything on Art. 50 AI Act" across all jurisdictions at once.
**A limitation worth knowing:** of the 2068 provisions only **665** carry
their own text and an official link. The remaining 1403 are references — id,
instrument, designation, subject — good for linking and filtering, not for
reading.

**3. Decision** — with parties, docket number, holding, operative reasoning
and citation. 66 % carry an official full text, 76 % among those of high
importance. Anything not checked against the document carries a verification
note saying what is missing.

**4. Controversy** — the unsettled legal question, with the positions that
contradict each other, the courts that hold them, the arguments that carry
them, and a forecast of how it will be resolved. **This is the actual
yield.** A decision is a date; a controversy is an insight.

**5. Commentary** — with the central thesis, an assessment of my own, and
links to the controversies it bears on.

**6. Deadline** — cut-off dates with an official citation, advance warning
and calendar export.

## What it is good for

**Answering a question across jurisdictions.** "How is the breach of a
machine-readable reservation of rights treated?" — Italy criminalises it
(Art. 26 Legge 132/2025), Kazakhstan specifies it down to the format (XML,
JSON, RDF, CSV, YAML), Germany is litigating before the Federal Court of
Justice over what "machine-readable" even means. That stands side by side in
a single controversy, with citations.

**Grasping the state of a question in five minutes.** Who has decided, who
has not, what is pending, when the decision falls — and what to watch for.

**Citing instead of asserting.** Every entry carries a citation or says that
it lacks one. For a publication, a talk or a video that is the foundation
without which everything else stays assertion.

**Missing nothing.** 51 active sources are polled twice a day, 29
publication profiles searched, deadlines reported with advance warning.

## How good it is — honestly

**Strong:** the connection between the levels; the citation density for the
legal deadlines (87 % official) and for the decisions of high importance
(76 %); the controversies; the breadth (50 jurisdictions, twelve of which do
not appear in Western overviews at all); and the fact that every entry says
what it is missing — 1850 named open points are not a defect but the
opposite of a smoothed-over collection.

**Weak:**

- **111 decisions without a reliable citation** (26 %), 38 of them of high
  importance. The cause is almost always a blocked court portal.
- **255 instruments without a checked commencement date.** The measured error
  rate when these were checked was **17 %** — of 166 dates checked, 29 were
  wrong or invented. Read anything unchecked with that rate in mind.
- **The tracker watches only twelve of 50 jurisdictions.** For the remaining
  38 there is no continuous monitoring; they age.
- **Completeness is uncertain for the most recently recorded
  jurisdictions.** The September research ran without a search engine, purely
  through portals addressed directly.
- **The world grid is only 22 % backed by official sources** — it is a map,
  not an audit, and was never meant to be one.
- **The norm level is 68 % empty.** 1403 of 2068 provisions are bare
  references without text and without a link. Anyone wanting to read a
  provision from inside the database can do so for 665 of them.
- **The collection stores analysis, not narrative.** `ergebnis` (405 entries,
  710 characters on average) and `eigene_bewertung` (1004 entries, 733
  characters) carry the substance; a written-out statement of facts exists
  for 160 entries, a formal headnote for 23. For a narrative format the facts
  therefore have to be read back out of the full text case by case; the
  full-text link is present for 66 % of the decisions.

**What the maturity rating per jurisdiction does not say:** it measures
whether the six levels hold, not what share of the total population we have.
Nobody knows the total population. "Nigeria 50 %" means: the instruments are
recorded and cited, decisions and the norm level are missing. It does not
mean that half of Nigeria's AI statutes are missing.

## The tools

**Checking:** `schema/validate.py` (vocabulary, ids, dead references),
`build/fremdumlaut.py` (umlauts corrupted in either direction),
`build/quellenart.py` (reliability of every citation),
`build/guete.py` (official backing per component),
`build/abdeckung.py` (maturity per jurisdiction).

**Building:** `build/build.py` (database → app data),
`build/artifact.py` (app data → a self-contained page file),
`build/aus_artifact.py` (page file → components, for sessions without the repo),
`build/uebernehmen.py` (page file → database, closing the return path).

**Ingesting:** `build/einspielen.py` (research file → database),
`build/einspielen_inkrafttreten.py`, `build/einspielen_streitstaende.py`
(each id is checked before anything is written).

**Monitoring:** `tracker/watch.py` (sources), `tracker/literatur.py`
(profiles), `tracker/fristen.py` (advance warning),
`tracker/pruefe_quellen.py` (self-test), notification via ntfy. Runs on
GitHub Actions at 06:00 and 18:00 UTC.

**Automation:** a weekly run that keeps the holdings current without
widening them.

## Where it lives

- **The repository:** the YAML database in `data/`, the data model in
  `schema/`, the tools in `build/`, the monitoring service in `tracker/`.
- **The app:** built from `app/` with `build/build.py` and opened through a
  local server; it carries data, styles and logic inside itself.
- **The access routes** to the court and government portals are in
  `docs/ZUGANGSWEGE.md` (in German) — which ones work, which ones block, and
  how.

## The three rules everything hangs on

1. **`volltext_url` only for official full text.** Press coverage, law firm
   pages and tracker portals belong in `sekundaerquelle_url`.
2. **A gap is better than an invented citation.** Anything unchecked carries
   `verifiziert: false` and a verification note saying why.
3. **The controversy is the yield, not the decision.** Collecting builds an
   archive. Sorting builds a work.
