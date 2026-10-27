import { readFileSync } from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

const script = readFileSync(new URL("../docs/apercu.user.js", import.meta.url), "utf8");
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
