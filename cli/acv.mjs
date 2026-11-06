#!/usr/bin/env node
import { parseArgs } from "node:util";
import { loadSite } from "./site.mjs";

const USAGE = `Usage :
  node cli/acv.mjs chercher <lieu> <acte> [date] [--page <page du registre>] [--json]
  node cli/acv.mjs page <cote> <page du registre> [--json]
  node cli/acv.mjs lieux <texte> [--json]

Actes : naissance (baptême), mariage, deces, catechumenes, autre (reconnaissance, légitimation), tous.
Dates : 1789, 03.1789, 1789-03, 12.03.1789, 1789-03-12.`;

const KIND_ALIASES = {
  bapteme: "naissance", bapt: "naissance", deces: "deces", sepulture: "deces", inhumation: "deces", mort: "deces",
  annonce: "mariage", promesse: "mariage", catechumene: "catechumenes", reconnaissance: "autre", legitimation: "autre",
};

class UsageError extends Error {}

const { site } = loadSite();

function resolvePlace(text) {
  const entry = site.SUGGESTIONS.find(candidate => candidate.key === site.normalize(text));
  if (entry) return entry;
  const suggestions = site.searchSuggestions(text).map(candidate => `${candidate.name} (${site.describeTargets(candidate)})`);
  throw new UsageError(`Lieu inconnu : « ${text} ».${suggestions.length ? ` Lieux proches : ${suggestions.join(" ; ")}.` : ""}`);
}

function resolveKind(text) {
  const key = site.normalize(text);
  const kind = site.KINDS.find(candidate => candidate.id === key)?.id ?? KIND_ALIASES[key];
  if (!kind) throw new UsageError(`Acte inconnu : « ${text} ». Actes : ${site.KINDS.map(candidate => candidate.id).join(", ")}.`);
  return kind;
}

function resolveDate(text) {
  const query = text ? site.parseQueryDate(text) : null;
  if (query?.error) throw new UsageError(query.error);
  return query;
}

function resolveUnit(cote) {
  const wanted = site.normalize(cote);
  const unit = site.DATA.units.find(candidate => site.normalize(candidate.cote) === wanted);
  if (!unit) throw new UsageError(`Cote inconnue : « ${cote} ».`);
  return unit;
}

const pdfUrl = (unit, page) => unit.pdf ? `${site.DATA.pdfBase}${unit.pdf}${page ? `#page=${page}` : ""}` : null;

function pageTargets(unit, page, kind) {
  const targets = site.pdfTargets(unit, String(page));
  if (!targets) throw new UsageError(`Page du registre invalide : « ${page} ».`);
  return targets
    .sort((a, b) => site.partMatchesKind(b.part, kind) - site.partMatchesKind(a.part, kind))
    .map(({ part, pdf, approx }) => ({ pdf, approx, content: part.content, url: pdfUrl(unit, pdf) }));
}

function describeUnit(unit, segments, kind, page) {
  return {
    cote: unit.cote,
    fonds: unit.fonds,
    era: site.FONDS_ERA[unit.fonds] ?? unit.fonds,
    dates: unit.dates,
    url: unit.url,
    pdf: pdfUrl(unit),
    pdfSize: unit.pdfSize?.replace("MiB", "Mo") ?? null,
    availability: unit.pdf ? null : site.DIGITIZED_FONDS.has(unit.fonds)
      ? "Pas de PDF en ligne (délai de protection ou pas encore numérisé) : consultable aux ACV."
      : "Non numérisé : à consulter en salle de lecture ou à demander aux ACV.",
    segments: segments.map(segment => ({
      label: segment.label, start: segment.start, end: segment.end, range: site.formatRange(segment), pages: segment.pages || null,
      headToTail: Boolean(segment.tb), foreign: Boolean(segment.foreign), section: segment.section || null,
    })),
    repertoire: unit.aids ? site.tidyAids(unit.aids, kind) : [],
    pdfParts: (unit.pdfParts ?? []).map(part => ({
      pdf: part.pdf, content: part.content, pages: part.pages ? site.pageSpan(part.pages, part.roman) : null,
      relevant: site.partMatchesKind(part, kind), note: part.note || null, url: pdfUrl(unit, part.pdf[0]),
    })),
    pageRequested: page !== undefined,
    page: page !== undefined && unit.pdfParts ? pageTargets(unit, page, kind) : null,
    note: unit.note || null,
  };
}

const describeGroups = (segments, kind, page) => site.groupByUnit(segments).map(({ unit, segments: unitSegments }) => describeUnit(unit, unitSegments, kind, page));

function search(placeText, kindText, dateText, page) {
  const entry = resolvePlace(placeText);
  const kind = resolveKind(kindText);
  const query = resolveDate(dateText);
  const placeIds = site.entryPlaceIds(entry);
  const { registers, justificatives, near } = site.findRegisters(placeIds, entry.since, kind, query);
  const { pending, notes } = site.contextNotes(placeIds, kind, query);
  return {
    place: {
      name: entry.name,
      places: placeIds.map(id => ({ id, name: site.placesById.get(id).name, kind: site.placesById.get(id).kind, via: entry.targets.get(id) || null })),
    },
    kind: { id: kind, label: site.KINDS.find(candidate => candidate.id === kind).label },
    date: query && { start: query.start, end: query.end, label: query.label },
    registers: describeGroups(registers, kind, page),
    justificatives: describeGroups(justificatives, kind, page),
    near: describeGroups(near, kind, page),
    nearYears: site.NEAR_YEARS,
    pending: pending.map(series => ({ cote: series.cote, dates: series.dates, url: series.url })),
    notes,
  };
}

