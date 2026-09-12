#!/usr/bin/env python3
"""Klassifiziert jeden Volltext-Link nach seiner Belastbarkeit.

Ein Verweis auf einen Zeitungsartikel ist keine Fundstelle. Wer zitiert,
braucht das amtliche Dokument in der Originalsprache. Diese Einstufung
macht sichtbar, wo das fehlt:

  amtlich    - Gericht, Amtsblatt, Behoerde: unmittelbar zitierfaehig
  datenbank  - etablierte Rechtsdatenbank mit Volltext (dejure, Justia,
               CanLII): zitierfaehig, aber nicht die Urschrift
  sekundaer  - Bericht, Analyse, Kanzleiseite, Presse: KEINE Fundstelle
  fehlt      - gar kein Link
"""
import re, sys
from pathlib import Path
import yaml

# Amtliche Quellen: Gerichte, Gesetzblaetter, Aufsichtsbehoerden.
AMTLICH = [
    r"\.gov$", r"\.gov\.", r"\.gov/", r"\.gouv\.", r"\.gob\.", r"\.go\.jp",
    r"\.go\.kr", r"\.gc\.ca", r"\.govt\.nz", r"\.gov\.au", r"\.gov\.uk",
    r"europa\.eu", r"coe\.int", r"un\.org", r"oecd\.org", r"unesco\.org",
    r"wipo\.int", r"echr\.coe\.int", r"hudoc\.",
    r"bundesgerichtshof\.de", r"bundesverfassungsgericht\.de", r"bverwg\.de",
    r"bundesarbeitsgericht\.de", r"bundessozialgericht\.de", r"bfh\.de",
    r"gesetze-im-internet\.de", r"bgbl\.de", r"bundesanzeiger\.de",
    r"justiz\.", r"rechtsprechung-im-internet\.de", r"dip\.bundestag\.de",
    r"caselaw\.nationalarchives\.gov\.uk", r"legislation\.gov\.uk",
    r"judiciary\.uk", r"supremecourt\.uk", r"parliament\.uk",
    r"fedcourt\.gov\.au", r"hcourt\.gov\.au", r"austlii\.edu\.au",
    r"legislation\.gov\.au", r"aph\.gov\.au", r"oaic\.gov\.au", r"accc\.gov\.au",
    r"scc-csc\.ca", r"decisions\.fct-cf\.ca", r"laws-lois\.justice\.gc\.ca",
    r"priv\.gc\.ca", r"canlii\.org",
    r"supremecourt\.gov", r"uscourts\.gov", r"ftc\.gov", r"sec\.gov",
    r"copyright\.gov", r"uspto\.gov", r"federalregister\.gov", r"congress\.gov",
    r"storage\.courtlistener\.com", r"govinfo\.gov/content/pkg/USCOURTS",
    r"courtlistener\.com/docket/", r"courtlistener\.com/recap/",
    r"pravo\.gov\.ru", r"publication\.pravo\.gov\.ru", r"duma\.gov\.ru",
    r"kad\.arbitr\.ru", r"sudrf\.ru", r"vsrf\.ru", r"mos-gorsud\.ru", r"ksrf\.ru",
    r"court\.gov\.cn", r"pkulaw\.", r"npc\.gov\.cn", r"cac\.gov\.cn",
    r"courts\.gov\.il", r"scjn\.gob\.mx", r"stj\.jus\.br", r"stf\.jus\.br",
    r"jusbrasil\.com\.br/processos", r"indiankanoon\.org", r"sci\.gov\.in",
    r"delhihighcourt\.nic\.in", r"courtsofnz\.govt\.nz",
    r"ico\.org\.uk", r"garanteprivacy\.it", r"cnil\.fr", r"edpb\.europa\.eu",
    r"aepd\.es", r"datatilsynet\.", r"pipc\.go\.kr", r"ppc\.go\.jp",
    r"iso\.org", r"cencenelec\.eu", r"nist\.gov", r"ieee\.org",
    # EU-Mitgliedstaaten: Gerichte, Amtsblaetter, Parlamente, Aufsicht
    r"conseil-constitutionnel\.fr", r"conseil-etat\.fr", r"courdecassation\.fr",
    r"legifrance\.gouv\.fr", r"senat\.fr", r"assemblee-nationale\.fr",
    r"gazzettaufficiale\.it", r"normattiva\.it", r"camera\.it", r"senato\.it",
    r"italgiure\.giustizia\.it", r"giustizia-amministrativa\.it",
    r"cortedicassazione\.it", r"agid\.gov\.it", r"acn\.gov\.it", r"agcom\.it",
    r"boe\.es", r"congreso\.es", r"senado\.es", r"poderjudicial\.es",
    r"aesia\.digital\.gob\.es", r"consejodetransparencia\.es",
    r"et\.gr", r"api\.et\.gr", r"opengov\.gr", r"archive\.opengov\.gr",
    r"hellenicparliament\.gr", r"dpa\.gr", r"adjustice\.gr", r"eett\.gr",
    r"retsinformation\.dk", r"lovtidende\.dk", r"ft\.dk", r"oda\.ft\.dk",
    r"hoeringsportalen\.dk", r"domstol\.dk", r"domsdatabasen\.dk",
    r"digst\.dk", r"kum\.dk",
    # Ministerien, Parlamente und Behoerden, die keine .gov-Endung tragen
    r"\.bund\.de", r"bundestag\.de", r"bundesrat\.de", r"bmjv\.de", r"bmj\.de",
    r"bmwk\.de", r"bmwi\.de", r"bundesnetzagentur\.de", r"bfdi\.bund\.de",
    r"datenschutzkonferenz-online\.de", r"canada\.ca", r"oecd\.ai",
    r"\.gv\.at", r"\.admin\.ch", r"overheid\.nl", r"riksdagen\.se",
    r"\.europa\.eu", r"\.int/", r"\.int$",
    r"landtag\.nrw\.de", r"landtag-bw\.de", r"landtag\.", r"landesregierung\.",
    r"bancaditalia\.it", r"sozd\.duma\.gov\.ru", r"e-gov\.go\.jp", r"law\.go\.kr",
    r"sso\.agc\.gov\.sg", r"planalto\.gov\.br", r"in\.gov\.br", r"parl\.ca",
    r"egazette\.gov\.in", r"meity\.gov\.in", r"cga\.ct\.gov", r"cppa\.ca\.gov",
    r"leginfo\.legislature\.ca\.gov", r"nysenate\.gov", r"ilga\.gov", r"le\.utah\.gov",
    # --- Welle 300: neu erfasste Rechtsordnungen -----------------------
    # Zentralasien: die amtlichen Rechtsportale tragen keine .gov-Endung
    r"adilet\.zan\.kz", r"zan\.kz", r"egov\.kz", r"primeminister\.kz",
    r"akorda\.kz", r"sud\.kz", r"lex\.uz", r"president\.uz", r"sud\.uz",
    # Vietnam, Thailand, Malaysia, Indonesien
    r"chinhphu\.vn", r"quochoi\.vn", r"vbpl\.vn", r"toaan\.gov\.vn",
    r"ratchakitcha\.soc\.go\.th", r"etda\.or\.th", r"law\.go\.th",
    r"krisdika\.go\.th", r"supremecourt\.or\.th", r"\.go\.th",
    r"agc\.gov\.my", r"parlimen\.gov\.my", r"kehakiman\.gov\.my",
    r"pdp\.gov\.my", r"\.gov\.my", r"peraturan\.go\.id",
    r"peraturan\.bpk\.go\.id", r"setneg\.go\.id", r"mahkamahagung\.go\.id",
    r"\.go\.id",
    # Peru und Chile
    r"elperuano\.pe", r"busquedas\.elperuano\.pe", r"spij\.minjus\.gob\.pe",
    r"congreso\.gob\.pe", r"pj\.gob\.pe", r"tc\.gob\.pe",
    r"bcn\.cl", r"leychile\.cl", r"senado\.cl", r"camara\.cl",
    r"tramitacion\.senado\.cl", r"pjud\.cl", r"tribunalconstitucional\.cl",
    r"diariooficial\.interior\.gob\.cl", r"\.gob\.cl",
    # Golfstaaten und Tuerkei
    r"uaelegislation\.gov\.ae", r"u\.ae", r"ai\.gov\.ae", r"difc\.ae",
    r"difccourts\.ae", r"adgm\.com", r"digitaldubai\.ae", r"\.gov\.ae",
    r"laws\.boe\.gov\.sa", r"sdaia\.gov\.sa", r"nca\.gov\.sa",
    r"ncar\.gov\.sa", r"sjp\.moj\.gov\.sa", r"\.gov\.sa",
    r"mevzuat\.gov\.tr", r"resmigazete\.gov\.tr", r"tbmm\.gov\.tr",
    r"kvkk\.gov\.tr", r"btk\.gov\.tr", r"yargitay\.gov\.tr",
    r"anayasa\.gov\.tr", r"danistay\.gov\.tr", r"\.gov\.tr",
    # Afrika
    r"nass\.gov\.ng", r"nitda\.gov\.ng", r"ndpc\.gov\.ng",
    r"copyright\.gov\.ng", r"fmcide\.gov\.ng", r"\.gov\.ng",
    r"kenyalaw\.org", r"parliament\.go\.ke", r"odpc\.go\.ke", r"\.go\.ke",
    r"au\.int", r"achpr\.au\.int", r"achpr\.org", r"afchpr\.au\.int",
    # Schweiz, Oesterreich, Norwegen
    r"fedlex\.admin\.ch", r"bger\.ch", r"bvger\.ch", r"parlament\.ch",
    r"edoeb\.admin\.ch", r"finma\.ch", r"swissmedic\.ch",
    r"ris\.bka\.gv\.at", r"parlament\.gv\.at", r"dsb\.gv\.at", r"rtr\.at",
    r"lovdata\.no", r"regjeringen\.no", r"stortinget\.no",
    # Landesrechtsportale der deutschen Laender - amtliche Verkuendung
    r"gesetze-bayern\.de", r"hessenrecht\.hessen\.de", r"landesrecht-hamburg\.de",
    r"recht\.nrw\.de", r"landesrecht-bw\.de", r"landesrecht\.", r"buergerservice\.",
    r"govinfo\.gov/link/uscode", r"statutes\.capitol\.texas\.gov", r"le\.utah\.gov",
    r"archives\.gov/founding-docs", r"cga\.ct\.gov", r"leg\.colorado\.gov",
    r"ai-act-service-desk\.ec\.europa\.eu",
    r"datatilsynet\.no", r"ki\.norge\.no", r"\.norge\.no",
]
# Rechtsdatenbanken mit Volltext - zitierfaehig, aber nicht die Urschrift.
DATENBANK = [
    r"dejure\.org", r"openjur\.de", r"law\.justia\.com", r"caselaw\.findlaw\.com",
    r"bailii\.org", r"vlex\.com", r"jurion\.de", r"lexology\.com/library",
    r"courtlistener\.com/opinion/", r"casetext\.com", r"leagle\.com", r"anylaw\.com", r"casemine\.com",
    r"jade\.io", r"nzlii\.org", r"saflii\.org", r"asianlii\.org",
    r"consultant\.ru", r"garant\.ru", r"legiscan\.com", r"pravo\.by",
    r"pkulaw\.com", r"lawinfochina\.com", r"kluwerlawonline\.com",
    r"entscheidsuche\.ch", r"africanlii\.org", r"nigerialii\.org",
    r"thuvienphapluat\.vn", r"luatvietnam\.vn", r"hukukdergisi\.",
    r"zakon\.kz", r"norma\.uz",
    r"dsgvo-gesetz\.de", r"lexcada\.com", r"codes\.findlaw\.com",
    r"amlegal\.com", r"law\.cornell\.edu",
]
def art(url):
    u = str(url or "").lower()
    if not u.startswith("http"): return "fehlt"
    for m in AMTLICH:
        if re.search(m, u): return "amtlich"
    for m in DATENBANK:
        if re.search(m, u): return "datenbank"
    return "sekundaer"

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    from collections import Counter
    zaehler = Counter()
    nur_pruefen = "--pruefen" in sys.argv
    verschieben = "--verschieben" in sys.argv
    kandidaten = []
    for p in sorted((root / "data/urteile").rglob("*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        for u in d.get("urteile") or []:
            a = art(u.get("volltext_url"))
            zaehler[a] += 1
            u["quelle_art"] = a
            # Ein sekundaerer Link bleibt erhalten, wandert aber ins
            # eigene Feld - die Fundstelle darf er nicht besetzen.
            #
            # Nur auf ausdrueckliche Anweisung: Das Verschieben hat schon
            # zweimal amtliche Links entwertet, weil eine neu erfasste
            # Rechtsordnung ihr Amtsblatt noch nicht in AMTLICH stehen
            # hatte. Ohne --verschieben wird nur gezaehlt und am Ende
            # aufgelistet, was verschoben wuerde.
            if a == "sekundaer" and u.get("volltext_url"):
                if verschieben:
                    u.setdefault("sekundaerquelle_url", u["volltext_url"])
                    u["volltext_url"] = None
                else:
                    kandidaten.append((u.get("id"), u["volltext_url"]))
        if not nur_pruefen:
            p.write_text("# Gepflegte Datenbasis. Rohrecherche in _research/.\n" +
                         yaml.dump(d, allow_unicode=True, sort_keys=False, width=100))
    gesamt = sum(zaehler.values())
    for a in ("amtlich","datenbank","sekundaer","fehlt"):
        print(f"  {zaehler[a]:>3} ({zaehler[a]*100//gesamt:>2}%)  {a}")
    print(f"\n{zaehler['sekundaer']+zaehler['fehlt']} Entscheidungen ohne belastbare Fundstelle")
    if kandidaten:
        print(f"\n{len(kandidaten)} Links gelten als sekundaer und wuerden mit "
              f"--verschieben aus volltext_url herausgenommen.")
        print("Vorher pruefen, ob die Domaene nur in AMTLICH fehlt:")
        for i, u in kandidaten[:25]:
            print(f"   {i}  {u[:88]}")
