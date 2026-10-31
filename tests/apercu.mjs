import { readFileSync } from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

const script = readFileSync(new URL("../docs/apercu.user.js", import.meta.url), "utf8");
const pageMap = JSON.parse(readFileSync(new URL("../docs/pdf-pages.json", import.meta.url), "utf8"));
const { registerPageAt, locatePage } = vm.runInContext(`${readFileSync(new URL("../site/page_map.js", import.meta.url), "utf8")}\n;({ registerPageAt, locatePage })`, vm.createContext({}));
const readerContext = vm.createContext({ URL: { createObjectURL: blob => `blob:${blob}`, revokeObjectURL() {} }, document: { createElement: () => ({ getContext() {}, toBlob: resolve => resolve("jpeg") }) } });
const createPdfjsReader = vm.runInContext(`${readFileSync(new URL("../site/pdfjs_reader.js", import.meta.url), "utf8")}\n;createPdfjsReader`, readerContext);
const HASH = "#apercu=&page=6&pdf=8%2Ff%2Fe%2FCH-ACV_RN-ED-15-1.pdf&titre=Ed+15%2F1";
const ZURICH = "https://suche.staatsarchiv.djiktzh.ch/detail.aspx?id=316880";

const element = attributes => ({ ...attributes, inserted: [], getAttribute(name) { return this[name]; }, before(node) { this.inserted.push(node); }, closest: () => null, style: {} });

const page = (links, cells = {}) => ({
  readyState: "complete",
  querySelector: selector => selector in cells ? { textContent: cells[selector] } : selector.includes(".pdf") ? links[0] ?? null : null,
  querySelectorAll: selector => selector.includes('openDoc(" i') ? links : [],
  createElement: () => ({ style: {} }),
});

const fakePdfjs = () => {
  const requests = [];
  const pdfPage = { getViewport: ({ scale }) => ({ width: 1000 * scale, height: 600 * scale }), render: () => ({ promise: Promise.resolve() }), cleanup: () => { requests.push("cleanup"); } };
  const pdf = { numPages: 3, getMetadata: async () => ({ contentLength: 2048 }), getPage: async n => { requests.push(n); return pdfPage; } };
  return { requests, load: async () => ({ getDocument: options => { requests.push(options); return { promise: Promise.resolve(pdf) }; } }) };
};

const run = (href, storage = new Map(), dom = {}) => {
  const url = new URL(href);
  const replaced = [];
  const events = [];
  const dataset = {};
  vm.runInContext(script, vm.createContext({
    location: { hostname: url.hostname, origin: url.origin, pathname: url.pathname, search: url.search, hash: url.hash },
    document: { documentElement: { dataset }, readyState: "loading", addEventListener() {}, dispatchEvent: event => events.push(event.type), ...dom },
    Event: class { constructor(type) { this.type = type; } },
    history: { replaceState: (state, title, target) => replaced.push(target) },
    sessionStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) },
    addEventListener() {},
    URLSearchParams,
  }));
  return { replaced, events, dataset, storage };
};

