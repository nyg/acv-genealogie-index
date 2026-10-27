import { readFileSync } from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

const script = readFileSync(new URL("../scraper/davel_pdf.js", import.meta.url), "utf8");
const context = vm.createContext({ window: {}, Worker: class { postMessage() {} }, Blob: class {}, URL: { createObjectURL: () => "" }, TextDecoder });
vm.runInContext(script, context);
const { segment, unpredict } = context.window.pdf;

const pages = (from, to, w, h) => Array.from({ length: to - from + 1 }, (_, i) => ({ n: from + i, w, h }));
const strip = n => ({ n, w: 700, h: 115 });
const runs = infos => Array.from(segment(infos), s => (s.strip ? `bande ${s.from}` : `${s.from}-${s.to}`));

const tests = {
  "un répertoire séparé suit sa bande et change de format": () => assert.deepEqual(
    runs([strip(1), ...pages(2, 285, 727, 1082), strip(286), ...pages(287, 354, 830, 1140), ...pages(355, 452, 733, 1082)]),
    ["bande 1", "2-285", "bande 286", "287-354", "355-452"],
  ),
  "l'alternance recto/verso reste une seule partie": () => assert.deepEqual(
    runs([strip(1), ...pages(2, 40, 942, 1214), ...Array.from({ length: 23 }, (_, i) => ({ n: 41 + i, w: 950, h: i % 2 ? 1208 : 1268 })), ...pages(64, 120, 944, 1220)]),
    ["bande 1", "2-120"],
  ),
  "un feuillet inséré ne coupe pas la partie": () => assert.deepEqual(
    runs([strip(1), ...pages(2, 102, 930, 1201), { n: 103, w: 381, h: 337 }, ...pages(104, 200, 950, 1188)]),
    ["bande 1", "2-200"],
  ),
  "le prédicteur PNG Up des tables xref est décodé": () => assert.deepEqual(
    Array.from(unpredict(new Uint8Array([2, 1, 0, 5, 2, 0, 1, 3]), "/Predictor 12/Columns 3")),
    [1, 0, 5, 1, 1, 8],
    "lignes de 3 colonnes : la 2e s'ajoute à la 1re",
  ),
};

let failures = 0;
for (const [name, run] of Object.entries(tests)) {
  try {
    run();
    console.log(`ok   ${name}`);
  } catch (error) {
    failures++;
    console.log(`FAIL ${name}\n     ${error.message}`);
  }
}
process.exit(failures ? 1 : 0);