function lookupPage(cote, page) {
  const unit = resolveUnit(cote);
  if (!unit.pdfParts) throw new UsageError(`${unit.cote} : les pages de ce registre ne sont pas encore reliées au PDF.`);
  return { cote: unit.cote, page: String(page), targets: pageTargets(unit, page, "tous"), known: unit.pdfParts.filter(part => part.pages).map(part => site.pageSpan(part.pages, part.roman)) };
}

function places(text) {
  return site.searchSuggestions(text).map(entry => ({ name: entry.name, places: site.describeTargets(entry) }));
}

const pdfLine = target => `${target.approx ? "≈ " : ""}PDF p. ${target.pdf} ${target.content} ${target.url}`;

function formatUnit(unit) {
  const lines = [`${unit.cote} · ${unit.era} · ${unit.dates}`];
  for (const segment of unit.segments) {
    const extras = [segment.pages, segment.headToTail && "tête-bêche", segment.foreign && "forains / célébrés ailleurs", segment.section].filter(Boolean);
    lines.push(`  ${segment.label} ${segment.range}${extras.length ? ` (${extras.join(", ")})` : ""}`);
  }
  unit.repertoire.forEach(line => lines.push(`  Répertoire : ${line}`));
  if (unit.pdfParts.length) {
    lines.push("  Dans le PDF :");
    unit.pdfParts.forEach(part => lines.push(`  ${part.relevant ? "→" : " "} p. ${site.pageSpan(part.pdf)} ${part.content}${part.pages ? ` (registre p. ${part.pages})` : ""}${part.note ? ` : ${part.note}` : ""}`));
  }
  if (unit.page) lines.push(unit.page.length ? unit.page.map(target => `  Page demandée : ${pdfLine(target)}`).join("\n") : "  Page demandée : pas dans les pages connues.");
  if (unit.page === null && unit.pageRequested) lines.push(`  Page demandée : ${unit.pdf ? "les pages de ce registre ne sont pas encore reliées au PDF." : "pas de PDF en ligne."}`);
  if (unit.note) lines.push(`  Remarque : ${unit.note.replace(/\n/g, " ")}`);
  lines.push(unit.pdf ? `  PDF${unit.pdfSize ? ` (${unit.pdfSize})` : ""} : ${unit.pdf}` : `  ${unit.availability}`);
  lines.push(`  Fiche : ${unit.url}`);
  return lines.join("\n");
}

function formatSearch(result) {
  const kind = result.kind.label.toLowerCase();
  const count = result.registers.length;
  const where = result.place.places.filter(place => place.via).map(place => `${place.name} (${place.via})`);
  const head = result.date
    ? `${count ? `${count === 1 ? "Un registre couvre" : `${count} registres couvrent`}` : "Aucun registre indexé ne couvre"} ${kind} ${result.date.label} pour ${result.place.name}.`
    : `${count} registres pour ${kind} à ${result.place.name}.`;
  const blocks = [head + (where.length ? `\nRattaché à : ${where.join(" ; ")}` : "")];
  if (result.pending.length) blocks.push(`Pas encore indexé : ${result.pending.map(series => `${series.cote} (${series.dates})`).join(", ")}.`);
  result.notes.forEach(note => blocks.push(note));
  result.registers.forEach(unit => blocks.push(formatUnit(unit)));
  if (result.justificatives.length) blocks.push(`Pièces justificatives (non numérisées, à demander aux ACV) :\n${result.justificatives.map(unit => `  ${unit.cote} · ${unit.dates} · ${unit.url}`).join("\n")}`);
  if (result.near.length) blocks.push(`Registres voisins (± ${result.nearYears} ans) :\n${result.near.map(unit => `  ${unit.cote} · ${unit.dates}`).join("\n")}`);
  return blocks.join("\n\n");
}

function formatPage(result) {
  if (!result.targets.length) return `${result.cote} p. ${result.page} : pas dans les pages connues (${result.known.join(", ")}).`;
  return result.targets.map(target => `${result.cote} p. ${result.page} → ${pdfLine(target)}`).join("\n");
}

const formatPlaces = list => list.length ? list.map(entry => `${entry.name} : ${entry.places}`).join("\n") : "Aucun lieu trouvé.";

function run(argv) {
  const { values, positionals } = parseArgs({ args: argv, allowPositionals: true, options: { json: { type: "boolean" }, page: { type: "string" }, help: { type: "boolean", short: "h" } } });
  const [command, ...args] = positionals;
  if (values.help || !command) return { text: USAGE };
  const commands = {
    chercher: { arity: [2, 3], run: () => search(args[0], args[1], args[2], values.page), format: formatSearch },
    page: { arity: [2, 2], run: () => lookupPage(args[0], args[1]), format: formatPage },
    lieux: { arity: [1, 1], run: () => places(args[0]), format: formatPlaces },
  };
  const chosen = commands[command];
  if (!chosen || args.length < chosen.arity[0] || args.length > chosen.arity[1]) throw new UsageError(USAGE);
  const result = chosen.run();
  return { text: values.json ? JSON.stringify(result, null, 2) : chosen.format(result) };
}

try {
  console.log(run(process.argv.slice(2)).text);
} catch (error) {
  if (!(error instanceof UsageError) && error.code !== "ERR_PARSE_ARGS_UNKNOWN_OPTION") throw error;
  console.error(error.message);
  process.exit(2);
}
