const ROMAN = [[1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"], [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
const toRoman = number => ROMAN.reduce(([text, rest], [value, letters]) => [text + letters.repeat(Math.floor(rest / value)), rest % value], ["", number])[0];
function fromRoman(text) {
  const values = [...text.toUpperCase()].map(letter => ROMAN.find(([, letters]) => letters === letter)[0]);
  return values.reduce((sum, value, index) => sum + (value < (values[index + 1] ?? 0) ? -value : value), 0);
}

const pageSpan = ([first, last], roman = false) => {
  const [a, b] = roman ? [toRoman(first), toRoman(last)] : [first, last];
  return first === last ? `${a}` : `${a}–${b}`;
};

const within = (value, a, b) => value >= Math.min(a, b) && value <= Math.max(a, b);

function locatePage(part, page) {
  if (part.pdf[0] === part.pdf[1]) return { pdf: part.pdf[0], approx: false };
  const points = [[part.pages[0], part.pdf[0]], ...part.anchors, [part.pages[1], part.pdf[1]]];
  const exact = points.find(([known]) => known === page);
  if (exact || !(part.anchors.length || part.spread)) return { pdf: exact ? exact[1] : part.pdf[0] + Math.abs(page - part.pages[0]), approx: false };
  const next = points.findIndex(([known], index) => index > 0 && within(page, points[index - 1][0], known));
  const [[fromPage, fromPdf], [toPage, toPdf]] = [points[next - 1], points[next]];
  return { pdf: Math.round(fromPdf + (page - fromPage) * (toPdf - fromPdf) / (toPage - fromPage)), approx: true };
}

function pdfTargets(unit, text) {
  const value = text.trim();
  const roman = /^[ivxlcdm]+$/i.test(value);
  if (!roman && !/^\d+$/.test(value)) return null;
  const page = roman ? fromRoman(value) : +value;
  return (unit.pdfParts ?? [])
    .filter(part => part.pages && within(page, ...part.pages) && (!roman || part.roman))
    .map(part => ({ part, ...locatePage(part, page) }));
}

function registerPageAt(part, pdf) {
  if (!part.pages || !within(pdf, ...part.pdf)) return null;
  const points = [[part.pages[0], part.pdf[0]], ...part.anchors, [part.pages[1], part.pdf[1]]];
  const exact = points.find(([, known]) => known === pdf);
  if (exact) return { page: exact[0], approx: false };
  if (!(part.anchors.length || part.spread)) return { page: part.pages[0] + Math.sign(part.pages[1] - part.pages[0]) * (pdf - part.pdf[0]), approx: false };
  const next = points.findIndex(([, known], index) => index > 0 && within(pdf, points[index - 1][1], known));
  const [[fromPage, fromPdf], [toPage, toPdf]] = [points[next - 1], points[next]];
  return { page: Math.round(fromPage + (pdf - fromPdf) * (toPage - fromPage) / (toPdf - fromPdf)), approx: true };
}
