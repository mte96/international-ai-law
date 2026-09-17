# =====================================================================
# quellenklasse.py - Wie viel ist eine Fundstelle wert?
#
# Eine Angabe traegt nur so weit wie die Quelle, an der sie steht. Das
# Projekt kannte diesen Unterschied bisher nur fuer Entscheidungen
# (`quelle_art`) und schaetzte ihn dort ueber eine Handvoll regulaerer
# Ausdruecke. Die Pruefung vom 10./11.09.2026 hat gemessen, was das
# kostet: 334 Inkrafttretens- und Anwendungsdaten trugen
# `verifiziert: true` auf einer Kanzleiseite, einem Presseartikel oder
# Wikipedia; 41 weitere auf einer Rechtsdatenbank; 60 ohne jede Quelle.
# Ein Kanzleiblog, der zufaellig recht hat, ist die Regel - einer, aus
# dem falsch abgeschrieben wurde, kam in einem von fuenf Faellen vor.
#
# Vier Klassen, nach dem Host der Adresse:
#
#   amtlich    Urschrift oder amtliche Veroeffentlichung: Amtsblatt,
#              Gesetzesportal, Gericht, Behoerde, Parlament, IGO.
#   urheber    Der Setzer des Instruments selbst, aber kein Staat:
#              ISO, IEC, CEN-CENELEC, IEEE, TC260, BRAK.
#   datenbank  Fuehrt den Volltext, ist aber nicht die Urschrift:
#              dejure, CourtListener, IndianKanoon, NZLII, SAFLII,
#              Justia, CanLII, consultant.ru, Thu vien phap luat.
#              Lesbar ja, zitierfaehig als Fundstelle nein.
#   sekundaer  Alles Uebrige: Presse, Kanzleien, Blogs, Tracker,
#              Wikipedia, Aufsaetze.
#   fehlt      Keine Adresse.
#
# Host-basiert, nicht mustergestuetzt: `.gov` faengt die Vereinigten
# Staaten, aber nicht `ai-law.gov.example.com`; umgekehrt ist
# `recht.bund.de` amtlich, ohne ein staatliches Suffix zu tragen, und
# `indiankanoon.org` ist es nicht, obwohl es Urteile im Volltext fuehrt.
# Die Liste stammt aus `klassifiziere.py` der Pruefung vom 10.09.2026;
# die 150 haeufigsten sekundaer eingestuften Hosts sind dort von Hand
# gegengelesen worden.
#
# Reihenfolge der Abfrage ist Absicht: Datenbank vor Urheber vor
# amtlich vor Suffix. Sonst schluepfte `itu.int` ueber `.int` in
# `amtlich`, obwohl die ITU hier als Urheberin ihrer eigenen Normen
# gemeint ist.
#
# Wer einen Host ergaenzt: in die richtige Liste, und nur, wenn die
# Seite die Quelle ist und nicht nur davon berichtet.
# =====================================================================
import re, collections