const tests = {
  "le lecteur de PDF est inclus dans le script": () => assert.match(script, /window\.pdf = \{[^}]*imageOf/),
  "le calcul des pages est inclus dans le script": () => assert.match(script, /function registerPageAt\(part, pdf\)/),
  "la table des pages publiée donne le sommaire d'Ed 15/1 par son PDF": () => {
    const entry = Object.entries(pageMap).find(([pdf]) => pdf.endsWith("/CH-ACV_RN-ED-15-1.pdf"))[1];
    assert.equal(entry.cote, "Ed 15/1");
    assert.deepEqual(entry.pdfParts.map(part => part.pdf), [[6, 369], [376, 427]]);
  },
  "une page du PDF donne la page du registre, même en pagination décroissante": () => assert.deepEqual(
    { ...registerPageAt({ pdf: [6, 140], pages: [312, 178], anchors: [], spread: false }, 139) },
    { page: 179, approx: false },
  ),
  "entre deux repères, la page du registre est approchée": () => {
    const part = { pdf: [6, 456], pages: [1, 375], anchors: [[100, 130], [150, 190]], spread: false };
    assert.deepEqual({ ...registerPageAt(part, 130) }, { page: 100, approx: false });
    assert.deepEqual({ ...registerPageAt(part, 160) }, { page: 125, approx: true });
    assert.equal(registerPageAt(part, 500), null);
  },
  "sans repères, chaque page du PDF revient à elle-même par la page du registre": () => {
    for (const { cote, pdfParts } of Object.values(pageMap)) {
      for (const part of pdfParts.filter(part => part.pages && !part.anchors.length && !part.spread)) {
        for (let pdf = part.pdf[0]; pdf <= part.pdf[1]; pdf++) {
          assert.equal(locatePage(part, registerPageAt(part, pdf).page).pdf, pdf, `${cote}, ${part.content}, PDF p. ${pdf}`);
        }
      }
    }
  },
  "le script tourne sur le catalogue de Zurich": () => assert.match(script, /@match +https:\/\/suche\.staatsarchiv\.djiktzh\.ch\/\*/),
  "pdf.js est chargé dans une version exacte": () => assert.match(script, /pdfjs-dist@\d+\.\d+\.\d+\/build/),
  "une fiche de Zurich reçoit un bouton vers le PDF de son lien openDoc": () => {
    const link = element({ href: "JavaScript:openDoc('Dateien/310/D1550397.pdf');" });
    run(ZURICH, new Map(), page([link], { ".veXDetailAttributValue": " E III 21.1 " }));
    assert.equal(link.inserted.length, 1);
    const [button] = link.inserted;
    assert.equal(button.textContent, "PDF seitenweise durchblättern");
    const params = new URLSearchParams(button.href.slice(1));
    assert.equal(params.get("pdf"), "Dateien/310/D1550397.pdf");
    assert.equal(params.get("titre"), "E III 21.1");
  },
  "une fiche de Zurich à plusieurs PDF reçoit un bouton par PDF, sans les autres documents": () => {
    const links = ["Dateien/1.pdf", "Dateien/2.pdf", "Dateien/3.jpg"].map(path => element({ href: `JavaScript:openDoc('${path}');` }));
    run(ZURICH, new Map(), page(links));
    assert.deepEqual(links.map(link => link.inserted.length), [1, 1, 0]);
  },
  "une fiche de davel-vd.ch garde son bouton et le chemin relatif au dossier uploads": () => {
    const link = element({ pathname: "/uploads/r/null/8/f/e/CH-ACV_RN-ED-15-1.pdf" });
    run("https://davel-vd.ch/ed-15-1", new Map(), page([link], { ".referenceCode": "Ed 15/1" }));
    const params = new URLSearchParams(link.inserted[0].href.slice(1));
    assert.equal(link.inserted[0].textContent, "Feuilleter le PDF page par page");
    assert.equal(params.get("pdf"), "8/f/e/CH-ACV_RN-ED-15-1.pdf");
    assert.equal(params.get("titre"), "Ed 15/1");
  },
  "le catalogue de Zurich ignore la page en attente de davel-vd.ch": () => {
    const pending = new Map([["acv-apercu", JSON.stringify({ path: "/detail.aspx?id=316880", hash: HASH })]]);
    const { replaced, storage } = run(ZURICH, pending);
    assert.deepEqual(replaced, []);
    assert.equal(storage.size, 1);
  },
  "pdf.js ne lit le PDF que par plages et donne sa taille sans le télécharger": async () => {
    const { requests, load } = fakePdfjs();
    const reader = createPdfjsReader(path => `https://example.org/${path}`, load);
    const doc = await reader.openDoc("a.pdf");
    assert.deepEqual({ ...requests[0] }, { url: "https://example.org/a.pdf", disableAutoFetch: true, disableStream: true, rangeChunkSize: 1048576 });
    assert.deepEqual([doc.url, doc.size, doc.pages.length], ["https://example.org/a.pdf", 2048, 3]);
  },
  "pdf.js réutilise le document ouvert et l'image déjà rendue": async () => {
    const { requests, load } = fakePdfjs();
    const reader = createPdfjsReader(path => path, load);
    assert.equal(await reader.imageOf("a.pdf", 2), "blob:jpeg");
    assert.equal(await reader.imageOf("a.pdf", 2), "blob:jpeg");
    await reader.openDoc("a.pdf");
    assert.deepEqual(requests.slice(1), [2, "cleanup"]);
  },
  "après un échec de chargement de pdf.js, un nouvel essai recharge la bibliothèque": async () => {
    const { load } = fakePdfjs();
    let attempts = 0;
    const reader = createPdfjsReader(path => path, () => ++attempts === 1 ? Promise.reject(new Error("réseau")) : load());
    await assert.rejects(reader.openDoc("a.pdf"), /réseau/);
    assert.equal((await reader.openDoc("a.pdf")).size, 2048);
  },
  "sur le site, le script signale sa présence": () => {
    const { dataset, events } = run("https://nyg.github.io/acv-genealogie-index/");
    assert.equal("acvApercu" in dataset, true);
    assert.deepEqual(events, ["acv-apercu"]);
  },
  "la page de vérification de davel-vd.ch garde la page demandée": () => {
    const { storage } = run(`https://davel-vd.ch/js_challenge.html?redirect=/ed-15-1${HASH}`);
    assert.deepEqual(JSON.parse(storage.get("acv-apercu")), { path: "/ed-15-1", hash: HASH });
  },
  "la fiche retrouve la page demandée après la vérification": () => {
    const pending = new Map([["acv-apercu", JSON.stringify({ path: "/ed-15-1", hash: HASH })]]);
    const { replaced, storage } = run("https://davel-vd.ch/ed-15-1", pending);
    assert.deepEqual(replaced, [HASH]);
    assert.equal(storage.size, 0);
  },
  "une autre fiche ignore la page en attente": () => {
    const pending = new Map([["acv-apercu", JSON.stringify({ path: "/ed-15-1", hash: HASH })]]);
    const { replaced, storage } = run("https://davel-vd.ch/ed-15-2", pending);
    assert.deepEqual(replaced, []);
    assert.equal(storage.size, 0);
  },
};

let failures = 0;
for (const [name, test] of Object.entries(tests)) {
  try {
    await test();
    console.log(`ok   ${name}`);
  } catch (error) {
    failures++;
    console.log(`FAIL ${name}\n     ${error.message}`);
  }
}
process.exit(failures ? 1 : 0);
