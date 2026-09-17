"use strict";

let D = null;
const Z = {ansicht:"regelwerke", suche:"", jur:new Set(), thema:new Set(),
           status:new Set(), norm:new Set(), sort:"standard", nurAmtlich:false};

// Sortierungen je Ansicht. "standard" ist die fachlich sinnvolle Voreinstellung,
// die uebrigen sind Werkzeuge fuer eine bestimmte Frage.
const SORTEN = {
  regelwerke: [["standard","Rechtsordnung"],["neu","Neueste zuerst"],
               ["alt","Älteste zuerst"],["az","Alphabetisch"],["dokumente","Meiste Dokumente"]],
  urteile:    [["standard","Bedeutung"],["neu","Neueste zuerst"],["alt","Älteste zuerst"],
               ["gericht","Gericht"],["jur","Rechtsordnung"]],
  literatur:  [["standard","Priorität"],["neu","Neueste zuerst"],["alt","Älteste zuerst"],
               ["zitiert","Meistzitiert"],["az","Titel A–Z"]],
  fristen:    [["standard","Nächste zuerst"],["alt","Späteste zuerst"]],
};

function jahrVon(e){
  const d = e.datum || e.inkrafttreten?.datum ||
            (e.anwendungsdaten||[])[0]?.datum || e.jahr;
  const m = String(d||"").match(/\d{4}/);
  return m ? +m[0] : 0;
}
function sortiere(liste, standard){
  const s = Z.sort;
  if(s==="standard" || !s) return liste.sort(standard);
  const nach = {
    neu:      (a,b)=> jahrVon(b)-jahrVon(a) || String(b.datum||"").localeCompare(String(a.datum||"")),
    alt:      (a,b)=> (jahrVon(a)||9999)-(jahrVon(b)||9999) || String(a.datum||"").localeCompare(String(b.datum||"")),
    az:       (a,b)=> (a.kurztitel||a.titel||"").localeCompare(b.kurztitel||b.titel||""),
    dokumente:(a,b)=> (b.dokumente||[]).length-(a.dokumente||[]).length,
    zitiert:  (a,b)=> (b.zitationen||0)-(a.zitationen||0),
    gericht:  (a,b)=> (a.gericht||"").localeCompare(b.gericht||""),
    jur:      (a,b)=> (D._jur[a.jurisdiktion]?.rang??99)-(D._jur[b.jurisdiktion]?.rang??99),
  }[s];
  return nach ? liste.sort(nach) : liste.sort(standard);
}

