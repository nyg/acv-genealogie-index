import { readFileSync } from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

const script = readFileSync(new URL("../docs/apercu.user.js", import.meta.url), "utf8");
const pageMap = JSON.parse(readFileSync(new URL("../docs/pdf-pages.json", import.meta.url), "utf8"));
const { registerPageAt, locatePage } = vm.runInContext(`${readFileSync(new URL("../site/page_map.js", import.meta.url), "utf8")}\n;({ registerPageAt, locatePage })`, vm.createContext({}));
const HASH = "#apercu=&page=6&pdf=8%2Ff%2Fe%2FCH-ACV_RN-ED-15-1.pdf&titre=Ed+15%2F1";

const run = (href, storage = new Map()) => {
  const url = new URL(href);
  const replaced = [];
  const events = [];
  const dataset = {};
  vm.runInContext(script, vm.createContext({
    location: { hostname: url.hostname, pathname: url.pathname, search: url.search, hash: url.hash },
    document: { documentElement: { dataset }, readyState: "loading", addEventListener() {}, dispatchEvent: event => events.push(event.type) },
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
    test();
    console.log(`ok   ${name}`);
  } catch (error) {
    failures++;
    console.log(`FAIL ${name}\n     ${error.message}`);
  }
}
process.exit(failures ? 1 : 0);
