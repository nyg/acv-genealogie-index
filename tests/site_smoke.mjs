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
const context = vm.createContext({
  document: { getElementById: id => elements.get(id) ?? elements.set(id, element()).get(id) },
  localStorage: { getItem: () => null, setItem() {} },
  matchMedia: () => ({ matches: true }),
  addEventListener() {},
  setTimeout, clearTimeout, Event: class {}, console,
});
vm.runInContext(`${script}\n;globalThis.__site = { state, SUGGESTIONS, selectEntry, parseQueryDate, render, normalize };`, context);
const site = context.__site;

const search = (place, kind, date) => {
  site.selectEntry(site.SUGGESTIONS.find(entry => entry.key === site.normalize(place)));
  site.state.kind = kind;
  site.state.query = site.parseQueryDate(date);
  site.render();
  const answers = elements.get("answers").innerHTML;
  const summary = answers.match(/<p class="summary">([\s\S]*?)<\/p>/)[1].replace(/<[^>]+>/g, "");
  const cotes = [...answers.matchAll(/<span class="cote">([^<]+)<\/span>/g)].map(match => match[1]);
  return { summary, cotes };
};

const cases = [
  ["Huémoz", "naissance", "17.02.1889", "SB 267/49/1/1"],
  ["Chesières", "naissance", "14.09.1833", "Ed 68 bis/1"],
  ["Ollon", "mariage", "1890", "SB 268/73/1"],
  ["Ollon", "naissance", "1787", "Eb 92/3"],
  ["Aigle", "deces", "1959", "SB 267/2/3/12"],
  ["Bex", "mariage", "1888", "SB 267/12/2/2"],
  ["Leysin", "naissance", "1880", "SB 269/59/1/1"],
];
let failures = 0;
for (const [place, kind, date, expected] of cases) {
  const { summary, cotes } = search(place, kind, date);
  const ok = cotes.includes(expected);
  failures += ok ? 0 : 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${place} / ${kind} / ${date} → attendu ${expected}\n     ${summary}\n     ${cotes.join(", ")}`);
}
process.exit(failures ? 1 : 0);
