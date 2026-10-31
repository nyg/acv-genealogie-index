import { readFileSync } from "node:fs";
import vm from "node:vm";

const html = readFileSync(new URL("../docs/index.html", import.meta.url), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];

const element = () => ({
  innerHTML: "", textContent: "", value: "", hidden: false, clientWidth: 900, dataset: {},
  classList: { toggle() {}, add() {}, remove() {} },
  setAttribute() {}, addEventListener() {}, dispatchEvent() {}, querySelector: () => null, querySelectorAll: () => [],
});
const elements = new Map();
const documentElement = { dataset: {} };
const context = vm.createContext({
  document: { getElementById: id => elements.get(id) ?? elements.set(id, element()).get(id), documentElement, addEventListener() {} },
  localStorage: { getItem: () => null, setItem() {} },
  matchMedia: () => ({ matches: true }),
  addEventListener() {},
  setTimeout, clearTimeout, Event: class {}, console, URLSearchParams,
});
vm.runInContext(`${script}\n;globalThis.__site = { state, SUGGESTIONS, selectEntry, parseQueryDate, render, normalize, unitsBySlug, pdfTargets };`, context);
const site = context.__site;

const search = (place, kind, date) => {
  site.selectEntry(site.SUGGESTIONS.find(entry => entry.key === site.normalize(place)));
  site.state.kind = kind;
  site.state.query = site.parseQueryDate(date);
  site.render();
  const answers = elements.get("answers").innerHTML;
  const summary = answers.match(/<p class="summary">([\s\S]*?)<\/p>/)[1].replace(/<[^>]+>/g, "");
  const cotes = [...answers.matchAll(/<span class="cote">([^<]+)<\/span>/g)].map(match => match[1]);
  return { summary, cotes, answers };
};

const cases = [
  ["Huémoz", "naissance", "17.02.1889", "SB 267/49/1/1"],
  ["Chesières", "naissance", "14.09.1833", "Ed 68 bis/1"],
  ["Ollon", "mariage", "1890", "SB 268/73/1"],
  ["Ollon", "naissance", "1787", "Eb 92/3"],
  ["Aigle", "deces", "1959", "SB 267/2/3/12"],
  ["Bex", "mariage", "1888", "SB 267/12/2/2"],
  ["Leysin", "naissance", "1880", "SB 269/59/1/1"],
  ["Château d'Oex", "naissance", "1850", "Ed 23/2"],
  ["Château d'Oex", "mariage", "1900", "SB 267/20/2/2"],
  ["Château d'Oex", "mariage", "1954", "SB 115/1225"],
  ["L'Étivaz", "mariage", "1900", "SB 268/58/2"],
  ["L'Étivaz", "naissance", "1790", "Eb 54/2"],
  ["L'Étivaz", "deces", "1895", "SB 267/58/3/1"],
  ["L'Étivaz", "naissance", "1910", "SB 267/20/1/6"],
  ["Ormont-Dessous", "naissance", "1880", "SB 269/75/1/1"],
  ["Ormont-Dessous", "mariage", "1867", "Ec 96/1"],
  ["Ormont-Dessous", "deces", "1907", "SB 23/1253"],
  ["Ormont-Dessus", "mariage", "1900", "SB 268/76/2"],
  ["Ormont-Dessus", "deces", "1920", "SB 115/128"],
  ["Rougemont", "deces", "1950", "SB 267/88/3/3"],
  ["Rougemont", "mariage", "1885", "SB 23/996"],
  ["Rougemont", "mariage", "1954", "SB 115/1226"],
  ["Lutry", "naissance", "1900", "SB 267/65/1/3"],
  ["Lutry", "mariage", "1890", "SB 268/65/4"],
  ["Lutry", "mariage", "1999", "SB 268/65/31"],
  ["Lutry", "naissance", "1850", "Ec 78/6"],
  ["Lutry", "naissance", "1920", "SB 115/307"],
  ["Cully", "autre", "1950", "SB 267/33/5/1"],
  ["Savigny", "deces", "1880", "SB 23/602"],
  ["Cheseaux-sur-Lausanne", "naissance", "1850", "Ed 25/2"],
  ["Cheseaux-sur-Lausanne", "mariage", "1830", "Ec 25/1"],
  ["Cheseaux-sur-Lausanne", "naissance", "1900", "SB 267/86/1/7"],
  ["Romanel-sur-Lausanne", "deces", "1913", "SB 115/258"],
  ["Romanel-sur-Lausanne", "mariage", "1879", "SB 23/486"],
  ["Prilly", "naissance", "1960", "SB 267/86/1/19"],
  ["Sullens", "deces", "1890", "SB 23/202"],
  ["Bournens", "deces", "1920", "SB 269/96/3/3"],
  ["Bournens", "naissance", "1840", "Ed 105/1"],
  ["Bournens", "deces", "1860", "Ed 139/4"],
  ["Boussens", "mariage", "1840", "Ed 105/3"],
  ["Sullens", "naissance", "1860", "Ed 139/1"],
  ["Romanel-sur-Lausanne", "naissance", "1790", "Eb 80/2"],
  ["Romanel-sur-Lausanne", "mariage", "1847", "Ed 110/5"],
  ["Cheseaux-sur-Lausanne", "deces", "1847", "Ed 87/5"],
  ["Le Mont-sur-Lausanne", "mariage", "1750", "Eb 80/1"],
  ["Le Mont-sur-Lausanne", "naissance", "1800", "Ec 80/3"],
  ["Morrens", "mariage", "1850", "Ec 87/2"],
  ["Vufflens-la-Ville", "mariage", "1820", "Eb 139/2"],
];
let failures = 0;
for (const [place, kind, date, expected] of cases) {
  const { summary, cotes } = search(place, kind, date);
  const ok = cotes.includes(expected);
  failures += ok ? 0 : 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${place} / ${kind} / ${date} → attendu ${expected}\n     ${summary}\n     ${cotes.join(", ")}`);
}

const pdfCases = [
  ["eb-92-2", "466", ["544"]],
  ["eb-92-2", "400", ["535", "610"]],
  ["eb-92-4", "179", ["139"]],
  ["eb-92-7", "355", ["6"]],
  ["eb-92-1", "166", ["171", "172"]],
  ["eb-92-1", "330", ["432"]],
  ["ed-92-7", "195", ["200"]],
  ["ed-92-7", "999", []],
  ["ed-92-1", "192", ["230"]],
  ["ed-92-1", "150", ["≈180"]],
  ["eb-15-1", "75", ["80", "403"]],
  ["eb-15-1", "340", ["401"]],
  ["eb-15-3", "44", ["109", "110", "480"]],
  ["eb-15-3", "xlvii", ["483"]],
  ["ed-15-2", "177", ["100"]],
  ["ed-15-2", "3", ["≈6"]],
  ["eb-3-1", "10", ["≈29", "225"]],
  ["ed-3-2", "367", ["213"]],
  ["ed-3-13", "444", ["441"]],
  ["ed-3-13", "440", []],
  ["eb-10-1", "220", ["229"]],
  ["eb-10-1", "214", ["223", "225"]],
  ["eb-23-8", "196", ["≈143"]],
  ["eb-23-8", "281", ["100"]],
  ["eb-54-2", "326", ["24"]],
  ["ed-54-3", "30", ["71", "73"]],
];
for (const [slug, page, expected] of pdfCases) {
  const pdfPages = site.pdfTargets(site.unitsBySlug.get(slug), page).map(target => `${target.approx ? "≈" : ""}${target.pdf}`);
  const ok = JSON.stringify(pdfPages) === JSON.stringify(expected);
  failures += ok ? 0 : 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${slug} p. ${page} → attendu PDF ${expected.join(", ") || "aucune"}, obtenu ${pdfPages.join(", ") || "aucune"}`);
}