const $  = s => document.querySelector(s);
const el = (t,k,x) => {const n=document.createElement(t); if(k)n.className=k; if(x!=null)n.textContent=x; return n;};
const esc = s => String(s??"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// Belastbarkeit der Fundstelle - fuer einen Juristen die erste Frage.
const QUELLE = {
  amtlich:   '<span class="plakette p-gruen" title="Amtliches Dokument: unmittelbar zitierfähig">amtliche Fundstelle</span>',
  datenbank: '<span class="plakette p-blau" title="Rechtsdatenbank mit Volltext: zitierfähig, aber nicht die Urschrift">Datenbank</span>',
  sekundaer: '<span class="plakette p-amber" title="Nur ein Bericht über die Entscheidung — keine Fundstelle">nur Sekundärquelle</span>',
  fehlt:     '<span class="plakette p-rot" title="Kein Volltext hinterlegt">Fundstelle fehlt</span>',
};

const STATUSFARBE = {anwendbar:"gruen", teilanwendbar:"amber", verfahren:"blau",
  verabschiedet:"lila", entwurf:"blau", idee:"grau", gescheitert:"rot",
  aufgehoben:"grau", softlaw:"grau", rechtskraeftig:"gruen", anhaengig:"blau",
  erstinstanzlich:"amber", rechtsmittel:"amber", vergleich:"lila", erledigt:"grau"};

/* ---------------- Start ---------------- */
(function thema(){
  try{const t=localStorage.getItem("thema"); if(t)document.documentElement.dataset.thema=t;}catch(_){}
})();

fetch("data.json").then(r=>r.json()).then(d=>{
  D = d;
  // Reihenfolge der Taxonomie ist bewusst gewaehlt (EU, US, UK, AU, DE ...)
  D._jur    = Object.fromEntries(d.taxonomie.jurisdiktionen.map((j,i)=>[j.id,{...j,rang:i}]));
  D._thema  = Object.fromEntries(d.taxonomie.themenachsen.map(t=>[t.id,t]));
  D._status = Object.fromEntries([...d.taxonomie.statuswerte.regelwerk,
                                  ...d.taxonomie.statuswerte.verfahren].map(s=>[s.id,s]));
  D._doktyp = Object.fromEntries(d.taxonomie.dokumenttypen.map(t=>[t.id,t.name]));
  indiziere();
  speicherStarten();
  $("#stand").textContent = "Stand " + fdat(d.erzeugt);
  bauFilter(); ausHash(); zeichne();
}).catch(e=>{
  $("#inhalt").innerHTML = `<div class="leer"><p>Daten konnten nicht geladen werden.<br><code>${esc(e.message)}</code></p></div>`;
});

/* ---------------- Neue Fassung anbieten ----------------
   Der Service Worker liefert die Huelle aus dem Zwischenspeicher, sonst
   waere die Seite offline nicht zu gebrauchen. Der Preis: eine neue Fassung
   erreicht ein Geraet erst, wenn die Seite neu geladen wird - und auf dem
   Telefon heisst das im Zweifel nie, weil iOS die Seite schlafen legt statt
   sie zu verwerfen. Also fragen wir von uns aus nach und sagen Bescheid,
   statt darauf zu hoffen. */
let neuladenLaeuft = false;

function neueFassungAnbieten(reg){
  if(document.getElementById("neuefassung")) return;
  const b = el("div","neufassung"); b.id = "neuefassung";
  b.innerHTML = `<span>Eine neue Fassung ist bereit.</span>
    <button type="button" class="jetzt">Neu laden</button>
    <button type="button" class="spaeter" aria-label="Später">&times;</button>`;
  b.querySelector(".spaeter").onclick = ()=>b.remove();
  b.querySelector(".jetzt").onclick = ()=>{
    b.querySelector(".jetzt").textContent = "…";
    // Der wartende Worker uebernimmt erst auf Zuruf; das loest
    // controllerchange aus, und dort wird neu geladen.
    if(reg.waiting) reg.waiting.postMessage({typ:"uebernehmen"});
    else { neuladenLaeuft = true; location.reload(); }
  };
  document.body.appendChild(b);
}

if("serviceWorker" in navigator) addEventListener("load", async ()=>{
  let reg;
  try{ reg = await navigator.serviceWorker.register("sw.js"); }catch(_){ return; }

  navigator.serviceWorker.addEventListener("controllerchange", ()=>{
    if(neuladenLaeuft) return;          // gegen Endlosschleifen
    neuladenLaeuft = true; location.reload();
  });

  // Beim Laden liegt vielleicht schon einer bereit.
  if(reg.waiting && navigator.serviceWorker.controller) neueFassungAnbieten(reg);

  reg.addEventListener("updatefound", ()=>{
    const neu = reg.installing; if(!neu) return;
    neu.addEventListener("statechange", ()=>{
      // controller != null heisst: es gab schon eine Fassung. Beim allerersten
      // Einrichten gibt es nichts anzubieten.
      if(neu.state === "installed" && navigator.serviceWorker.controller)
        neueFassungAnbieten(reg);
    });
  });

  // Von selbst nachsehen. Ohne das fragt auf dem Telefon niemand nach.
  let zuletzt = 0;
  const nachsehen = ()=>{
    if(document.visibilityState !== "visible") return;
    if(Date.now() - zuletzt < 9e5) return;      // hoechstens alle 15 Minuten
    zuletzt = Date.now();
    reg.update().catch(()=>{});
  };
  addEventListener("visibilitychange", nachsehen);
  setInterval(nachsehen, 9e5);
});

/* ---------------- Suchindex ----------------
   Wird beim Laden gebaut statt mitgeliefert: derselbe Text ein zweites Mal
   im JSON haette die Datei fast verdoppelt. */
function indiziere(){
  const flach = v => Array.isArray(v) ? v.map(flach).join(" ")
    : (v && typeof v === "object") ? Object.values(v).map(flach).join(" ")
    : (v == null ? "" : String(v));
  const bau = (liste, felder) => liste.forEach(e => {
    e._such = felder.map(f => flach(e[f])).join(" ").replace(/\s+/g," ").toLowerCase();
  });
  const sf = D.suchfelder || {};
  bau(D.regelwerke, sf.regelwerk || ["kurztitel"]);
  bau(D.urteile,    sf.urteil    || ["gericht"]);
  bau(D.literatur,  sf.literatur || ["titel"]);
  bau(D.streitstaende || [], sf.streitstand || ["titel","frage"]);
  bau(D.angebote || [], ["name","anbieter","art","format"]);
}


/* ================= Serverseitiger Speicher =================
   Notizen, Lesestatus und Dossiers liegen nicht im Browser, sondern in
   der Datenbank des Artefakts. Damit stehen sie auf jedem Gerät bereit
   und können von einer späteren Sitzung gelesen werden — die App wird so
   zum Auftragskanal, nicht nur zum Nachschlagewerk.
   Die Seite muss ohne Speicher vollständig funktionieren: `use()` löst
   null auf, wenn diese Ansicht ihn nicht ausführen kann. */
const S = {db:null, notizen:{}, status:{}, dossiers:{}, bereit:false, grund:""};

async function speicherStarten(){
  try{ S.db = await claude.use("db"); }catch(_){ S.db = null; }
  if(!S.db){ S.bereit = true; S.grund = "Speicher in dieser Ansicht nicht verfügbar"; zeichne(); return; }
  try{
    S.db.collection("notizen").onSnapshot(schnapp=>{
      S.notizen = {}; S.status = {};
      // QuerySnapshot traegt ein docs-Array - kein forEach auf dem Snapshot selbst.
      (schnapp.docs || []).forEach(d=>{
        const v = d.data() || {};
        if(v.text) S.notizen[d.id] = v.text;
        if(v.lesestatus) S.status[d.id] = v.lesestatus;
        if(v.geaendert) S.notizen[d.id+"__stand"] = v.geaendert;
      });
      if(!$("#detail").hidden) detailAuffrischen();
      if(Z.ansicht==="literatur"||Z.ansicht==="dossiers") zeichne();
    }, e=>{ S.grund = "Notizen: " + (e && e.code || "Fehler"); });

    S.db.collection("dossiers").onSnapshot(schnapp=>{
      S.dossiers = {};
      (schnapp.docs || []).forEach(d=>{ S.dossiers[d.id] = {id:d.id, ...(d.data()||{})}; });
      if(Z.ansicht==="dossiers") zeichne();
      if(!$("#detail").hidden) detailAuffrischen();
    }, e=>{ S.grund = "Dossiers: " + (e && e.code || "Fehler"); });
  }catch(e){ S.grund = "Speicher nicht erreichbar: " + (e && e.message || e); }
  S.bereit = true;
  zeichne();   // die Ansicht kannte den Speicher beim ersten Zeichnen noch nicht
}

let schreibZeit;
function notizSichern(id, text){
  if(!S.db) return;
  clearTimeout(schreibZeit);
  schreibZeit = setTimeout(()=>{
    S.db.doc("notizen/"+id).set({
      text, lesestatus: S.status[id] || null, geaendert: new Date().toISOString(),
    }).catch(()=>{});
  }, 700);
}
function statusSetzen(id, wert){
  if(!S.db) return;
  S.status[id] = wert;
  S.db.doc("notizen/"+id).set({
    text: S.notizen[id] || "", lesestatus: wert, geaendert: new Date().toISOString(),
  }).catch(()=>{});
}
async function dossierAnlegen(titel){
  if(!S.db){ meldung("Speicher nicht verfügbar."); return; }
  if(!titel.trim()) return;
  const id = titel.trim().toLowerCase().replace(/[^a-z0-9äöüß]+/g,"-").slice(0,40)
             + "-" + Math.random().toString(36).slice(2,6);
  const eintrag = {titel: titel.trim(), eintraege: [], angelegt: new Date().toISOString()};
  try{
    await S.db.doc("dossiers/"+id).set(eintrag);
    S.dossiers[id] = {id, ...eintrag};   // nicht auf den Snapshot warten
    if(Z.ansicht==="dossiers") zeichne();
    meldung(`Dossier „${titel.trim()}" angelegt.`);
  }catch(e){ meldung("Konnte nicht angelegt werden: " + (e && e.code || "Fehler")); }
}
function dossierSchalten(dosId, eintragId, typ){
  const d = S.dossiers[dosId]; if(!S.db || !d) return;
  const liste = (d.eintraege || []).filter(e=>e.id !== eintragId);
  const zugefuegt = liste.length === (d.eintraege||[]).length;
  if(zugefuegt) liste.push({id:eintragId, typ});
  const neu = {...d, eintraege: liste, geaendert: new Date().toISOString()};
  delete neu.id;
  S.dossiers[dosId] = {id: dosId, ...neu};
  detailAuffrischen();
  S.db.doc("dossiers/"+dosId).set(neu)
    .then(()=>meldung(zugefuegt ? `Zu „${d.titel}" hinzugefügt.` : `Aus „${d.titel}" entfernt.`))
    .catch(e=>meldung("Nicht gespeichert: " + (e && e.code || "Fehler")));
}

/* ---------------- Export ---------------- */
function bibtexSchluessel(l){
  const a = ((l.autoren||[""])[0].split(",")[0] || "anon").replace(/[^A-Za-z]/g,"");
  return `${a.toLowerCase()}${l.jahr||""}${(l.titel||"").split(/\s+/)[0].replace(/[^A-Za-z]/g,"").toLowerCase().slice(0,6)}`;
}
function alsBibtex(liste){
  const TYP = {monografie:"book", dissertation:"phdthesis", "working-paper":"techreport",
    bericht:"techreport", blogbeitrag:"misc", kommentar:"book", handbuch:"book"};
  return liste.map(l=>{
    const f = [["author", (l.autoren||[]).join(" and ")], ["title", l.titel],
      ["year", l.jahr], ["journal", l.fundstelle], ["doi", l.doi],
      ["url", l.url], ["language", l.sprache], ["note", l.kernthese]]
      .filter(x=>x[1]).map(([k,v])=>`  ${k} = {${String(v).replace(/[{}]/g,"")}}`).join(",\n");
    return `@${TYP[l.typ]||"article"}{${bibtexSchluessel(l)},\n${f}\n}`;
  }).join("\n\n");
}
function alsRis(liste){
  const TYP = {monografie:"BOOK", dissertation:"THES", "working-paper":"RPRT",
    bericht:"RPRT", blogbeitrag:"BLOG", aufsatz:"JOUR"};
  return liste.map(l=>{
    const z = [`TY  - ${TYP[l.typ]||"JOUR"}`];
    (l.autoren||[]).forEach(a=>z.push(`AU  - ${a}`));
    if(l.titel) z.push(`TI  - ${l.titel}`);
    if(l.jahr) z.push(`PY  - ${l.jahr}`);
    if(l.fundstelle) z.push(`JO  - ${l.fundstelle}`);
    if(l.doi) z.push(`DO  - ${l.doi}`);
    if(l.url) z.push(`UR  - ${l.url}`);
    if(l.sprache) z.push(`LA  - ${l.sprache}`);
    if(l.kernthese) z.push(`AB  - ${l.kernthese}`);
    z.push("ER  - ");
    return z.join("\r\n");
  }).join("\r\n");
}
function alsCsv(zeilen, spalten){
  const e = v => `"${String(v??"").replace(/"/g,'""').replace(/\n/g," ")}"`;
  return [spalten.map(e).join(","),
    ...zeilen.map(z=>spalten.map(sp=>e(z[sp])).join(","))].join("\r\n");
}
async function exportieren(format, liste, name){
  const dl = await claude.use("downloads");
  if(!dl){ meldung("Export ist in dieser Ansicht nicht verfügbar."); return; }
  let daten, datei;
  if(format==="bibtex"){ daten = alsBibtex(liste); datei = name+".txt"; }
  else if(format==="ris"){ daten = alsRis(liste); datei = name+".txt"; }
  else {
    const flach = liste.map(l=>({
      Titel:l.titel, Autoren:(l.autoren||[]).join("; "), Jahr:l.jahr,
      Fundstelle:l.fundstelle, Typ:l.typ, Sprache:l.sprache, DOI:l.doi,
      URL:l.url, Zugang:l.zugang, Priorität:l.prioritaet,
      Themen:(l.themenachsen||[]).join("; "), Normen:(l.normen||[]).join("; "),
      Kernthese:l.kernthese, Bewertung:l.eigene_bewertung,
    }));
    daten = "\ufeff" + alsCsv(flach, Object.keys(flach[0]||{Titel:""}));
    datei = name+".csv";
  }
  try{ await dl.save({filename: datei, data: daten});
       meldung(`${liste.length} Titel exportiert.`); }
  catch(e){ if(e && e.code!=="declined") meldung("Export nicht möglich."); }
}
function meldung(text){
  let m = $("#meldung");
  if(!m){ m = el("div","meldung"); m.id="meldung"; document.body.appendChild(m); }
  m.textContent = text; m.style.opacity = "1";
  clearTimeout(m._t); m._t = setTimeout(()=>{ m.style.opacity = "0"; }, 3200);
}

/* ---------------- Hilfen ---------------- */
function fdat(s){
  if(!s) return "";
  const m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[3]}.${m[2]}.${m[1]}` : String(s);
}
function jname(id){ return D._jur[id]?.name || (id||"").toUpperCase(); }

function passt(e, felder){
  if(Z.norm.size && !(e.normen||[]).some(n=>Z.norm.has(n))) return false;
  if(Z.nurAmtlich && e.quelle_art && e.quelle_art !== "amtlich") return false;
  if(Z.jur.size && !Z.jur.has(e.jurisdiktion)) return false;
  if(Z.status.size && !Z.status.has(e.status)) return false;
  if(Z.thema.size && !(e.themenachsen||[]).some(t=>Z.thema.has(t))) return false;
  if(Z.suche){
    const q = Z.suche.toLowerCase().split(/\s+/).filter(Boolean);
    const heu = (e._such||"") + " " + felder.map(f=>String(e[f]??"")).join(" ").toLowerCase();
    if(!q.every(w=>heu.includes(w))) return false;
  }
  return true;
}

function hervor(text, kurz){
  const t = String(text??"");
  if(!Z.suche) return esc(kurz ? t.slice(0,kurz) : t);
  const woerter = Z.suche.split(/\s+/).filter(w=>w.length>1)
    .map(w=>w.replace(/[.*+?^${}()|[\]\\]/g,"\\$&"));
  if(!woerter.length) return esc(t);
  return esc(t).replace(new RegExp(`(${woerter.join("|")})`,"gi"), '<span class="mark">$1</span>');
}

/* ---------------- Filterleiste ---------------- */
function bauFilter(){
  const mach = (ziel, eintraege, menge) => {
    const w = $(ziel); w.innerHTML = "";
    eintraege.forEach(([id,label])=>{
      const b = el("button","chip");
      b.innerHTML = esc(label) + ' <span class="n"></span>';
      b.dataset.id = id;
      b.onclick = ()=>{ menge.has(id)?menge.delete(id):menge.add(id); zeichne(); };
      w.appendChild(b);
    });
  };
  machJurBaum();
  mach("#f-thema", D.taxonomie.themenachsen.map(t=>[t.id,t.name.split(" und ")[0].slice(0,26)]), Z.thema);
  mach("#f-status", D.taxonomie.statuswerte.regelwerk.map(s=>[s.id,s.name.split(" (")[0].slice(0,24)]), Z.status);

  $("#btn-reset").onclick = ()=>{ Z.jur.clear(); Z.thema.clear(); Z.status.clear();
    Z.norm.clear(); Z.nurAmtlich=false; $("#btn-amtlich").classList.remove("an");
    $("#btn-amtlich").textContent = "Nur amtliche Fundstellen";
    Z.suche=""; $("#suche").value=""; $("#f-normsuche").value="";
    Z.sort="standard"; zeichne(); };

  // Vorschriftenfilter: erst suchen, dann waehlen - 121 Chips auf einmal
  // waeren keine Auswahl.
  const nf = $("#f-normsuche");
  nf.oninput = ()=>{ normChipsZeichnen(nf.value.trim().toLowerCase()); };
  normChipsZeichnen("");

  $("#sortierung").onchange = e=>{ Z.sort = e.target.value; zeichne(); };
  $("#btn-export").onclick = exportMenue;
  $("#btn-amtlich").onclick = e=>{
    Z.nurAmtlich = !Z.nurAmtlich;
    e.target.classList.toggle("an", Z.nurAmtlich);
    e.target.textContent = Z.nurAmtlich ? "Alle Fundstellen" : "Nur amtliche Fundstellen";
    zeichne();
  };

  $("#reiter").querySelectorAll("button").forEach(b=>{
    b.onclick = ()=>{ Z.ansicht=b.dataset.ansicht;
      $("#reiter").querySelectorAll("button").forEach(x=>x.classList.toggle("aktiv",x===b));
      $("#inhalt").scrollTo?.(0,0); window.scrollTo(0,0); zeichne(); };
  });

  const s = $("#suche");
  let t; s.oninput = ()=>{ clearTimeout(t); t=setTimeout(()=>{ Z.suche=s.value.trim();
    $("#btn-loeschen").hidden = !s.value; zeichne(); },130); };
  $("#btn-loeschen").onclick = ()=>{ s.value=""; Z.suche=""; $("#btn-loeschen").hidden=true; zeichne(); s.focus(); };

  $("#btn-thema").onclick = ()=>{
    const r = document.documentElement;
    const dunkelJetzt = r.dataset.thema ? r.dataset.thema==="dunkel"
      : matchMedia("(prefers-color-scheme:dark)").matches;
    r.dataset.thema = dunkelJetzt ? "hell" : "dunkel";
    try{ localStorage.setItem("thema", r.dataset.thema); }catch(_){}
  };

  $("#btn-filter").onclick    = ()=>{ $("#filter").classList.add("offen"); $("#overlay").hidden=false; };
  $("#btn-filter-zu").onclick = zuFilter;
  $("#overlay").onclick       = ()=>{ zuFilter(); zuDetail(); };
  $("#btn-detail-zu").onclick = zuDetail;
  addEventListener("keydown", e=>{
    if(e.key==="Escape"){ zuDetail(); zuFilter(); }
    if(e.key==="/" && document.activeElement!==s){ e.preventDefault(); s.focus(); }
  });
  addEventListener("hashchange", ()=>{ ausHash(); });
}
/* ---------------- Auswahl der Rechtsordnung ----------------
   59 Knoepfe nebeneinander sind keine Auswahl, sondern eine Wand - deshalb
   stand hier frueher ein filter(tier<=2), der 13 zeigte und 37 belegte
   Rechtsordnungen unerreichbar machte. Jetzt: nach Kontinent gruppiert und
   zugeklappt. Uebernationales steht zuerst, weil dort das Recht entsteht,
   das die uebrigen uebernehmen. */
const JKURZ = {eu:"Europäische Union", us:"USA", uk:"Vereinigtes Königreich",
  ae:"Vereinigte Arabische Emirate", iso:"Normung",
  intl:"Übergreifend", latam:"Lateinamerika", africa:"Afrikanische Union"};
const jkurz = j => JKURZ[j.id] || j.name;
const JAUF = new Set(["uebernational"]);   // offene Gruppen

function jurChip(j){
  const b = el("button","chip");
  b.innerHTML = esc(jkurz(j)) + ' <span class="n"></span>';
  b.dataset.id = j.id;
  b.title = j.begruendung ? String(j.begruendung).trim().split("\n").join(" ") : "";
  b.onclick = ()=>{ Z.jur.has(j.id)?Z.jur.delete(j.id):Z.jur.add(j.id); zeichne(); };
  return b;
}

function machJurBaum(){
  const w = $("#f-jurisdiktion"); w.innerHTML = "";
  w.className = "jbaum";
  const kont = D.taxonomie.kontinente;
  if(!kont){                       // aeltere data.json aus dem Zwischenspeicher
    w.className = "chips";
    D.taxonomie.jurisdiktionen.forEach(j=>w.appendChild(jurChip(j)));
    return;
  }
  w.appendChild(el("div","jgewaehlt"));
  kont.forEach(k=>{
    const teil = D.taxonomie.jurisdiktionen.filter(j=>j.kontinent===k.id)
      .sort((a,b)=>jkurz(a).localeCompare(jkurz(b),"de"));
    if(!teil.length) return;
    const g = el("div","jgruppe"); g.dataset.k = k.id;
    const kopf = el("button","jkopf");
    kopf.type = "button";
    kopf.innerHTML = `<svg class="jpfeil" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>
      <span class="jname">${esc(k.name)}</span>
      <span class="jwahl" hidden></span><span class="jn"></span>`;
    kopf.onclick = ()=>{ JAUF.has(k.id)?JAUF.delete(k.id):JAUF.add(k.id); jbaumStand(); };
    const rumpf = el("div","jchips chips");
    teil.forEach(j=>rumpf.appendChild(jurChip(j)));
    if(teil.length > 2){
      const alle = el("button","jalle");
      alle.type = "button";
      alle.onclick = ()=>{
        const ids = teil.map(j=>j.id);
        if(ids.every(i=>Z.jur.has(i))) ids.forEach(i=>Z.jur.delete(i));
        else ids.forEach(i=>Z.jur.add(i));
        zeichne();
      };
      alle.dataset.ids = teil.map(j=>j.id).join(" ");
      rumpf.appendChild(alle);
    }
    g.append(kopf, rumpf); w.appendChild(g);
  });
  jbaumStand();
}

/* Haelt Zaehler, Auswahlmarken und Aufklappstand in einer Hand: wird nach
   jedem Zeichnen aufgerufen, damit die Zahlen zum gezeigten Bestand passen. */
function jbaumStand(){
  const w = $("#f-jurisdiktion");
  if(!w || !w.classList.contains("jbaum")) return;
  w.querySelectorAll(".jgruppe").forEach(g=>{
    const k = g.dataset.k;
    const chips = [...g.querySelectorAll(".chip")];
    const summe  = chips.reduce((s,b)=>s + (+b.querySelector(".n").textContent || 0), 0);
    const gewaehlt = chips.filter(b=>Z.jur.has(b.dataset.id)).length;
    const offen = JAUF.has(k) || gewaehlt > 0;
    g.classList.toggle("offen", offen);
    g.querySelector(".jchips").hidden = !offen;
    g.querySelector(".jkopf").setAttribute("aria-expanded", offen ? "true" : "false");
    g.querySelector(".jn").textContent = summe || "";
    const m = g.querySelector(".jwahl");
    m.hidden = !gewaehlt; m.textContent = gewaehlt;
    g.classList.toggle("taub", !summe && !gewaehlt);
    const alle = g.querySelector(".jalle");
    if(alle){
      const ids = alle.dataset.ids.split(" ");
      alle.textContent = ids.every(i=>Z.jur.has(i)) ? "Auswahl aufheben" : "alle wählen";
    }
  });
  const bar = w.querySelector(".jgewaehlt");
  if(!bar) return;
  bar.innerHTML = "";
  bar.hidden = !Z.jur.size;
  [...Z.jur].forEach(id=>{
    const j = D._jur[id]; if(!j) return;
    const b = el("button","jmarke");
    b.type = "button";
    b.innerHTML = esc(jkurz(j)) + ' <span aria-hidden="true">&times;</span>';
    b.title = "Auswahl aufheben";
    b.onclick = ()=>{ Z.jur.delete(id); zeichne(); };
    bar.appendChild(b);
  });
}

function normChipsZeichnen(suche){
  const w = $("#f-norm"); if(!w) return;
  const alle = (D.normen||[]).filter(n=>(n._eintraege||[]).length)
    .sort((a,b)=>(b._eintraege||[]).length-(a._eintraege||[]).length);
  const treffer = suche
    ? alle.filter(n=>(n.bezeichnung+" "+(n.thema||"")).toLowerCase().includes(suche))
    : alle.slice(0, 12);
  w.innerHTML = "";
  treffer.slice(0, 40).forEach(n=>{
    const b = el("button","chip"+(Z.norm.has(n.id)?" an":""));
    b.innerHTML = esc(n.bezeichnung) + ` <span class="n">${(n._eintraege||[]).length}</span>`;
    b.title = n.thema || "";
    b.dataset.id = n.id;
    b.onclick = ()=>{ Z.norm.has(n.id)?Z.norm.delete(n.id):Z.norm.add(n.id);
      normChipsZeichnen(suche); zeichne(); };
    w.appendChild(b);
  });
  if(!suche && alle.length > 12){
    const h = el("div","fusszeile");
    h.style.cssText = "margin:8px 0 0;padding:0;border:none;font-size:11px";
    h.textContent = `${alle.length} Vorschriften belegt — oben suchen`;
    w.appendChild(h);
  }
}

function exportMenue(){
  const liste = Z.ansicht==="literatur"
    ? D.literatur.filter(l=>{
        if(Z.suche && !(l._such||"").includes(Z.suche.toLowerCase())) return false;
        if(Z.thema.size && !(l.themenachsen||[]).some(t=>Z.thema.has(t))) return false;
        if(Z.jur.size && !(l.jurisdiktionen||[]).some(x=>Z.jur.has(x))) return false;
        if(Z.norm.size && !(l.normen||[]).some(n=>Z.norm.has(n))) return false;
        return true; })
    : [];
  if(!liste.length){ meldung("Nichts zu exportieren."); return; }
  const name = "ki-recht-literatur";
  const w = el("div","exportmenue");
  w.innerHTML = `<div class="em-kopf">${liste.length} Titel exportieren</div>` +
    [["bibtex","BibTeX — für Zotero, JabRef, LaTeX"],
     ["ris","RIS — für EndNote, Citavi, Mendeley"],
     ["csv","CSV — für Tabellenkalkulation"]]
    .map(([f,t])=>`<button data-f="${f}">${esc(t)}</button>`).join("") +
    `<button data-f="" class="ab">Abbrechen</button>`;
  document.body.appendChild(w);
  w.querySelectorAll("button").forEach(b=>b.onclick=()=>{
    const f = b.dataset.f; w.remove();
    if(f) exportieren(f, liste, name);
  });
}

function zuFilter(){ $("#filter").classList.remove("offen"); $("#overlay").hidden=true; }

function zaehlerAktualisieren(liste){
  const zaehle = (feld, ziel, mehrfach) => {
    const c = {};
    liste.forEach(e=>{ const v = e[feld];
      (mehrfach ? (v||[]) : [v]).forEach(x=>{ if(x) c[x]=(c[x]||0)+1; }); });
    $(ziel).querySelectorAll(".chip").forEach(b=>{
      const n = c[b.dataset.id]||0;
      b.querySelector(".n").textContent = n||"";
      b.style.opacity = n ? "" : ".38";
    });
  };
  zaehle("jurisdiktion","#f-jurisdiktion",false);
  zaehle("themenachsen","#f-thema",true);
  zaehle("status","#f-status",false);
  ["#f-jurisdiktion","#f-thema","#f-status"].forEach((z,i)=>{
    const m = [Z.jur,Z.thema,Z.status][i];
    $(z).querySelectorAll(".chip").forEach(b=>b.classList.toggle("an", m.has(b.dataset.id)));
  });
  jbaumStand();
}

/* ---------------- Zeichnen ---------------- */
function kennzahlen(c){
  const naechste = D.fristen.find(f=>f._tage!=null && f._tage>=0);
  const felder = [
    ["Regelwerke", D.statistik.regelwerke, D.statistik.jurisdiktionen_belegt + " Rechtsordnungen"],
    // "verlinkt und geprüft" stimmte fuer 2040 Dokumente nicht: 33 haben
    // gar keine Adresse, 494 eine sekundaere, und geprueft ist gut die
    // Haelfte. Der Kennzahlenblock sagt jetzt, was die Quellenlage
    // hergibt (build.py, statistik.quellenlage).
    ["Verfahrensdokumente", D.statistik.dokumente,
      `${(D.statistik.quellenlage?.dokumente?.amtlich||0)
        + (D.statistik.quellenlage?.dokumente?.urheber||0)} mit amtlicher Adresse`],
    ["Entscheidungen", D.statistik.urteile,
      `${D.statistik.urteile_amtlich} mit amtlichem Volltext`],
    ["Literatur", D.statistik.literatur,
      `${D.statistik.literatur_frei} frei zugänglich`],
    ["Offene Fristen", D.fristen.filter(f=>f._tage!=null && f._tage>=0).length, ""],
  ];
  const w = el("div","kennzahlen");
  felder.forEach(([label, wert, unten])=>{
    const d = el("div","kz");
    d.innerHTML = `<b>${wert}</b><span>${esc(label)}</span>${unten?`<small>${esc(unten)}</small>`:""}`;
    w.appendChild(d);
  });
  if(naechste){
    const d = el("div","kz" + (naechste._tage<=30?" warn":""));
    d.innerHTML = `<b>${naechste._tage} ${naechste._tage===1?"Tag":"Tage"}</b><span>bis zur nächsten Frist</span>
      <small title="${esc(naechste.beschreibung||"")}">${esc((naechste.beschreibung||"").slice(0,60))}</small>`;
    d.style.cursor = "pointer";
    d.onclick = ()=>{ $('#reiter button[data-ansicht="fristen"]').click(); };
    w.appendChild(d);
  }
  c.appendChild(w);
}

function werkzeugeAktualisieren(){
  const sorten = SORTEN[Z.ansicht];
  const leiste = $("#werkzeuge"), sel = $("#sortierung");
  leiste.hidden = !sorten;
  $("#fg-norm").hidden = !["urteile","literatur"].includes(Z.ansicht);
  $("#btn-export").hidden = Z.ansicht !== "literatur";
  $("#btn-amtlich").hidden = Z.ansicht !== "urteile";
  if(!sorten) return;
  if(!sorten.some(([w])=>w===Z.sort)) Z.sort = "standard";
  sel.innerHTML = sorten.map(([w,t])=>
    `<option value="${w}"${w===Z.sort?" selected":""}>${esc(t)}</option>`).join("");
}

function zeichne(){
  const c = $("#inhalt"); c.innerHTML = "";
  werkzeugeAktualisieren();
  zaehlerAktualisieren(D.regelwerke);
  if(Z.ansicht==="regelwerke" && !Z.suche && !Z.jur.size && !Z.thema.size && !Z.status.size)
    kennzahlen(c);
  ({regelwerke:vRegelwerke, fristen:vFristen, zeitstrahl:vZeitstrahl,
    urteile:vUrteile, streit:vStreit, literatur:vLiteratur,
    lernen:vLernen, dossiers:vDossiers, welt:vWelt,
    matrix:vMatrix}[Z.ansicht] || vRegelwerke)(c);
}

function leer(c, text, tipp){
  c.innerHTML = `<div class="leer">
    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
    <p>${esc(text)}${tipp?`<br><small>${esc(tipp)}</small>`:""}</p></div>`;
}

function plakette(status){
  const s = D._status[status];
  return `<span class="plakette p-${STATUSFARBE[status]||"grau"}">${esc(s?s.name.split(",")[0].split(" (")[0]:status)}</span>`;
}

function vRegelwerke(c){
  const liste = sortiere(
    D.regelwerke.filter(r=>passt(r,["kurztitel","offizieller_titel","celex","verfahrensnummer"])),
    (a,b)=>{
      const ra = D._jur[a.jurisdiktion]?.rang ?? 99, rb = D._jur[b.jurisdiktion]?.rang ?? 99;
      return ra-rb || (a.kurztitel||"").localeCompare(b.kurztitel||"");
    });
  c.appendChild(el("div","zaehler", `${liste.length} von ${D.regelwerke.length} Regelwerken`));
  if(!liste.length) return leer(c,"Nichts gefunden.","Filter zurücksetzen oder Suchbegriff ändern.");
  const w = el("div","karten");
  liste.forEach(r=>{
    const b = el("button","karte");
    const doks = (r.dokumente||[]).length, fr = (r.fristen||[]).length;
    b.innerHTML = `
      <div class="karte-kopf">
        <span class="karte-titel">${hervor(r.kurztitel)}</span>
        ${plakette(r.status)}
      </div>
      <div class="karte-meta">
        <span class="plakette p-akz">${esc(jname(r.jurisdiktion))}</span>
        ${r.fundstelle?`<code>${hervor(r.fundstelle)}</code>`:""}
        ${r.verfahrensnummer?`<code>${hervor(r.verfahrensnummer)}</code>`:""}
        ${doks?`<span>${doks} Dokumente</span>`:""}
        ${fr?`<span>${fr} Fristen</span>`:""}
      </div>
      ${r.status_detail?`<div class="karte-text">${hervor(r.status_detail)}</div>`:""}
      <div class="achsen">${(r.themenachsen||[]).map(t=>
        `<span class="achse">${esc(D._thema[t]?.name.split(" und ")[0]||t)}</span>`).join("")}</div>`;
    b.onclick = ()=>oeffne(r.id);
    w.appendChild(b);
  });
  c.appendChild(w);
}

function vFristen(c){
  const liste = D.fristen.filter(f=>{
    if(Z.jur.size && !Z.jur.has(f.jurisdiktion)) return false;
    if(Z.suche){ const q=Z.suche.toLowerCase();
      return ((f.beschreibung||"")+(f._regelwerk_titel||"")+(f.adressat||"")).toLowerCase().includes(q); }
    return true;
  });
  const kommend = liste.filter(f=>f._tage!=null && f._tage>=0);
  c.appendChild(el("div","zaehler", `${kommend.length} kommende Fristen, ${liste.length-kommend.length} vergangen`));
  if(!liste.length) return leer(c,"Keine Fristen erfasst.");
  const w = el("div","karten");
  liste.forEach(f=>{
    const t = f._tage, weg = t!=null && t<0;
    const kl = weg ? "weg" : t<=30 ? "eilig" : t<=120 ? "bald" : "";
    const b = el("button","karte");
    b.innerHTML = `<div class="frist">
      <div class="frist-tage ${kl}">
        <b>${t==null?"?":Math.abs(t)}</b><span>${t==null?"":weg?"Tage her":"Tage"}</span>
      </div>
      <div style="flex:1;min-width:0">
        <div class="karte-titel" style="font-size:14.5px">${hervor(f.beschreibung)}</div>
        <div class="karte-meta">
          <span class="plakette p-akz">${esc(jname(f.jurisdiktion))}</span>
          <code>${fdat(f.datum)}</code>
          ${f._regelwerk_titel?`<span>${esc(f._regelwerk_titel)}</span>`:""}
          ${f.verifiziert===false?'<span class="plakette p-amber">unverifiziert</span>':""}
        </div>
        ${f.adressat?`<div class="karte-text">${hervor(f.adressat)}</div>`:""}
      </div></div>`;
    if(f.regelwerk) b.onclick = ()=>oeffne(f.regelwerk);
    w.appendChild(b);
  });
  c.appendChild(w);
}

function vZeitstrahl(c){
  const ereignisse = [];
  D.regelwerke.forEach(r=>{
    if(!passt(r,["kurztitel"])) return;
    (r.dokumente||[]).forEach(d=>{ if(d.datum) ereignisse.push({
      datum:String(d.datum).slice(0,10), titel:d.titel||D._doktyp[d.typ]||"Dokument",
      quelle:r.kurztitel, url:d.url, rid:r.id,
      gross:["endfassung","konsolidiert","abstimmung"].includes(d.typ)}); });
    (r.anwendungsdaten||[]).forEach(a=>{ if(a.datum) ereignisse.push({
      datum:String(a.datum).slice(0,10), titel:(a.was_gilt||"").slice(0,190),
      quelle:r.kurztitel, rid:r.id, gross:true}); });
  });
  ereignisse.sort((a,b)=>b.datum.localeCompare(a.datum));
  c.appendChild(el("div","zaehler", `${ereignisse.length} Ereignisse`));
  if(!ereignisse.length) return leer(c,"Keine datierten Ereignisse im aktuellen Filter.");
  const w = el("div","zs"); let jahr = null;
  ereignisse.forEach(e=>{
    const j = e.datum.slice(0,4);
    if(j!==jahr){ jahr=j; w.appendChild(el("div","zs-jahr",j)); }
    const d = el("div","zs-e"+(e.gross?" gross":""));
    d.innerHTML = `<div class="zs-d">${fdat(e.datum)}</div>
      <div class="zs-t">${e.url?`<a href="${esc(e.url)}" target="_blank" rel="noopener">${hervor(e.titel)}</a>`:hervor(e.titel)}</div>
      <div class="zs-q">${esc(e.quelle)}</div>`;
    d.querySelector(".zs-q").onclick = ()=>oeffne(e.rid);
    d.querySelector(".zs-q").style.cursor = "pointer";
    w.appendChild(d);
  });
  c.appendChild(w);
}

function vUrteile(c){
  const liste = sortiere(
    D.urteile.filter(u=>passt(u,["gericht","aktenzeichen","kernfrage"])),
    (a,b)=>{
      const g = {hoch:0, mittel:1, niedrig:2};
      return (g[a.bedeutung]??3)-(g[b.bedeutung]??3) ||
             String(b.datum||"").localeCompare(String(a.datum||""));
    });
  const unver = liste.filter(u=>u.verifiziert===false).length;
  const amtl = liste.filter(u=>u.quelle_art==="amtlich").length;
  c.appendChild(el("div","zaehler",
    `${liste.length} von ${D.urteile.length} Entscheidungen — ${amtl} mit amtlicher Fundstelle` +
    (unver ? `, ${unver} nicht am Primärdokument verifiziert` : "")));
  if(!liste.length) return leer(c,"Nichts gefunden.","Filter zurücksetzen oder Suchbegriff ändern.");
  const w = el("div","karten");
  liste.forEach(u=>{
    const b = el("button","karte");
    const p = u.parteien || {};
    const titel = (p.klaeger || p.beklagter)
      ? `${p.klaeger||"?"} ./. ${p.beklagter||"?"}` : (u.gericht || u.id);
    b.innerHTML = `<div class="karte-kopf">
        <span class="karte-titel">${hervor(titel)}</span>
        ${u.bedeutung==="hoch"?'<span class="plakette p-akz">Leitentscheidung</span>':""}
        ${plakette(u.status)}</div>
      <div class="karte-meta">
        <span class="plakette p-grau">${esc(jname(u.jurisdiktion))}</span>
        <span>${esc(u.gericht||"")}</span>
        ${u.aktenzeichen?`<code>${hervor(u.aktenzeichen)}</code>`:""}
        ${u.datum?`<code>${fdat(u.datum)}</code>`:""}
        ${u.verifiziert===false?'<span class="plakette p-amber">unverifiziert</span>':""}
        ${QUELLE[u.quelle_art]||""}
        ${u.zweifelhaft?'<span class="plakette p-rot">zweifelhaft</span>':""}
        ${u.verfahrensstadium?`<span class="plakette p-blau">${esc(u.verfahrensstadium.split("—")[0].trim())}</span>`:""}
        ${(u.instanzenzug||[]).length?`<span>${u.instanzenzug.length+1} Instanzen</span>`:""}</div>
      ${u.kernfrage?`<div class="karte-text">${hervor(u.kernfrage)}</div>`:""}
      <div class="achsen">${(u.themenachsen||[]).map(t=>
        `<span class="achse">${esc(D._thema[t]?.name.split(" und ")[0]||t)}</span>`).join("")}</div>`;
    b.onclick = ()=>oeffneUrteil(u.id);
    w.appendChild(b);
  });
  c.appendChild(w);
}

function vStreit(c){
  const liste = (D.streitstaende||[]).filter(s=>{
    if(Z.suche && !(s._such||"").includes(Z.suche.toLowerCase())) return false;
    if(Z.thema.size && !(s.themenachsen||[]).some(t=>Z.thema.has(t))) return false;
    if(Z.jur.size && !(s.jurisdiktionen||[]).some(j=>Z.jur.has(j))) return false;
    return true;
  });
  c.appendChild(el("div","zaehler",
    `${liste.length} Rechtsfragen, die von verschiedenen Gerichten gegensätzlich beantwortet werden`));
  if(!liste.length) return leer(c,"Nichts gefunden.");
  const titelVon = id => {
    const u = D.urteile.find(x=>x.id===id);
    const teile = String(id).split("-");
    const jahr = teile[1] && /^\d{4}$/.test(teile[1]) ? teile[1] : String(u?.datum||"").slice(0,4);
    const name = (teile[2] || "").replace(/^\w/, c=>c.toUpperCase());
    return name ? `${name} ${jahr}`.trim() : (u?.gericht || id);
  };
  const w = el("div","karten");
  liste.forEach(s=>{
    const d = el("div","streit");
    d.innerHTML = `
      <div>
        <div class="streit-t">${hervor(s.titel)}</div>
        <div class="karte-meta" style="margin-top:6px">
          ${(s.jurisdiktionen||[]).map(j=>`<span class="plakette p-grau">${esc(jname(j))}</span>`).join("")}
          ${(s.themenachsen||[]).map(t=>`<span class="achse">${esc(D._thema[t]?.name||t)}</span>`).join("")}
        </div>
      </div>
      ${s.frage?`<div class="streit-f">${hervor(s.frage)}</div>`:""}
      ${s.video_haenger?`<div class="haenger">${hervor(s.video_haenger)}</div>`:""}
      ${s.stand?`<div class="streit-ab"><b>Stand</b>${hervor(s.stand)}</div>`:""}
      <div class="pos">${(s.positionen||[]).map(p=>`
        <div class="pos-e">
          <div class="pos-h">${esc(p.position||"")}</div>
          <div class="pos-g">${esc(p.gericht||"")}</div>
          <div class="pos-b">${esc(p.begruendung||"")}</div>
          ${(p.urteile||[]).length?`<div class="pos-u">${p.urteile.map(u=>
            `<span class="beleg" data-u="${esc(u)}">${esc(titelVon(u))}</span>`).join("")}</div>`:""}
        </div>`).join("")}</div>
      ${(s.unterfragen||[]).length?`<div class="pos">${s.unterfragen.map(u=>`
        <div class="unfrage">
          <div class="unfrage-f">${esc(u.frage||"")}</div>
          ${u.ja?`<div class="unfrage-s"><span>dafür</span><span>${esc(u.ja)}</span></div>`:""}
          ${u.nein?`<div class="unfrage-s"><span>dagegen</span><span>${esc(u.nein)}</span></div>`:""}
        </div>`).join("")}</div>`:""}
      ${(s._literatur||[]).length?`<div class="streit-ab"><b>Dazu geschrieben (${
        s._literatur.length})</b><div class="pos-u" style="margin-top:5px">${
        s._literatur.slice(0,8).map(i=>{const l=D.literatur.find(x=>x.id===i);
          return l?`<span class="beleg" data-lit="${esc(i)}"${
            l.prioritaet==="pflicht"?' style="border-color:var(--rot);color:var(--rot)"':""
          }>${esc((l.autoren||[""])[0].split(",")[0])} ${l.jahr||""}</span>`:"";}).join("")}${
        s._literatur.length>8?`<span class="beleg">+${s._literatur.length-8}</span>`:""}</div></div>`:""}
      ${s.aufloesung?`<div class="streit-ab"><b>Auflösung erwartet durch</b>${esc(s.aufloesung)}</div>`:""}
      ${s.eigene_bewertung?`<div class="streit-ab"><b>Eigene Bewertung</b>${esc(s.eigene_bewertung)}</div>`:""}
      ${(s.fehlende_belege||[]).length?`<details class="luecken"><summary>Noch zu beschaffen (${
        s.fehlende_belege.length})</summary><ul>${s.fehlende_belege.map(b=>
        `<li>${esc(typeof b==="string"?b:(b.was||b.fundstelle||JSON.stringify(b)))}</li>`).join("")}</ul></details>`:""}`;
    d.querySelectorAll(".beleg").forEach(b=>{
      if(b.dataset.u) b.onclick = ()=>oeffneUrteil(b.dataset.u);
      if(b.dataset.lit) b.onclick = ()=>oeffneLiteratur(b.dataset.lit);
    });
    w.appendChild(d);
  });
  c.appendChild(w);
}

function vLiteratur(c){
  const liste = D.literatur.filter(l=>{
    if(Z.norm.size && !(l.normen||[]).some(n=>Z.norm.has(n))) return false;
    if(Z.suche && !(l._such||"").includes(Z.suche.toLowerCase())) return false;
    if(Z.thema.size && !(l.themenachsen||[]).some(t=>Z.thema.has(t))) return false;
    if(Z.jur.size && !(l.jurisdiktionen||[]).some(j=>Z.jur.has(j))) return false;
    return true;
  });
  sortiere(liste, (a,b)=>{
    const p = {pflicht:0, wichtig:1, optional:2};
    return (p[a.prioritaet]??3)-(p[b.prioritaet]??3) || (b.jahr||0)-(a.jahr||0)
           || (b.zitationen||0)-(a.zitationen||0);
  });
  const pflicht = liste.filter(l=>l.prioritaet==="pflicht").length;
  const frei = liste.filter(l=>["open-access","ssrn","repositorium"].includes(l.zugang)).length;
  c.appendChild(el("div","zaehler",
    `${liste.length} Titel — ${pflicht} Pflichtlektüre, ${frei} frei zugänglich`));
  if(!liste.length) return leer(c,"Nichts gefunden.","Filter zurücksetzen oder Suchbegriff ändern.");
  const ZUGANG = {"open-access":"frei", ssrn:"SSRN", repositorium:"Repositorium",
    verlagsseite:"Verlag", beck:"nur Beck", juris:"nur juris", kauf:"kostenpflichtig",
    bibliothek:"Bibliothek", heinonline:"HeinOnline", westlaw:"Westlaw"};
  const w = el("div","karten");
  liste.forEach(l=>{
    const b = el("button","karte");
    const frei_ = ["open-access","ssrn","repositorium"].includes(l.zugang);
    b.innerHTML = `<div class="karte-kopf">
        <span class="karte-titel">${hervor(l.titel)}</span>
        ${l.prioritaet==="pflicht"?'<span class="plakette p-rot">Pflicht</span>'
          :l.prioritaet==="wichtig"?'<span class="plakette p-amber">wichtig</span>':""}</div>
      <div class="karte-meta">
        <span>${esc((l.autoren||[]).slice(0,3).join(" · "))}${(l.autoren||[]).length>3?" u.a.":""}</span>
        ${l.fundstelle?`<span>${hervor(l.fundstelle)}</span>`:""}
        ${l.jahr?`<code>${l.jahr}</code>`:""}
        <span class="plakette p-${frei_?"gruen":"grau"}">${esc(ZUGANG[l.zugang]||l.zugang||"")}</span>
        ${l.zitationen?`<span>${l.zitationen}× zitiert</span>`:""}
        ${l.sprache && l.sprache!=="en"?`<code>${esc(String(l.sprache).toUpperCase())}</code>`:""}</div>
      ${l.kernthese?`<div class="karte-text">${hervor(l.kernthese)}</div>`:""}
      <div class="achsen">${(l.bezug_streitstaende||[]).map(s=>{
        const st = (D.streitstaende||[]).find(x=>x.id===s);
        return `<span class="achse" style="border-color:var(--akz);color:var(--akz)">${
          esc(st?st.titel.slice(0,42):s)}</span>`;}).join("")}</div>`;
    b.onclick = ()=>oeffneLiteratur(l.id);
    w.appendChild(b);
  });
  c.appendChild(w);
}

function oeffneLiteratur(id, ohneHash){
  const l = D.literatur.find(x=>x.id===id); if(!l) return;
  if(!ohneHash) location.hash = encodeURIComponent(id);
  $("#detail-marke").textContent = (l.jurisdiktionen||[]).map(jname).join(" · ") || "Literatur";
  const TYP = {aufsatz:"Aufsatz", monografie:"Monografie", kommentar:"Kommentar",
    handbuch:"Handbuch", dissertation:"Dissertation", blogbeitrag:"Blogbeitrag",
    bericht:"Bericht", "working-paper":"Working Paper"};
  const zeilen = [["Autoren",(l.autoren||[]).join("; ")],["Fundstelle",l.fundstelle],
    ["Jahr",l.jahr],["Art",TYP[l.typ]||l.typ],["Sprache",(l.sprache||"").toUpperCase()],
    ["DOI",l.doi],["ISBN",l.isbn],["Zugang",l.zugang],
    ["Zitationen",l.zitationen],["Lesestatus",l.lesestatus]]
    .filter(z=>z[1]).map(z=>`<tr><td>${esc(z[0])}</td><td>${esc(z[1])}</td></tr>`).join("");

  const bezug = (feld, sammlung, benenner) => {
    const ids = l[feld] || []; if(!ids.length) return "";
    return `<ul class="d-liste">${ids.map(i=>{
      const e = (D[sammlung]||[]).find(x=>x.id===i);
      return `<li>${e?`<span class="beleg" data-${sammlung[0]}="${esc(i)}">${
        esc(benenner(e))}</span>`:`<code>${esc(i)}</code>`}</li>`;}).join("")}</ul>`;
  };

  $("#detail-rumpf").innerHTML = `
    <div class="d-titel">${esc(l.titel)}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
      ${l.prioritaet==="pflicht"?'<span class="plakette p-rot">Pflichtlektüre</span>':""}
      ${(l.themenachsen||[]).map(t=>`<span class="achse">${esc(D._thema[t]?.name||t)}</span>`).join("")}
    </div>
    <table class="d-tabelle">${zeilen}</table>
    ${ab("Kernthese", l.kernthese?`<div class="d-text">${esc(l.kernthese)}</div>`:"")}
    ${ab("Eigene Bewertung", l.eigene_bewertung?`<div class="d-text">${esc(l.eigene_bewertung)}</div>`:"")}
    ${ab("Zum Streitstand", bezug("bezug_streitstaende","streitstaende", e=>e.titel))}
    ${ab("Bespricht", bezug("bezug_urteile","urteile", e=>{
        const p = e.parteien||{};
        return (p.klaeger||p.beklagter) ? `${p.klaeger||"?"} ./. ${p.beklagter||"?"}` : (e.gericht||e.id);}))}
    ${ab("Zu Regelwerk", bezug("bezug_regelwerke","regelwerke", e=>e.kurztitel))}
    ${ab("Einschlägige Vorschriften", (l.normen||[]).length ? `<div class="normzeile">${
      l.normen.map(n=>{ const v=(D.normen||[]).find(x=>x.id===n);
        return `<span class="norm" data-norm="${esc(n)}" title="${esc(v?.thema||"")}">${
          esc(v?v.bezeichnung:n)}</span>`;}).join("")}</div>` : "")}
    ${l.url?`<div class="d-ab"><a href="${esc(l.url)}" target="_blank" rel="noopener">Volltext öffnen &rarr;</a></div>`
      :`<div class="d-ab"><span class="plakette p-amber">Kein freier Volltext — ${esc(l.zugang||"")}</span></div>`}
    ${notizblock(l.id, true)}`;
  offenerEintrag = {id: l.id, art: "literatur"};
  notizblockBinden(l.id, "literatur");
  bindeVerweise();
  $("#detail").hidden = false;
  if(innerWidth<=860) $("#overlay").hidden = false;
  $("#detail-rumpf").scrollTop = 0;
}

function vLernen(c){
  const heute = new Date(D.erzeugt);
  const cur = D.curriculum || [];
  // Laufendes Quartal aus dem Zeitraum ableiten
  const MONAT = {januar:0,februar:1,"märz":2,april:3,mai:4,juni:5,juli:6,august:7,
    september:8,oktober:9,november:10,dezember:11};
  const istJetzt = q => {
    const m = (q.zeitraum||"").match(/(\w+)\s*–\s*(\w+)\s*(\d{4})/);
    if(!m) return false;
    const j = +m[3], a = MONAT[m[1].toLowerCase()], b = MONAT[m[2].toLowerCase()];
    if(a==null||b==null) return false;
    const von = new Date(j, a, 1), bis = new Date(b < a ? j+1 : j, b+1, 0);
    return heute >= von && heute <= bis;
  };
  c.appendChild(el("div","zaehler",
    `${cur.length} Quartale über 24 Monate — ${(D.angebote||[]).length} Angebote erfasst`));
  const w = el("div","karten");

  cur.forEach(q => {
    const jetzt = istJetzt(q);
    const d = el("div","quartal" + (jetzt ? " jetzt" : ""));
    const lit = (q.lektuere||[]).map(i=>D.literatur.find(l=>l.id===i)).filter(Boolean);
    const ang = (q.angebote||[]).map(i=>(D.angebote||[]).find(a=>a.id===i)).filter(Boolean);
    d.innerHTML = `
      <div class="q-kopf">
        <span class="q-titel">${hervor(q.titel)}</span>
        ${jetzt ? '<span class="q-marke">läuft</span>' : ''}
        <span class="q-std">${q.stunden_pro_woche} h/Woche</span>
      </div>
      <div class="q-zeit">${esc(q.zeitraum)}</div>
      ${q.schwerpunkt?`<div class="q-block"><b>Schwerpunkt</b>${hervor(q.schwerpunkt)}</div>`:""}
      ${lit.length?`<div class="q-block"><b>Lektüre (${lit.length})</b>
        <div class="pos-u">${lit.map(l=>`<span class="beleg" data-lit="${esc(l.id)}"${
          l.prioritaet==="pflicht"?' style="border-color:var(--rot);color:var(--rot)"':""
        }>${esc((l.autoren||[""])[0].split(",")[0])} ${l.jahr||""}</span>`).join("")}</div></div>`:""}
      ${ang.length?`<div class="q-block"><b>Kurse und Termine</b>
        <div class="pos-u">${ang.map(a=>`<span class="beleg" data-ang="${esc(a.id)}">${
          esc((a.name||a.id).slice(0,38))}</span>`).join("")}</div></div>`:""}
      ${q.output?`<div class="q-block"><b>Ergebnis</b>${hervor(q.output)}</div>`:""}
      ${q.meilenstein?`<div class="q-block"><b>Meilenstein</b>${esc(q.meilenstein)}</div>`:""}
      ${q.hinweis?`<div class="q-hinweis">${esc(q.hinweis)}</div>`:""}`;
    d.querySelectorAll("[data-lit]").forEach(b=>b.onclick=()=>oeffneLiteratur(b.dataset.lit));
    d.querySelectorAll("[data-ang]").forEach(b=>b.onclick=()=>oeffneAngebot(b.dataset.ang));
    w.appendChild(d);
  });

  if((D.nebenstraenge||[]).length){
    const t = el("div","zaehler","Nebenstränge — Entscheidungen mit eigenem Zeitplan");
    t.style.marginTop = "22px"; w.appendChild(t);
    D.nebenstraenge.forEach(n=>{
      const d = el("div","nebenstrang");
      const tage = n.entscheidung_bis
        ? Math.round((new Date(n.entscheidung_bis) - heute)/864e5) : null;
      d.innerHTML = `<div class="ns-kopf">
          <span class="ns-titel">${hervor(n.titel)}</span>
          ${tage!=null?`<span class="plakette p-${tage<0?"grau":tage<60?"rot":"blau"}">${
            tage<0?"entschieden?":`Entscheidung in ${tage} Tagen`}</span>`:""}</div>
        <div class="q-zeit">${esc(n.zeitraum||"")}</div>
        <div class="q-block">${hervor(n.beschreibung||"")}</div>`;
      w.appendChild(d);
    });
  }
  c.appendChild(w);
}

function oeffneAngebot(id, ohneHash){
  const a = (D.angebote||[]).find(x=>x.id===id); if(!a) return;
  if(!ohneHash) location.hash = encodeURIComponent(id);
  $("#detail-marke").textContent = {zertifikat:"Zertifikat", kurs:"Kurs",
    programm:"Programm", konferenz:"Konferenz", australien:"Australien"}[a.art] || "Angebot";
  const geld = k => {
    if(!k) return null;
    if(typeof k === "string") return k;
    if(typeof k === "object"){
      const teile = Object.entries(k).map(([n,v])=>
        v && typeof v==="object" && v.betrag!=null
          ? `${n.replace(/_/g," ")}: ${v.betrag} ${v.waehrung||""}`.trim()
          : `${n.replace(/_/g," ")}: ${v}`);
      return teile.join(" · ");
    }
    return String(k);
  };
  const zeilen = [["Anbieter",a.anbieter],["Format",a.format],["Dauer",a.dauer],
    ["Aufwand",a.aufwand_pro_woche],["Kosten",geld(a.kosten)],
    ["Prüfung",a.pruefungsformat],["Nächste Frist",a.naechste_frist||a.frist]]
    .filter(z=>z[1]).map(z=>`<tr><td>${esc(z[0])}</td><td>${esc(z[1])}</td></tr>`).join("");
  const meine = D.fristen.filter(f=>f.angebot===a.id ||
    (f.beschreibung||"").toLowerCase().includes((a.name||"").toLowerCase().slice(0,18)));
  $("#detail-rumpf").innerHTML = `
    <div class="d-titel">${esc(a.name||a.id)}</div>
    <table class="d-tabelle">${zeilen}</table>
    ${ab("Einschätzung", a.einschaetzung||a.bewertung
      ? `<div class="d-text">${esc(a.einschaetzung||a.bewertung)}</div>` : "")}
    ${ab("Inhalt", a.inhalt?`<div class="d-text">${esc(a.inhalt)}</div>`:"")}
    ${ab("Fristen", meine.length?`<ul class="d-liste">${meine.map(f=>
      `<li><code style="color:var(--akz);font:12px var(--mono)">${fdat(f.datum)}</code>
       ${f._tage!=null&&f._tage>=0?`<span class="plakette p-${f._tage<=14?"rot":"blau"}">in ${f._tage} Tagen</span>`:""}
       ${esc(f.beschreibung||"")}</li>`).join("")}</ul>`:"")}
    ${a.url?`<div class="d-ab"><a href="${esc(a.url)}" target="_blank" rel="noopener">Zum Angebot &rarr;</a></div>`:""}`;
  $("#detail").hidden = false;
  if(innerWidth<=860) $("#overlay").hidden = false;
  $("#detail-rumpf").scrollTop = 0;
}

// Ein Eintrag kann Regelwerk, Entscheidung, Literatur oder Streitstand sein.
// Diese Tabelle uebersetzt zwischen id und Anzeige, damit ein Dossier alles
// nebeneinander fuehren kann.
const SAMMLUNGEN = {
  regelwerk:  {liste:()=>D.regelwerke,    kurz:"Reg", name:e=>e.kurztitel, oeffnen:oeffne},
  urteil:     {liste:()=>D.urteile,       kurz:"Entsch", oeffnen:oeffneUrteil,
               name:e=>{const p=e.parteien||{}; return (p.klaeger||p.beklagter)
                 ? `${p.klaeger||"?"} ./. ${p.beklagter||"?"}` : (e.gericht||e.id);}},
  literatur:  {liste:()=>D.literatur,     kurz:"Lit", oeffnen:oeffneLiteratur,
               name:e=>`${(e.autoren||[""])[0].split(",")[0]}, ${e.titel}`},
  streitstand:{liste:()=>D.streitstaende||[], kurz:"Streit", name:e=>e.titel,
               oeffnen:()=>$('#reiter button[data-ansicht="streit"]').click()},
};
function eintragFinden(id, typ){
  const s = SAMMLUNGEN[typ]; if(!s) return null;
  return s.liste().find(e=>e.id===id) || null;
}
function typVon(id){
  for(const [typ,s] of Object.entries(SAMMLUNGEN))
    if(s.liste().some(e=>e.id===id)) return typ;
  return null;
}

function vDossiers(c){
  if(!S.db){
    c.innerHTML = `<div class="leer">
      <svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h10"/></svg>
      <p>${S.bereit ? "Dossiers brauchen den Speicher dieser Seite."
                    : "Speicher wird verbunden …"}<br>
      <small>${S.bereit
        ? esc(S.grund || "In dieser Ansicht nicht verfügbar") +
          " — die übrigen Reiter funktionieren normal."
        : "Einen Moment."}</small></p></div>`;
    return;
  }
  const neu = el("div","neu-dossier");
  neu.innerHTML = `<input id="dos-neu" placeholder="Neues Dossier, z. B. „DABUS und Erfinderschaft“" maxlength="80">
    <button class="wzbtn" id="dos-anlegen">Anlegen</button>`;
  c.appendChild(neu);
  const anlegen = ()=>{ const f = $("#dos-neu");
    if(f.value.trim()){ dossierAnlegen(f.value); f.value=""; } };
  $("#dos-anlegen").onclick = anlegen;
  $("#dos-neu").onkeydown = e=>{ if(e.key==="Enter") anlegen(); };

  const liste = Object.values(S.dossiers)
    .sort((a,b)=>String(b.geaendert||b.angelegt||"").localeCompare(String(a.geaendert||a.angelegt||"")));
  if(!liste.length){
    c.appendChild(el("div","hinweisleiste",
      "Noch kein Dossier. Ein Dossier sammelt Regelwerke, Entscheidungen und Literatur "
      + "zu einer Frage — quer zu allen Kategorien. Angelegt wird es hier, gefüllt aus "
      + "jeder Detailansicht heraus."));
    return;
  }
  c.appendChild(el("div","zaehler", `${liste.length} Dossiers`));
  const w = el("div","karten");
  liste.forEach(d=>{
    const k = el("div","dossier");
    const eintraege = (d.eintraege||[]).map(e=>({...e, obj: eintragFinden(e.id, e.typ)}))
      .filter(e=>e.obj);
    k.innerHTML = `<div class="dos-kopf">
        <span class="dos-titel">${hervor(d.titel||d.id)}</span>
        <span class="dos-zahl">${eintraege.length}</span>
        <button class="wzbtn" data-exp="${esc(d.id)}">Export</button>
      </div>
      ${eintraege.length ? `<div class="dos-eintraege">${eintraege.map(e=>
        `<div class="dos-e" data-id="${esc(e.id)}" data-typ="${esc(e.typ)}">
           <span class="art">${esc(SAMMLUNGEN[e.typ].kurz)}</span>
           <span>${esc(SAMMLUNGEN[e.typ].name(e.obj))}</span>
         </div>`).join("")}</div>`
        : `<div class="leerdossier">Noch leer — öffne einen Eintrag und ordne ihn hier zu.</div>`}`;
    k.querySelectorAll(".dos-e").forEach(z=>z.onclick=()=>
      SAMMLUNGEN[z.dataset.typ].oeffnen(z.dataset.id));
    const eb = k.querySelector("[data-exp]");
    if(eb) eb.onclick = ()=>{
      const lit = eintraege.filter(e=>e.typ==="literatur").map(e=>e.obj);
      if(!lit.length){ meldung("Dieses Dossier enthält keine Literatur."); return; }
      exportieren("bibtex", lit, (d.titel||d.id).toLowerCase().replace(/[^a-z0-9]+/g,"-"));
    };
    w.appendChild(k);
  });
  c.appendChild(w);
}

/* ================= Weltkarte =================
   Die Umrisse liegen in weltkarte.json: Natural Earth 1:110m (gemeinfrei),
   projiziert in Equal Earth. Flaechentreu, damit in einer Karte ueber
   Regelungsdichte kein Land groesser aussieht, als es ist.
   Erst geholt, wenn diese Ansicht zum ersten Mal geoeffnet wird - 98 KB
   gehoeren nicht in jeden Seitenaufruf.
   Erzeugt von build/weltkarte.py; laeuft nicht im taeglichen Bau mit. */
let KARTE = null, karteHolt = null;
function karteHolen(){
  if(KARTE) return Promise.resolve(KARTE);
  if(!karteHolt) karteHolt = fetch("weltkarte.json").then(r=>r.json())
    .then(k=>{ delete k._quelle; delete k._feld; return (KARTE = k); })
    .catch(()=>(KARTE = {}));
  return karteHolt;
}

const KSICHT = {x:-2.70, y:-1.33, b:5.40, h:2.40};
let kBlick = {...KSICHT};                 // ueberlebt das Neuzeichnen
let kModus = "status";

const KMODI = {
  status: {feld:"status", name:"Stand der Gesetzgebung",
    werte:[["gesetz","Gesetz erlassen"],["entwurf","Entwurf im Verfahren"],
           ["strategie","nur Strategie oder Leitlinien"],["nichts","keine Gesetzgebung"]]},
  einstufung: {feld:"einstufung", name:"Unser Arbeitsstand",
    werte:[["erfasst","erfasst"],["pflicht","zu erfassen"],
           ["beobachten","unter Beobachtung"],["nachrangig","Beobachtungsliste"]]},
};

function landPasst(l){
  if(!Z.suche) return true;
  return (l.land+" "+(l.kurztitel||"")+" "+(l.inhalt||"")+" "+(l.notiz||""))
    .toLowerCase().includes(Z.suche.toLowerCase());
}

function karteBauen(huelle, raster){
  const idx = {}; raster.forEach(l=>{ if(l.code) idx[l.code] = l; });
  const M = KMODI[kModus];
  const flaechen = [], punkte = [];
  for(const c in KARTE){
    const [d, x, y, name, klein] = KARTE[c];
    const l = idx[c];
    const kl = l ? `l-${M.feld}-${l[M.feld] || "nichts"}` : "l-aus";
    const matt = l && !landPasst(l) ? " matt" : "";
    const a = l ? ` data-c="${esc(c)}" tabindex="-1"` : "";
    if(d) flaechen.push(`<path class="wland ${kl}${matt}" d="${d}"${a}></path>`);
    if(l && (klein || !d))
      punkte.push(`<circle class="wpunkt ${kl}${matt}" cx="${x}" cy="${y}" r="0.026"${a}></circle>`);
  }
  huelle.innerHTML =
    `<svg class="wkarte" viewBox="${kBlick.x} ${kBlick.y} ${kBlick.b} ${kBlick.h}"
          role="img" aria-label="Weltkarte: ${esc(M.name)}. Die vollständige Liste steht darunter.">
       <rect class="wmeer" x="-3" y="-1.5" width="6" height="3"></rect>
       ${flaechen.join("")}${punkte.join("")}
     </svg>
     <div class="wtipp" hidden></div>
     <div class="wzoom">
       <button type="button" data-z="ein" aria-label="Näher">+</button>
       <button type="button" data-z="aus" aria-label="Weiter weg">&minus;</button>
       <button type="button" data-z="null" aria-label="Ganze Welt">Welt</button>
     </div>`;
  karteBinden(huelle, idx);
}

/* Ziehen, Rad und Knoepfe aendern nur das Sichtfeld des SVG - kein Neubau
   der Pfade, deshalb bleibt es auch auf dem Telefon fluessig. */
function karteBinden(huelle, idx){
  const svg  = huelle.querySelector(".wkarte");
  const tipp = huelle.querySelector(".wtipp");
  const setz = ()=>svg.setAttribute("viewBox",
    `${kBlick.x} ${kBlick.y} ${kBlick.b} ${kBlick.h}`);

  const zoom = (f, mx, my)=>{
    const b = Math.min(KSICHT.b, Math.max(KSICHT.b/14, kBlick.b*f));
    const g = b / kBlick.b;                       // tatsaechlicher Faktor
    kBlick.x = mx - (mx - kBlick.x)*g;
    kBlick.y = my - (my - kBlick.y)*g;
    kBlick.b = b; kBlick.h = KSICHT.h * (b/KSICHT.b);
    // im Bild bleiben
    kBlick.x = Math.min(KSICHT.x + KSICHT.b - kBlick.b, Math.max(KSICHT.x, kBlick.x));
    kBlick.y = Math.min(KSICHT.y + KSICHT.h - kBlick.h, Math.max(KSICHT.y, kBlick.y));
    setz();
  };
  const inKarte = e=>{
    const r = svg.getBoundingClientRect();
    return [kBlick.x + (e.clientX - r.left)/r.width  * kBlick.b,
            kBlick.y + (e.clientY - r.top) /r.height * kBlick.h];
  };

  huelle.querySelectorAll(".wzoom button").forEach(b=>b.onclick = ()=>{
    const mx = kBlick.x + kBlick.b/2, my = kBlick.y + kBlick.h/2;
    if(b.dataset.z === "ein") zoom(1/1.5, mx, my);
    else if(b.dataset.z === "aus") zoom(1.5, mx, my);
    else { kBlick = {...KSICHT}; setz(); }
  });
  svg.addEventListener("wheel", e=>{
    e.preventDefault();
    const [mx,my] = inKarte(e);
    zoom(e.deltaY > 0 ? 1.16 : 1/1.16, mx, my);
  }, {passive:false});

  let zieht = null, weit = 0;
  svg.addEventListener("pointerdown", e=>{
    if(e.button) return;
    // Das Ziel wird hier gemerkt: setPointerCapture leitet alle weiteren
    // Zeigerereignisse auf das SVG um, beim pointerup steht also nicht mehr
    // das Land unter e.target.
    zieht = {...inKarte(e), sx:e.clientX, sy:e.clientY,
             ziel:e.target.closest("[data-c]")}; weit = 0;
    svg.setPointerCapture(e.pointerId); svg.classList.add("zieht");
  });
  svg.addEventListener("pointermove", e=>{
    const ziel = e.target.closest("[data-c]");
    if(!zieht){
      if(ziel && idx[ziel.dataset.c]){
        const l = idx[ziel.dataset.c], M = KMODI[kModus];
        const bez = (M.werte.find(w=>w[0] === l[M.feld]) || ["","—"])[1];
        tipp.innerHTML = `<b>${esc(l.land)}</b><span>${esc(bez)}</span>` +
          (l.kurztitel ? `<em>${esc(l.kurztitel)}</em>` : "");
        tipp.hidden = false;
        const r = huelle.getBoundingClientRect();
        tipp.style.left = Math.max(4, Math.min(r.width - 190, e.clientX - r.left + 14)) + "px";
        tipp.style.top  = Math.max(4, e.clientY - r.top - 8) + "px";
        svg.querySelectorAll(".hell").forEach(x=>x.classList.remove("hell"));
        svg.querySelectorAll(`[data-c="${CSS.escape(ziel.dataset.c)}"]`)
           .forEach(x=>x.classList.add("hell"));
      } else {
        tipp.hidden = true;
        svg.querySelectorAll(".hell").forEach(x=>x.classList.remove("hell"));
      }
      return;
    }
    weit = Math.max(weit, Math.abs(e.clientX - zieht.sx) + Math.abs(e.clientY - zieht.sy));
    const [mx,my] = inKarte(e);
    kBlick.x = Math.min(KSICHT.x + KSICHT.b - kBlick.b,
               Math.max(KSICHT.x, kBlick.x - (mx - zieht[0])));
    kBlick.y = Math.min(KSICHT.y + KSICHT.h - kBlick.h,
               Math.max(KSICHT.y, kBlick.y - (my - zieht[1])));
    setz();
  });
  const los = ()=>{
    if(zieht && weit < 5 && zieht.ziel && idx[zieht.ziel.dataset.c])
      oeffneLand(idx[zieht.ziel.dataset.c]);
    zieht = null; svg.classList.remove("zieht");
  };
  svg.addEventListener("pointerup", los);
  svg.addEventListener("pointercancel", ()=>{ zieht = null; svg.classList.remove("zieht"); });
  svg.addEventListener("pointerleave", ()=>{
    tipp.hidden = true;
    svg.querySelectorAll(".hell").forEach(x=>x.classList.remove("hell"));
  });
}

function vWelt(c){
  const raster = D.weltraster || [];
  const GRUPPEN = [
    ["erfasst", "Erfasst", "Vollständig in der Datenbasis — Regelwerke, Verfahrensdokumente, Rechtsprechung."],
    ["pflicht", "Zu erfassen", "Große Volkswirtschaft oder eigenständiger Regelungsansatz. Gehört in den Bestand, fehlt noch."],
    ["beobachten", "Unter Beobachtung", "Vorhaben im Gang. Vierteljährliche Prüfung genügt, bis sich etwas bewegt."],
    ["nachrangig", "Beobachtungsliste", "Keine Gesetzgebung in Sicht. Steht hier, damit es nicht übersehen wird, wenn sich das ändert."],
  ];
  const STATUS = {gesetz:"Gesetz erlassen", entwurf:"Entwurf im Verfahren",
                  strategie:"nur Strategie", nichts:"nichts"};

  c.appendChild(el("div","zaehler",
    `${raster.length} Staaten beobachtet, ${D.statistik.laender_erfasst} davon vollständig erfasst`));

  /* --- Karte --- */
  const M = KMODI[kModus];
  const kw = el("div","wkasten");
  const leiste = el("div","wleiste");
  leiste.innerHTML =
    `<div class="segment" role="group" aria-label="Einfärbung">` +
    Object.entries(KMODI).map(([k,m])=>
      `<button type="button" data-m="${k}"${k===kModus?' class="an" aria-pressed="true"':' aria-pressed="false"'}>${esc(m.name)}</button>`).join("") +
    `</div><div class="wlegende">` +
    M.werte.map(([w,n])=>
      `<span><i class="l-${M.feld}-${w}"></i>${esc(n)}</span>`).join("") +
    `<span><i class="l-aus"></i>nicht beobachtet</span></div>`;
  leiste.querySelectorAll("[data-m]").forEach(b=>b.onclick = ()=>{ kModus = b.dataset.m; zeichne(); });
  kw.appendChild(leiste);
  const huelle = el("div","whuelle");
  huelle.innerHTML = '<div class="wladen">Karte wird geladen …</div>';
  kw.appendChild(huelle);
  c.appendChild(kw);
  karteHolen().then(k=>{
    if(!document.body.contains(huelle)) return;      // Ansicht schon gewechselt
    if(!k || !Object.keys(k).length){
      huelle.innerHTML = '<div class="wladen">Die Karte konnte nicht geladen werden. '
        + 'Die Liste darunter enthält dieselben Staaten.</div>';
      return;
    }
    karteBauen(huelle, raster);
  });

  c.appendChild(el("div","hinweisleiste",
    "Der Zweck dieser Ansicht ist nicht Vollständigkeit, sondern dass kein Sonderweg "
    + "übersehen wird, weil das Land klein ist. Die Karte zeigt den gewählten Maßstab, "
    + "die Liste darunter unseren Arbeitsstand. Kleinstaaten stehen als Punkt."));

  const gefiltert = landPasst;
  GRUPPEN.forEach(([schl, titel, erklaerung])=>{
    const teil = raster.filter(l=>l.einstufung===schl).filter(gefiltert);
    if(!teil.length) return;
    const g = el("div","wr-gruppe");
    g.innerHTML = `<div class="wr-kopf"><h3>${esc(titel)}</h3><span class="n">${teil.length}</span></div>
      <div class="wr-erklaerung">${esc(erklaerung)}</div>`;
    const r = el("div","wr-raster");
    teil.forEach(l=>{
      const b = el("button","wr-land hat-"+(l.status||"nichts"));
      b.innerHTML = `<span class="wr-name">${hervor(l.land)}</span>
        <span class="wr-status">${esc(STATUS[l.status]||"—")}${
          l.regelwerke_erfasst?` · ${l.regelwerke_erfasst} Regelwerke`:""}</span>
        ${l.kurztitel?`<span class="wr-titel" title="${esc(l.kurztitel)}">${esc(l.kurztitel)}</span>`:""}`;
      b.onclick = ()=>oeffneLand(l);
      r.appendChild(b);
    });
    g.appendChild(r); c.appendChild(g);
  });

  const sw = (D.sonderwege||[]).filter(s=>!Z.suche ||
    (s.land+" "+(s.was||"")+" "+(s.warum_bemerkenswert||"")).toLowerCase().includes(Z.suche.toLowerCase()));
  if(sw.length){
    const t = el("div","zaehler","Sonderwege — Ansätze, die größere Rechtsordnungen nicht kennen");
    t.style.marginTop = "26px"; c.appendChild(t);
    const w = el("div","karten");
    sw.forEach(s=>{
      const d = el("div","sonderweg");
      d.innerHTML = `<div class="sw-land">${hervor(s.land)}</div>
        <div class="sw-was">${hervor(s.was||"")}</div>
        <div class="sw-warum">${hervor(s.warum_bemerkenswert||"")}</div>`;
      w.appendChild(d);
    });
    c.appendChild(w);
  }
}

function oeffneLand(l){
  $("#detail-marke").textContent = "Weltraster";
  const STATUS = {gesetz:"Gesetz erlassen", entwurf:"Entwurf im Verfahren",
                  strategie:"nur Strategie oder Leitlinien", nichts:"keine Gesetzgebung"};
  const EINST = {erfasst:"vollständig erfasst", pflicht:"zu erfassen",
                 beobachten:"unter Beobachtung", nachrangig:"Beobachtungsliste"};
  const zeilen = [["Stand der Gesetzgebung", STATUS[l.status]],
    ["Unser Arbeitsstand", EINST[l.einstufung]],
    ["EU-Mitglied", l.eu_mitglied ? "ja" : null],
    ["Durchführung der KI-VO", l.durchfuehrung_kivo],
    ["Eigenständige Regelung", l.eigenstaendige_regelung===true ? "ja"
      : l.eigenstaendige_regelung===false ? "nein" : null],
    ["Regelwerk", l.kurztitel], ["Datum", l.datum ? fdat(l.datum) : null],
    ["Fundstelle", l.fundstelle],
    ["Erfasste Regelwerke", l.regelwerke_erfasst],
    ["Zuletzt geprüft", l.letzte_pruefung ? fdat(l.letzte_pruefung) : null]]
    .filter(z=>z[1]).map(z=>`<tr><td>${esc(z[0])}</td><td>${esc(z[1])}</td></tr>`).join("");
  const eigene = (D.regelwerke||[]).filter(r=>r.jurisdiktion===l.code);
  $("#detail-rumpf").innerHTML = `
    <div class="d-titel">${esc(l.land)}</div>
    <table class="d-tabelle">${zeilen}</table>
    ${ab("Inhalt", l.inhalt?`<div class="d-text">${esc(l.inhalt)}</div>`:"")}
    ${ab("Einordnung", l.notiz?`<div class="d-text">${esc(l.notiz)}</div>`:"")}
    ${ab(`Im Bestand (${eigene.length})`, eigene.length
      ? `<div class="pos-u">${eigene.slice(0,24).map(r=>
          `<span class="beleg" data-r="${esc(r.id)}">${esc(r.kurztitel.slice(0,34))}</span>`).join("")}</div>` : "")}
    ${l.url?`<div class="d-ab"><a href="${esc(l.url)}" target="_blank" rel="noopener">Amtlicher Text &rarr;</a></div>`:""}`;
  bindeVerweise();
  $("#detail").hidden = false;
  if(innerWidth<=860) $("#overlay").hidden = false;
  $("#detail-rumpf").scrollTop = 0;
}

function vMatrix(c){
  const jur = D.taxonomie.jurisdiktionen.filter(j=>
    D.regelwerke.some(r=>r.jurisdiktion===j.id));
  const themen = D.taxonomie.themenachsen;
  c.appendChild(el("div","zaehler","Belegung Themenachsen × Rechtsordnungen — leere Zellen sind der Arbeitsvorrat"));
  const h = el("div","matrix-huelle");
  let s = '<table class="matrix"><thead><tr><th>Themenachse</th>';
  jur.forEach(j=>s += `<th>${esc(j.name.replace("Europäische Union","EU").replace("Vereinigte Staaten","USA").replace("Vereinigtes Königreich","UK"))}</th>`);
  s += "<th>Σ</th></tr></thead><tbody>";
  themen.forEach(t=>{
    let summe = 0;
    let zeile = `<tr><th title="${esc(t.beschreibung||"")}">${esc(t.name)}</th>`;
    jur.forEach(j=>{
      const n = D.regelwerke.filter(r=>r.jurisdiktion===j.id && (r.themenachsen||[]).includes(t.id)).length;
      summe += n;
      zeile += `<td class="${n?"hat":""}">${n||"·"}</td>`;
    });
    s += zeile + `<td class="${summe?"hat":""}">${summe||"·"}</td></tr>`;
  });
  h.innerHTML = s + "</tbody></table>";
  c.appendChild(h);
}

/* ---------------- Detailansicht ---------------- */
function ausHash(){
  const id = decodeURIComponent(location.hash.slice(1));
  if(!id){ zuDetail(true); return; }
  if(D.regelwerke.some(r=>r.id===id)) oeffne(id, true);
  else if(D.urteile.some(u=>u.id===id)) oeffneUrteil(id, true);
  else if(D.literatur.some(l=>l.id===id)) oeffneLiteratur(id, true);
  else if((D.angebote||[]).some(a=>a.id===id)) oeffneAngebot(id, true);
}
function zuDetail(ohneHash){
  offenerEintrag = null;
  $("#detail").hidden = true; $("#overlay").hidden = true;
  if(!ohneHash && location.hash) history.pushState("", "", location.pathname + location.search);
}

// Notizen, Lesestatus und Dossierzuordnung haengen an jedem Eintrag.
// Ohne Speicher wird der Block weggelassen statt kaputt angezeigt.
function notizblock(id, mitLesestatus){
  if(!S.db) return "";
  const text = S.notizen[id] || "";
  const stand = S.notizen[id+"__stand"];
  const st = S.status[id] || "ungelesen";
  const STUFEN = [["ungelesen","ungelesen"],["angelesen","angelesen"],
                  ["gelesen","gelesen"],["exzerpiert","exzerpiert"]];
  const dos = Object.values(S.dossiers);
  return `<div class="notizblock">
    <h3>Meine Notiz</h3>
    <textarea class="notizfeld" id="notiz-feld" placeholder="Gedanken, Exzerpt, offene Frage …">${esc(text)}</textarea>
    <div class="notizfuss">
      <span>wird automatisch gespeichert</span>
      ${stand?`<span class="stand">${fdat(stand)}</span>`:""}
    </div>
    ${mitLesestatus?`<div class="lesestatus">${STUFEN.map(([w,t])=>
      `<button class="lsbtn${st===w?" an":""}" data-ls="${w}">${t}</button>`).join("")}</div>`:""}
    ${dos.length?`<div class="dossierwahl">${dos.map(d=>{
      const drin = (d.eintraege||[]).some(e=>e.id===id);
      return `<button class="dwbtn${drin?" drin":""}" data-dos="${esc(d.id)}">${
        drin?"✓ ":"+ "}${esc(d.titel||d.id)}</button>`;}).join("")}</div>`
      : `<div class="notizfuss">Noch kein Dossier angelegt — im Reiter „Dossiers“.</div>`}
  </div>`;
}

function notizblockBinden(id, typ){
  const f = $("#notiz-feld"); if(!f) return;
  f.oninput = ()=>{ S.notizen[id] = f.value; notizSichern(id, f.value); };
  $("#detail-rumpf").querySelectorAll("[data-ls]").forEach(b=>b.onclick=()=>{
    statusSetzen(id, b.dataset.ls);
    $("#detail-rumpf").querySelectorAll("[data-ls]").forEach(x=>
      x.classList.toggle("an", x.dataset.ls===b.dataset.ls));
  });
  $("#detail-rumpf").querySelectorAll("[data-dos]").forEach(b=>b.onclick=()=>{
    dossierSchalten(b.dataset.dos, id, typ);
  });
}

// Nach einer Aenderung im Speicher die offene Detailansicht neu aufbauen
let offenerEintrag = null;
function detailAuffrischen(){
  if(!offenerEintrag) return;
  const {id, art} = offenerEintrag;
  ({regelwerk:oeffne, urteil:oeffneUrteil, literatur:oeffneLiteratur,
    angebot:oeffneAngebot}[art] || (()=>{}))(id, true);
}

// Alle anklickbaren Verweise in der Detailansicht an einer Stelle binden.
function bindeVerweise(){
  const r = $("#detail-rumpf");
  r.querySelectorAll("[data-u]").forEach(b=>b.onclick=()=>oeffneUrteil(b.dataset.u));
  r.querySelectorAll("[data-lit]").forEach(b=>b.onclick=()=>oeffneLiteratur(b.dataset.lit));
  r.querySelectorAll("[data-r]").forEach(b=>b.onclick=()=>oeffne(b.dataset.r));
  r.querySelectorAll("[data-ang]").forEach(b=>b.onclick=()=>oeffneAngebot(b.dataset.ang));
  r.querySelectorAll("[data-s]").forEach(b=>b.onclick=()=>{
    $('#reiter button[data-ansicht="streit"]').click(); zuDetail(); });
  // Eine Vorschrift anzuklicken filtert den ganzen Bestand darauf.
  r.querySelectorAll("[data-norm]").forEach(b=>b.onclick=()=>{
    Z.norm.clear(); Z.norm.add(b.dataset.norm);
    if(!["urteile","literatur"].includes(Z.ansicht))
      $('#reiter button[data-ansicht="urteile"]').click();
    else zeichne();
    normChipsZeichnen($("#f-normsuche").value.trim().toLowerCase());
    zuDetail();
    meldung("Gefiltert auf " + b.textContent);
  });
}

function ab(titel, inhalt){
  return inhalt ? `<div class="d-ab"><h3>${esc(titel)}</h3>${inhalt}</div>` : "";
}

function oeffne(id, ohneHash){
  const r = D.regelwerke.find(x=>x.id===id); if(!r) return;
  if(!ohneHash) location.hash = encodeURIComponent(id);
  $("#detail-marke").textContent = jname(r.jurisdiktion);

  const zeilen = [
    ["Status", (r.status_detail||D._status[r.status]?.name||"")],
    ["Fundstelle", r.fundstelle],
    ["Verfahren", r.verfahrensnummer],
    ["CELEX", r.celex],
    ["ELI", r.eli ? `<a href="${esc(r.eli)}" target="_blank" rel="noopener">${esc(r.eli)}</a>` : null],
    ["In Kraft", r.inkrafttreten?.datum ? fdat(r.inkrafttreten.datum) +
       (r.inkrafttreten.verifiziert===false ? " (unverifiziert)" : "") : null],
    ["Geprüft", r.letzte_pruefung ? fdat(r.letzte_pruefung) : null],
  ].filter(z=>z[1]).map(z=>`<tr><td>${esc(z[0])}</td><td>${z[0]==="ELI"?z[1]:esc(z[1])}</td></tr>`).join("");

  const anwend = (r.anwendungsdaten||[]).length ? `<ul class="d-liste">${
    r.anwendungsdaten.map(a=>`<li><code style="color:var(--akz);font:12px var(--mono)">${fdat(a.datum)}</code> — ${esc(a.was_gilt||"")}${
      a.verifiziert===false?' <span class="plakette p-amber">unverifiziert</span>':""}</li>`).join("")}</ul>` : "";

  const nachTyp = {};
  (r.dokumente||[]).forEach(d=>{ (nachTyp[d.typ||"bericht"] ||= []).push(d); });
  const reihenfolge = ["entwurf","folgenabschaetzung","stellungnahme","konsultation",
    "ausschussbericht","aenderungsantrag","kompromiss","abstimmung","plenarprotokoll",
    "endfassung","konsolidiert","delegiert","leitlinie","norm","bericht",
    "pressemitteilung","uebersicht"];
  const doks = Object.keys(nachTyp).sort((a,b)=>
      (reihenfolge.indexOf(a)+1||99)-(reihenfolge.indexOf(b)+1||99)).map(typ=>`
    <div style="margin-bottom:16px">
      <div style="font-size:11px;color:var(--txt3);margin-bottom:6px;font-weight:600">
        ${esc(D._doktyp[typ]||typ)}</div>
      <div class="d-liste">${nachTyp[typ].sort((a,b)=>String(a.datum||"").localeCompare(String(b.datum||""))).map(d=>`
        <div class="dok">
          <span class="dok-d">${d.datum?fdat(d.datum):"—"}</span>
          <span class="dok-h">
            ${d.url?`<a class="dok-t" href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.titel||d.typ_original||"Dokument")}</a>`
                   :`<span class="dok-t">${esc(d.titel||"Dokument")}</span>`}
            <span class="dok-m">
              ${d.urheber?`<span>${esc(d.urheber)}</span>`:""}
              ${d.sprache?`<span>${esc(String(d.sprache).toUpperCase())}</span>`:""}
              ${d.verifiziert===false?'<span class="plakette p-amber">unverifiziert</span>':""}
            </span>
            ${d.notiz?`<div class="dok-n">${esc(d.notiz)}</div>`:""}
          </span>
          ${d.url?'<svg class="pfeil" viewBox="0 0 24 24"><path d="M7 17L17 7M8 7h9v9"/></svg>':""}
        </span></div>`).join("")}</div></div>`).join("");

  const punkte = arr => Array.isArray(arr) && arr.length
    ? `<ul class="d-punkte">${arr.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>` : "";

  const meineFristen = D.fristen.filter(f=>f.regelwerk===r.id);
  const fristenHtml = meineFristen.length ? `<ul class="d-liste">${meineFristen.map(f=>
    `<li><code style="color:var(--akz);font:12px var(--mono)">${fdat(f.datum)}</code>
      ${f._tage!=null?`<span class="plakette p-${f._tage<0?"grau":f._tage<=30?"rot":f._tage<=120?"amber":"blau"}">${
        f._tage<0?`vor ${-f._tage} T.`:`in ${f._tage} T.`}</span>`:""}
      ${esc(f.beschreibung||"")}</li>`).join("")}</ul>` : "";

  $("#detail-rumpf").innerHTML = `
    <div class="d-titel">${esc(r.kurztitel)}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
      ${plakette(r.status)}
      ${(r.themenachsen||[]).map(t=>`<span class="achse">${esc(D._thema[t]?.name||t)}</span>`).join("")}
    </div>
    ${r.offizieller_titel?`<div class="d-amtlich">${esc(r.offizieller_titel)}</div>`:""}
    <table class="d-tabelle">${zeilen}</table>
    ${ab("Anwendungsdaten", anwend)}
    ${ab("Fristen", fristenHtml)}
    ${ab("Regelungsschwerpunkte", punkte(r.regelungsschwerpunkte))}
    ${ab("Offene Punkte", punkte(r.offene_punkte))}
    ${ab(`Dokumente (${(r.dokumente||[]).length})`, doks)}
    ${ab("Eigene Bewertung", r.eigene_bewertung?`<div class="d-text">${esc(r.eigene_bewertung)}</div>`:"")}
    ${ab(`Rechtsprechung dazu (${(r._urteile||[]).length})`, (r._urteile||[]).length
      ? `<div class="pos-u">${r._urteile.slice(0,20).map(i=>{
          const u = D.urteile.find(x=>x.id===i); if(!u) return "";
          const p = u.parteien||{};
          return `<span class="beleg" data-u="${esc(i)}">${esc(
            ((p.klaeger||u.gericht||i).split(/[ ,]/)[0])+" "+String(u.datum||"").slice(0,4))}</span>`;
        }).join("")}${r._urteile.length>20?`<span class="beleg">+${r._urteile.length-20}</span>`:""}</div>` : "")}
    ${ab(`Literatur dazu (${(r._literatur||[]).length})`, (r._literatur||[]).length
      ? `<div class="pos-u">${r._literatur.slice(0,20).map(i=>{
          const l = D.literatur.find(x=>x.id===i); if(!l) return "";
          return `<span class="beleg" data-lit="${esc(i)}"${
            l.prioritaet==="pflicht"?' style="border-color:var(--rot);color:var(--rot)"':""
          }>${esc((l.autoren||[""])[0].split(",")[0])} ${l.jahr||""}</span>`;
        }).join("")}${r._literatur.length>20?`<span class="beleg">+${r._literatur.length-20}</span>`:""}</div>` : "")}
    ${ab("Monitoring", punkte(r.monitoring_quellen))}
    ${notizblock(r.id, false)}`;
  offenerEintrag = {id: r.id, art: "regelwerk"};
  notizblockBinden(r.id, "regelwerk");
  bindeVerweise();

  $("#detail").hidden = false;
  if(innerWidth<=860) $("#overlay").hidden = false;
  $("#detail-rumpf").scrollTop = 0;
}

function oeffneUrteil(id, ohneHash){
  const u = D.urteile.find(x=>x.id===id); if(!u) return;
  if(!ohneHash) location.hash = encodeURIComponent(id);
  $("#detail-marke").textContent = jname(u.jurisdiktion);
  const p = u.parteien || {};
  const titel = (p.klaeger || p.beklagter)
    ? `${p.klaeger||"?"} ./. ${p.beklagter||"?"}` : (u.gericht || u.id);
  const INSTANZ = {erstinstanzlich:"Erste Instanz", berufung:"Berufung",
    revision:"Revision", verfassungsgericht:"Verfassungsgericht",
    schiedsgericht:"Schiedsgericht", behoerde:"Behörde"};
  const zeilen = [["Gericht",u.gericht],["Instanz",INSTANZ[u.instanz]||u.instanz],
    ["Aktenzeichen",u.aktenzeichen],["ECLI",u.ecli],
    ["Datum",u.datum?fdat(u.datum):null],["Verfahrensstand",D._status[u.status]?.name],
    ["Anspruchsgrundlage",u.anspruchsgrundlage],
    ["Aktenzeichen (Original)",u.aktenzeichen_original],
    ["Art des Dokuments",u.dokumenttyp],
    ["Verfahrensstadium",u.verfahrensstadium],
    ["Gefunden über",u.quelle_tracker],
    ["Geprüft",u.letzte_pruefung?fdat(u.letzte_pruefung):null]]
    .filter(z=>z[1]).map(z=>`<tr><td>${esc(z[0])}</td><td>${esc(z[1])}</td></tr>`).join("");

  const zug = (u.instanzenzug||[]).map(i=>D.urteile.find(x=>x.id===i)).filter(Boolean);
  const zugHtml = zug.length ? `<div class="instanzen">${
    zug.sort((a,b)=>String(a.datum||"").localeCompare(String(b.datum||"")))
       .map(x=>`<span class="beleg" data-u="${esc(x.id)}">${esc(
         (INSTANZ[x.instanz]||"").split(" ")[0] || x.gericht?.slice(0,22) || x.id)}${
         x.datum?" · "+fdat(x.datum):""}</span>`).join('<span class="pfeilchen">→</span>')
    }</div>` : "";

  const streit = (D.streitstaende||[]).filter(s=>
    (s.positionen||[]).some(pos=>(pos.urteile||[]).includes(u.id)));
  const streitHtml = streit.length ? `<ul class="d-liste">${streit.map(s=>
    `<li><b>${esc(s.titel)}</b><br><span style="color:var(--txt2);font-size:13px">${
      esc(s.frage||"")}</span></li>`).join("")}</ul>` : "";

  $("#detail-rumpf").innerHTML = `
    <div class="d-titel">${esc(titel)}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px">
      ${u.bedeutung==="hoch"?'<span class="plakette p-akz">Leitentscheidung</span>':""}
      ${plakette(u.status)}
      ${u.verifiziert===false?'<span class="plakette p-amber">nicht am Primärdokument verifiziert</span>':""}
      ${QUELLE[u.quelle_art]||""}
      ${u.zweifelhaft?'<span class="plakette p-rot">Eintrag zweifelhaft</span>':""}
      ${(u.themenachsen||[]).map(t=>`<span class="achse">${esc(D._thema[t]?.name||t)}</span>`).join("")}
    </div>
    <table class="d-tabelle">${zeilen}</table>
    ${ab("Sachverhalt", u.sachverhalt?`<div class="d-text">${esc(u.sachverhalt)}</div>`:"")}
    ${ab("Kernfrage", u.kernfrage?`<div class="d-text">${esc(u.kernfrage)}</div>`:"")}
    ${ab("Ergebnis", u.ergebnis?`<div class="d-text">${esc(u.ergebnis)}</div>`:"")}
    ${ab("Einschlägige Vorschriften", (u.normen||[]).length ? `<div class="normzeile">${
      u.normen.map(n=>{ const v=(D.normen||[]).find(x=>x.id===n);
        return `<span class="norm" data-norm="${esc(n)}" title="${esc(v?.thema||"")}">${
          esc(v?v.bezeichnung:n)}</span>`;}).join("")}</div>` : "")}
    ${ab("Instanzenzug", zugHtml)}
    ${ab(`Besprochen von (${(u._besprochen_von||[]).length})`, (u._besprochen_von||[]).length
      ? `<div class="pos-u">${u._besprochen_von.map(i=>{
          const l = D.literatur.find(x=>x.id===i); if(!l) return "";
          return `<span class="beleg" data-lit="${esc(i)}"${
            l.prioritaet==="pflicht"?' style="border-color:var(--rot);color:var(--rot)"':""
          }>${esc((l.autoren||[""])[0].split(",")[0])} ${l.jahr||""}</span>`;}).join("")}</div>` : "")}
    ${ab("Teil des Streitstands", streitHtml)}
    ${ab("Eigene Bewertung", u.eigene_bewertung?`<div class="d-text">${esc(u.eigene_bewertung)}</div>`:"")}
    ${/* pruefvermerk wird bewusst NICHT angezeigt: das Feld ist eine interne
         Arbeitsnotiz der Pflege ("am 07.09. nicht erreichbar", "Datum
         berichtigt"). In die Oberflaeche gehoert, was gilt - nicht, wie es
         dorthin gekommen ist. Was offen ist, steht in offene_punkte. */""}
    ${(u.volltext_url||u.zusammenfassung_url||u.sekundaerquelle_url||u.suchadresse)?`<div class="d-ab"><div class="d-liste">
      ${u.volltext_url?`<div><a href="${esc(u.volltext_url)}" target="_blank" rel="noopener">${
      u.quelle_art==="amtlich"?"Amtliches Dokument öffnen":"Volltext öffnen"} &rarr;</a></div>`:""}
    ${u.sekundaerquelle_url?`<div><a href="${esc(u.sekundaerquelle_url)}" target="_blank" rel="noopener">Bericht dazu &rarr;</a> <span style="color:var(--txt3);font-size:12px">— keine Fundstelle</span></div>`:""}
    ${u.suchadresse?`<div><a href="${esc(u.suchadresse)}" target="_blank" rel="noopener">Dort selbst suchen &rarr;</a></div>`:""}
      ${u.zusammenfassung_url?`<div><a href="${esc(u.zusammenfassung_url)}" target="_blank" rel="noopener">Zusammenfassung &rarr;</a></div>`:""}
    </div></div>`:""}
    ${notizblock(u.id, false)}`;
  offenerEintrag = {id: u.id, art: "urteil"};
  notizblockBinden(u.id, "urteil");
  bindeVerweise();
  $("#detail").hidden = false;
  if(innerWidth<=860) $("#overlay").hidden = false;
  $("#detail-rumpf").scrollTop = 0;
}