# 1. Staatliche Suffixe (Host endet darauf)
STAAT_SUFFIX = [
 ".gov",".gov.uk",".gov.au",".gov.il",".gov.za",".gov.ng",".gov.tr",".gov.ae",".gov.sa",".gov.my",".gov.sg",
 ".gov.br",".gov.co",".gov.ar",".gov.in",".gov.ru",".gov.cn",".gov.vn",".gov.tw",".gov.pe",".gov.cl",".gov.mx",
 ".gov.hk",".gov.ph",".gov.pk",".gov.bd",".gov.lk",".gov.eg",".gov.ie",".gov.pl",".gov.hu",".gov.cz",".gov.si",
 ".gov.pt",".gov.ro",".gov.sk",".gov.mt",".gov.cy",".gov.lv",".gov.lt",".gov.ee",".gov.hr",".gov.bg",".gov.gr",
 ".gov.it",".gov.es",".gov.kz",".gov.uz",".gov.kg",".gov.ge",".gov.am",".gov.az",".gov.ua",".gov.by",".gov.rs",
 ".gov.rw",".gov.gh",".gov.et",".gov.ma",".gov.tn",".gov.dz",".gov.jo",".gov.qa",".gov.kw",".gov.bh",".gov.om",
 ".gov.lb",".gov.np",".gov.mm",".gov.kh",".gov.la",".gov.mn",".gov.bn",".gov.fj",".gov.pg",".gov.jm",".gov.tt",
 ".gov.bs",".gov.bb",".gov.gy",".gov.py",".gov.bo",".gov.ec",".gov.ve",".gov.uy",".gov.cr",".gov.pa",".gov.do",
 ".gov.gt",".gov.hn",".gov.sv",".gov.ni",".gov.cu",".gov.pr",".gov.ky",".gov.bm",".gov.mo",".gov.np",".gov.mv",
 ".gob.mx",".gob.es",".gob.ar",".gob.cl",".gob.pe",".gob.ec",".gob.bo",".gob.gt",".gob.hn",".gob.sv",".gob.ni",
 ".gob.pa",".gob.do",".gob.ve",".gob.cu",".gob.pr",".gub.uy",
 ".gouv.fr",".gouv.qc.ca",".gouv.ci",".gouv.sn",".gouv.bj",".gouv.ma",".gouv.tn",
 ".go.jp",".go.kr",".go.id",".go.th",".go.ke",".go.tz",".go.ug",
 ".gc.ca",".canada.ca",".govt.nz",".parliament.nz",".gv.at",".admin.ch",".bund.de",".bundestag.de",".bundesrat.de",
 ".europa.eu",".int",".mil",".nic.in",".parliament.uk",".judiciary.uk",".jus.br",".leg.br",".mp.br",".def.br",
 ".legislature.ca.gov",".state.us",".gov.nl",".overheid.nl",".rijksoverheid.nl",".riksdagen.se",".regeringen.se",
 ".regjeringen.no",".stortinget.no",".domstol.no",".ft.dk",".folketinget.dk",
 ".eduskunta.fi",".valtioneuvosto.fi",".finlex.fi",".oireachtas.ie",".courts.ie",".irishstatutebook.ie",
 ".sejm.gov.pl",".senat.gov.pl",".camera.it",".senato.it",".quirinale.it",".giustizia.it",".cortecostituzionale.it",
 ".congreso.es",".senado.es",".boe.es",".poderjudicial.es",".tribunalconstitucional.es",".moncloa.gob.es",
 ".senat.fr",".assemblee-nationale.fr",".legifrance.gouv.fr",".conseil-constitutionnel.fr",".conseil-etat.fr",".courdecassation.fr",
 ".et.gr",".hellenicparliament.gr",".opengov.gr",".ministryofjustice.gr",
 ".knesset.gov.il",".court.gov.il",".kremlin.ru",".duma.gov.ru",".council.gov.ru",".pravo.gov.ru",".arbitr.ru",".sudrf.ru",".vsrf.ru",".ksrf.ru",".gov.ru",
 ".court.gov.cn",".npc.gov.cn",".moj.gov.cn",".miit.gov.cn",".samr.gov.cn",".cac.gov.cn",
 ".judicial.gov.tw",".ly.gov.tw",".ey.gov.tw",".moj.gov.tw",".president.gov.tw",
 ".zan.kz",".sud.kz",".akorda.kz",".egov.kz",".primeminister.kz",".lex.uz",".sud.uz",".president.uz",".gov.uz",
 ".chinhphu.vn",".quochoi.vn",".vbpl.vn",".toaan.gov.vn",".moj.gov.vn",
 ".ratchakitcha.soc.go.th",".krisdika.go.th",
 ".kenyalaw.org",".parliament.go.ke",".judiciary.go.ke",
 ".au.int",".africa-union.org",
 ".u.ae",".difc.ae",".difccourts.ae",".adgm.com",".digitaldubai.ae",".dubai.ae",".abudhabi.ae",".ai.gov.ae",
 ".boe.gov.sa",".moj.gov.sa",".sdaia.gov.sa",".nca.gov.sa",
 ".mevzuat.gov.tr",".resmigazete.gov.tr",".tbmm.gov.tr",".yargitay.gov.tr",".anayasa.gov.tr",".danistay.gov.tr",
 ".parl.ca",".scc-csc.ca",".fct-cf.ca",".fca-caf.ca",".ontario.ca",".quebec.ca",".alberta.ca",".gov.bc.ca",
 ".uscourts.gov",".supremecourt.gov",".house.gov",".senate.gov",".loc.gov",".govinfo.gov",".federalregister.gov",".congress.gov",
 ".nysenate.gov",".ilga.gov",".le.utah.gov",".leg.colorado.gov",".cga.ct.gov",".capitol.texas.gov",".legis.state",".legislature",
 ".courts.state",".nycourts.gov",".ca.gov",".ny.gov",".texas.gov",".wa.gov",".mass.gov",".virginia.gov",".nj.gov",".pa.gov",
 ".mo.gov",".ohio.gov",".michigan.gov",".illinois.gov",".colorado.gov",".oregon.gov",".arizona.gov",".az.gov",".nv.gov",".utah.gov",
 ".maryland.gov",".delaware.gov",".vermont.gov",".maine.gov",".nh.gov",".ct.gov",".ri.gov",".hawaii.gov",".alaska.gov",".florida.gov",".georgia.gov",".ga.gov",".tn.gov",".ky.gov",".in.gov",".wisconsin.gov",".mn.gov",".iowa.gov",".ne.gov",".ks.gov",".ok.gov",".arkansas.gov",".louisiana.gov",".ms.gov",".alabama.gov",".sc.gov",".nc.gov",".wv.gov",".idaho.gov",".montana.gov",".wyo.gov",".nd.gov",".sd.gov",".nm.gov",".dc.gov",
]
# 2. Amtliche Hosts ohne staatliches Suffix (Gerichte, Behörden, Amtsblätter, Parlamente, IGOs)
AMTLICH_HOSTS = set("""
bundesgerichtshof.de bundesverfassungsgericht.de bverwg.de bundesarbeitsgericht.de bundessozialgericht.de bundesfinanzhof.de bfh.de
gesetze-im-internet.de bgbl.de bundesanzeiger.de recht.bund.de rechtsprechung-im-internet.de dip.bundestag.de dserver.bundestag.de
bundesnetzagentur.de bfdi.bund.de datenschutzkonferenz-online.de bmjv.de bmj.de bmwk.de bmwi.de bmds.bund.de bmi.bund.de bmas.de bmbf.de bmg.bund.de bmuv.de bmf.de bundesregierung.de bundeskartellamt.de bafin.de bsi.bund.de
gesetze-bayern.de hessenrecht.hessen.de landesrecht-hamburg.de recht.nrw.de landesrecht-bw.de landesrecht.sachsen.de landesrecht.rlp.de landesrecht-mv.de landesrecht.thueringen.de landesrecht.brandenburg.de gesetze.berlin.de berlin.de justiz.nrw.de justiz.bayern.de justiz.baden-wuerttemberg.de justiz.hamburg.de landtag.nrw.de landtag-bw.de bayern.landtag.de parlament-berlin.de landtag.brandenburg.de
datenschutz-berlin.de datenschutz-hamburg.de datenschutz.hessen.de lfd.niedersachsen.de baden-wuerttemberg.datenschutz.de ldi.nrw.de datenschutz.rlp.de datenschutz.saarland.de datenschutz-bayern.de lda.bayern.de
gazzettaufficiale.it normattiva.it italgiure.giustizia.it giustizia-amministrativa.it cortedicassazione.it agid.gov.it acn.gov.it agcom.it garanteprivacy.it bancaditalia.it consob.it lavoro.gov.it mimit.gov.it governo.it innovazione.gov.it agcm.it ivass.it
aepd.es aesia.digital.gob.es consejodetransparencia.es lamoncloa.gob.es cnmc.es
dpa.gr api.et.gr et.gr archive.opengov.gr ai.gov.gr adjustice.gr eett.gr areiospagos.gr ste.gr
retsinformation.dk lovtidende.dk oda.ft.dk ft.dk hoeringsportalen.dk domstol.dk domsdatabasen.dk digst.dk kum.dk datatilsynet.dk digitaliseringsministeriet.dk
cnil.fr cnil.fr entreprises.gouv.fr economie.gouv.fr
ico.org.uk caselaw.nationalarchives.gov.uk legislation.gov.uk supremecourt.uk bills.parliament.uk hansard.parliament.uk fca.org.uk cma.gov.uk ofcom.org.uk bailii.org
fedcourt.gov.au hcourt.gov.au legislation.gov.au aph.gov.au oaic.gov.au accc.gov.au apra.gov.au asic.gov.au esafety.gov.au industry.gov.au dta.gov.au wa.gov.au legislation.wa.gov.au legislation.nsw.gov.au legislation.vic.gov.au legislation.qld.gov.au supremecourt.nsw.gov.au caselaw.nsw.gov.au austlii.edu.au
courtsofnz.govt.nz legislation.govt.nz privacy.org.nz mbie.govt.nz beehive.govt.nz tikatangata.org.nz justice.govt.nz digital.govt.nz data.govt.nz
scc-csc.ca decisions.fct-cf.ca laws-lois.justice.gc.ca priv.gc.ca parl.ca ised-isde.canada.ca canada.ca ontariocourts.ca ipc.on.ca
storage.courtlistener.com uscode.house.gov ftc.gov sec.gov copyright.gov uspto.gov federalregister.gov congress.gov govinfo.gov uscourts.gov supremecourt.gov whitehouse.gov nist.gov eeoc.gov cfpb.gov justice.gov fcc.gov commerce.gov bis.doc.gov ai.gov ntia.gov hhs.gov fda.gov dol.gov ed.gov energy.gov state.gov treasury.gov oag.ca.gov cppa.ca.gov leginfo.legislature.ca.gov nysenate.gov assembly.ny.gov ilga.gov le.utah.gov leg.colorado.gov cga.ct.gov capitol.texas.gov statutes.capitol.texas.gov legis.la.gov malegislature.gov legislature.maine.gov leg.mt.gov nmlegis.gov ncleg.gov legis.nd.gov okleg.gov oregonlegislature.gov legis.state.pa.us scstatehouse.gov sdlegislature.gov capitol.tn.gov legislature.vermont.gov lis.virginia.gov leg.wa.gov wvlegislature.gov docs.legis.wisconsin.gov wyoleg.gov azleg.gov arkleg.state.ar.us flsenate.gov legis.ga.gov capitol.hawaii.gov legislature.idaho.gov iga.in.gov legis.iowa.gov kslegislature.org legislature.ky.gov mgaleg.maryland.gov legislature.mi.gov revisor.mn.gov legislature.ms.gov house.mo.gov senate.mo.gov nebraskalegislature.gov leg.state.nv.us gencourt.state.nh.us njleg.state.nj.us dccouncil.gov legis.delaware.gov courts.mo.gov courts.ca.gov nycourts.gov
pravo.gov.ru publication.pravo.gov.ru duma.gov.ru sozd.duma.gov.ru kad.arbitr.ru sudrf.ru vsrf.ru mos-gorsud.ru ksrf.ru kremlin.ru rkn.gov.ru government.ru digital.gov.ru regulation.gov.ru minjust.gov.ru
court.gov.cn wenshu.court.gov.cn npc.gov.cn cac.gov.cn flk.npc.gov.cn miit.gov.cn samr.gov.cn moj.gov.cn gov.cn english.www.gov.cn
courts.gov.il gov.il main.knesset.gov.il fs.knesset.gov.il knesset.gov.il boi.org.il nevo.co.il
scjn.gob.mx sjf2.scjn.gob.mx internet2.scjn.gob.mx dof.gob.mx diputados.gob.mx senado.gob.mx inai.org.mx
stj.jus.br stf.jus.br planalto.gov.br in.gov.br gov.br camara.leg.br senado.leg.br tst.jus.br cnj.jus.br
sci.gov.in indiacode.nic.in egazette.gov.in meity.gov.in delhihighcourt.nic.in
camara.gov.co secretariasenado.gov.co corteconstitucional.gov.co funcionpublica.gov.co suin-juriscol.gov.co normograma.mintic.gov.co sic.gov.co sedeelectronica.sic.gov.co mintic.gov.co
servicios.infoleg.gob.ar boletinoficial.gob.ar argentina.gob.ar scba.gov.ar csjn.gov.ar cij.gov.ar senado.gob.ar diputados.gob.ar hcdn.gob.ar
bcn.cl leychile.cl senado.cl camara.cl tramitacion.senado.cl pjud.cl tribunalconstitucional.cl diariooficial.interior.gob.cl cplt.cl
busquedas.elperuano.pe elperuano.pe spij.minjus.gob.pe congreso.gob.pe pj.gob.pe tc.gob.pe gob.pe
adilet.zan.kz zan.kz egov.kz primeminister.kz akorda.kz sud.kz office.sud.kz lex.uz president.uz sud.uz
chinhphu.vn congbao.chinhphu.vn vanban.chinhphu.vn quochoi.vn vbpl.vn toaan.gov.vn
ratchakitcha.soc.go.th etda.or.th law.go.th krisdika.go.th supremecourt.or.th pdpc.or.th
agc.gov.my parlimen.gov.my kehakiman.gov.my pdp.gov.my mosti.gov.my
peraturan.go.id peraturan.bpk.go.id setneg.go.id mahkamahagung.go.id komdigi.go.id
uaelegislation.gov.ae u.ae assets.u.ae ai.gov.ae difc.ae difccourts.ae adgm.com digitaldubai.ae tdra.gov.ae
laws.boe.gov.sa sdaia.gov.sa nca.gov.sa ncar.gov.sa sjp.moj.gov.sa istitlaa.ncc.gov.sa cst.gov.sa
mevzuat.gov.tr resmigazete.gov.tr tbmm.gov.tr kvkk.gov.tr btk.gov.tr yargitay.gov.tr anayasa.gov.tr danistay.gov.tr
nass.gov.ng nitda.gov.ng ndpc.gov.ng copyright.gov.ng fmcide.gov.ng placng.org
new.kenyalaw.org kenyalaw.org parliament.go.ke odpc.go.ke
au.int achpr.au.int achpr.org afchpr.au.int
gov.za inforegulator.org.za compcom.co.za pmg.org.za justice.gov.za parliament.gov.za concourt.org.za dcdt.gov.za
fedlex.admin.ch bger.ch bvger.ch parlament.ch edoeb.admin.ch finma.ch swissmedic.ch admin.ch
ris.bka.gv.at parlament.gv.at dsb.gv.at rtr.at digitalaustria.gv.at bmf.gv.at bka.gv.at
lovdata.no regjeringen.no stortinget.no datatilsynet.no ki.norge.no norge.no domstol.no
law.go.kr pipc.go.kr ppc.go.jp laws.e-gov.go.jp e-gov.go.jp cao.go.jp www8.cao.go.jp meti.go.jp soumu.go.jp courts.go.jp
sso.agc.gov.sg pdpc.gov.sg imda.gov.sg aiverifyfoundation.sg mddi.gov.sg
law.moj.gov.tw judgment.judicial.gov.tw lis.ly.gov.tw ey.gov.tw nstc.gov.tw moda.gov.tw fsc.gov.tw
eur-lex.europa.eu curia.europa.eu edpb.europa.eu edps.europa.eu digital-strategy.ec.europa.eu oeil.europarl.europa.eu europarl.europa.eu technical-regulation-information-system.ec.europa.eu ai-act-service-desk.ec.europa.eu ec.europa.eu consilium.europa.eu data.europa.eu op.europa.eu eba.europa.eu esma.europa.eu eiopa.europa.eu enisa.europa.eu
centralelectoral.ine.mx repositoriodocumental.ine.mx ine.mx finanstilsynet.dk sahpra.org.za iponline.cipc.co.za cipc.co.za csm.it nia.or.kr vie-publique.fr digitallibrary.un.org bioethics.gr coe.int hudoc.echr.coe.int rm.coe.int un.org ohchr.org unesco.org wipo.int oecd.org oecd.ai wto.org itu.int unctad.org undp.org unido.org ilo.org who.int
""".split())
# 3. Urheber-Organisationen (Normung, Standardsetzer): Quelle des Instruments selbst, aber nicht Staat
URHEBER_HOSTS = set("tc260.org.cn standards.ieee.org brak.de iso.org iec.ch cencenelec.eu ieee.org ietf.org w3.org etsi.org itu.int jtc21.eu din.de ce.gov ".split())
# 4. Rechtsdatenbanken (Volltext, aber nicht Urschrift)
DATENBANK_HOSTS = set("""
dejure.org openjur.de law.justia.com justia.com caselaw.findlaw.com codes.findlaw.com findlaw.com vlex.com jurion.de lexology.com courtlistener.com casetext.com leagle.com anylaw.com casemine.com
jade.io nzlii.org saflii.org asianlii.org africanlii.org nigerialii.org commonlii.org worldlii.org canlii.org indiankanoon.org
consultant.ru garant.ru legiscan.com pravo.by pkulaw.com pkulaw.cn lawinfochina.com kluwerlawonline.com entscheidsuche.ch
thuvienphapluat.vn luatvietnam.vn zakon.kz norma.uz dsgvo-gesetz.de lexcada.com amlegal.com law.cornell.edu
base.garant.ru buzer.de lexsoft.de juris.de beck-online.beck.de gesetze.io lexisnexis.com westlaw.com chinalawtranslate.com jusbrasil.com.br
rechtsprechung.at jusline.at ris.jusline.at swisslex.ch weblaw.ch legalis.pl lexlege.pl iuscomp.org casebase.at
docketalarm.com pacermonitor.com unicourt.com trellis.law govtrack.us openstates.org legiscan.com billtrack50.com
""".split())
# 5. Ausdrücklich sekundär (Kanzleien, Presse, Blogs, Tracker, Wissenschaft, Wikipedia)
def einstufung(h):
    if not h: return "fehlt"
    if h in DATENBANK_HOSTS: return "datenbank"
    if h in URHEBER_HOSTS: return "urheber"
    if h in AMTLICH_HOSTS: return "amtlich"
    for a in AMTLICH_HOSTS:
        if h.endswith("."+a): return "amtlich"
    for s in STAAT_SUFFIX:
        if h == s.lstrip(".") or h.endswith(s): return "amtlich"
    return "sekundaer"


# Fuer den Aufruf von aussen: aus einer Adresse den Host ziehen und
# einstufen. `None`, Leerstring und alles ohne Schema ergeben "fehlt" -
# ein Feld ohne Adresse ist keine Quelle, sondern eine Luecke.
def host_von(url):
    from urllib.parse import urlparse
    if not url or not isinstance(url, str):
        return ""
    try:
        h = urlparse(url.strip()).netloc.lower()
    except Exception:
        return ""
    if h.startswith("www."):
        h = h[4:]
    return h.split(":")[0]


def klasse(url):
    """amtlich | urheber | datenbank | sekundaer | fehlt"""
    return einstufung(host_von(url))


# Was als Beleg fuer `verifiziert: true` taugt. Eine Datenbank taugt
# nicht: sie fuehrt einen Text, den jemand anders gesetzt hat, und in
# den gemessenen Faellen (dejure mit ueberholtem Aenderungsstand) auch
# nicht den heutigen.
TRAEGT = {"amtlich", "urheber"}


def traegt(url):
    return klasse(url) in TRAEGT


if __name__ == "__main__":
    import sys
    for u in sys.argv[1:]:
        print(f"{klasse(u):10s} {host_von(u):40s} {u}")