const { answers } = search("Ollon", "deces", "1760");
const repertoireLink = /CH-ACV_RN-EB-92-4\.pdf#page=382"[^>]*>PDF p\. 382–441<\/a>\s*<div><span class="part-content">Répertoire des décès/;
const linked = repertoireLink.test(answers);
failures += linked ? 0 : 1;
console.log(`${linked ? "ok  " : "FAIL"} Ollon / deces / 1760 → lien vers le répertoire des décès d'Eb 92/4 (PDF p. 382)`);

documentElement.dataset.acvApercu = "";
const { answers: viewerAnswers } = search("Ollon", "deces", "1760");
delete documentElement.dataset.acvApercu;
const viewerLink = /href="https:\/\/davel-vd\.ch\/eb-92-4#apercu=&amp;page=382&amp;pdf=[^"]*CH-ACV_RN-EB-92-4\.pdf&amp;titre=Eb\+92%2F4"[^>]*>PDF p\. 382–441<\/a>/.test(viewerAnswers);
failures += viewerLink ? 0 : 1;
console.log(`${viewerLink ? "ok  " : "FAIL"} Ollon / deces / 1760, aperçu installé → le lien PDF p. 382 ouvre l'aperçu sur la fiche d'Eb 92/4`);

const placeholderHidden = !search("Prilly", "mariage", "1850").cotes.some(cote => cote.includes("FANTOME"));
failures += placeholderHidden ? 0 : 1;
console.log(`${placeholderHidden ? "ok  " : "FAIL"} Prilly / mariage / 1850 → pas de fiche FANTOME parmi les registres`);

const coveragePanel = elements.get("coverage-panel").innerHTML;
const covered = coveragePanel.includes(`data-place="paroisse-15">Bex</button>`) && /Pages du PDF<\/strong> : pour [^(]*Ollon \(\d+ registres\)/.test(coveragePanel);
failures += covered ? 0 : 1;
console.log(`${covered ? "ok  " : "FAIL"} couverture → Bex parmi les paroisses indexées, Ollon parmi les pages du PDF reliées`);

process.exit(failures ? 1 : 0);
