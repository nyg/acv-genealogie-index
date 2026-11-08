import { readFileSync } from "node:fs";
import vm from "node:vm";

const SITE = new URL("../docs/index.html", import.meta.url);
const EXPORTS = [
  "DATA", "KINDS", "KIND_NAMES", "FONDS_ERA", "DIGITIZED_FONDS", "NEAR_YEARS", "state", "SUGGESTIONS", "placesById", "unitsBySlug",
  "normalize", "searchSuggestions", "describeTargets", "entryPlaceIds", "selectEntry", "parseQueryDate", "findRegisters", "contextNotes",
  "groupByUnit", "formatRange", "formatDate", "tidyAids", "partMatchesKind", "pdfTargets", "pageSpan", "render", "fullyConsultableYear", "gapCote",
];

const element = () => ({
  innerHTML: "", textContent: "", value: "", hidden: false, clientWidth: 900, dataset: {},
  classList: { toggle() {}, add() {}, remove() {} },
  setAttribute() {}, addEventListener() {}, dispatchEvent() {}, querySelector: () => null, querySelectorAll: () => [],
});

export function loadSite(path = SITE) {
  const html = readFileSync(path, "utf8");
  const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
  const elements = new Map();
  const documentElement = { dataset: {} };
  const context = vm.createContext({
    document: { getElementById: id => elements.get(id) ?? elements.set(id, element()).get(id), documentElement, addEventListener() {} },
    localStorage: { getItem: () => null, setItem() {} },
    matchMedia: () => ({ matches: true }),
    addEventListener() {},
    setTimeout, clearTimeout, Event: class {}, console, URLSearchParams, Intl,
  });
  vm.runInContext(`${script}\n;globalThis.__site = { ${EXPORTS.join(", ")} };`, context);
  return { site: context.__site, elements, documentElement };
}
