import { readFileSync } from "node:fs";
import { loadSite } from "../cli/site.mjs";

const { site, elements, documentElement } = loadSite();

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
  ["Ballaigues", "naissance", "1890", "SB 267/7/1/1"],
  ["Ballaigues", "naissance", "1800", "Ec 10/1"],
  ["Ballaigues", "mariage", "1925", "SB 268/7/3"],
  ["Ballaigues", "mariage", "1955", "SB 267/99/2/8"],
  ["Lignerolle", "mariage", "1840", "Ec 74/1"],
  ["Lignerolle", "deces", "1886", "SB 23/844"],
  ["Lignerolle", "deces", "1906", "SB 23/2016"],
  ["Lignerolle", "deces", "1908", "SB 23/2017"],
  ["Lignerolle", "deces", "1916", "SB 115/427"],
  ["Les Clées", "naissance", "1890", "SB 267/85/1/2"],
  ["Les Clées", "deces", "1950", "SB 267/60/3/3"],
  ["Romainmôtier", "deces", "1877", "SB 23/846"],
  ["Vallorbe", "mariage", "1907", "SB 23/2046"],
  ["Ollon", "mariage", "15.10.1957", "SB 268/73/10"],
  ["Ollon", "mariage", "10.1957", "SB 268/73/11"],
  ["Chessières", "naissance", "1932", "SB 267/49/1/4"],
  ["Chessières", "naissance", "1850", "Ed 68 bis/1"],
  ["Ollon", "mariage", "1960", "SB 324/1/15"],
  ["Aigle", "mariage", "1956", "SB 324/1/1"],
  ["Cully", "mariage", "1960", "SB 324/1/84"],
  ["Lausanne", "naissance", "1962", "SB 324/4/58"],
  ["Lausanne", "deces", "1995", "SB 267/53/3/205"],
  ["Lausanne", "naissance", "1590", "Eb 71/2"],
  ["Lausanne", "mariage", "1960", "SB 268/53/73"],
  ["Lausanne", "naissance", "1880", "SB 269/53/1/1"],
  ["Aubonne", "naissance", "1800", "Eb 8/10"],
  ["Aubonne", "mariage", "1952", "SB 115/1115"],
  ["Aubonne", "deces", "1850", "Ed 8/10"],
  ["Lausanne", "mariage", "1876", "SB 23/342"],
  ["Lausanne", "mariage", "1890", "SB 23/407"],
  ["Lausanne", "mariage", "1923", "SB 115/48"],
  ["Lausanne", "naissance", "1850", "Ec 71/193"],
  ["Bussigny-près-Lausanne", "naissance", "1880", "SB 267/17/1/1"],
  ["Bussigny-près-Lausanne", "deces", "1900", "SB 269/17/3/2"],
  ["Bussigny-près-Lausanne", "mariage", "1890", "SB 268/17/2"],
  ["Bussigny-près-Lausanne", "mariage", "1886", "SB 23/635"],
  ["Bussigny-près-Lausanne", "mariage", "1935", "SB 115/915"],
  ["Bussigny-près-Lausanne", "mariage", "1952", "SB 115/1194"],
  ["Bussigny-près-Lausanne", "deces", "1950", "SB 115/916"],
  ["Villars-Sainte-Croix", "deces", "1890", "SB 23/636"],
  ["Arzier", "naissance", "1787", "Eb 5/1"],
  ["Arzier", "deces", "1787", "Eb 5/1"],
  ["Arzier", "deces", "1837", "Ed 5/4"],
  ["Arzier", "mariage", "1880", "SB 269/4/2/1"],
  ["Arzier", "deces", "1888", "SB 23/761"],
  ["Arzier", "naissance", "1850", "Ec 5/1"],
  ["Arzier", "naissance", "1847", "Ed 58/1"],
  ["Arzier", "deces", "1950", "SB 267/10/3/7"],
  ["Genolier", "naissance", "1840", "Ed 58/1"],
  ["Begnins", "naissance", "1800", "Eb 12/4"],
  ["Begnins", "mariage", "1850", "Ed 12/3"],
  ["Begnins", "deces", "1890", "SB 23/772"],
  ["La Sarraz", "naissance", "1719", "Eb 70/2"],
  ["La Sarraz", "naissance", "1719", "Eb 70/3"],
  ["La Sarraz", "deces", "1764", "Eb 70/5"],
  ["La Sarraz", "deces", "1788", "Eb 70/5"],
  ["La Sarraz", "naissance", "1865", "Ed 70/3"],
  ["La Sarraz", "naissance", "1840", "Ec 70/5"],
  ["La Sarraz", "mariage", "1887", "SB 267/50/2/1"],
  ["La Sarraz", "mariage", "1887", "SB 268/50/2"],
  ["La Sarraz", "naissance", "1910", "SB 269/50/1/2"],
  ["La Sarraz", "deces", "1893", "SB 23/173"],
  ["La Sarraz", "naissance", "1922", "SB 115/181"],
  ["La Sarraz", "deces", "1950", "SB 267/50/3/14"],
  ["Éclépens", "naissance", "1800", "Eb 70/7"],
  ["Bullet", "naissance", "1750", "Eb 19/1"],
  ["Bullet", "mariage", "1763", "Eb 19/4"],
  ["Bullet", "deces", "1850", "Ed 19/4"],
  ["Bullet", "naissance", "1850", "Ec 19/2"],
  ["Bullet", "naissance", "1882", "SB 23/281"],
  ["Bullet", "mariage", "1900", "SB 268/16/1"],
  ["Bullet", "mariage", "1940", "SB 115/687"],
  ["Bullet", "mariage", "1953", "SB 115/1135"],
  ["Sainte-Croix", "naissance", "1739", "Eb 121/2"],
  ["Corbeyrier", "deces", "1850", "Ed 3/9"],
  ["Ballaigues", "naissance", "1847", "Ed 74/1"],
  ["Oron-la-Ville", "naissance", "1750", "Eb 97/2"],
  ["Oron-la-Ville", "naissance", "1850", "Ed 97/2"],
  ["Oron-la-Ville", "mariage", "1850", "Ec 97/2"],
  ["Oron-la-Ville", "deces", "25.06.1896", "SB 267/77/3/1/1"],
  ["Oron-la-Ville", "deces", "25.06.1896", "SB 23/2062"],
  ["Oron-la-Ville", "mariage", "1898", "SB 23/2065"],
  ["Oron-la-Ville", "mariage", "1900", "SB 267/77/2/2"],
  ["Oron-la-Ville", "mariage", "1900", "SB 268/77/6"],
  ["Oron-la-Ville", "naissance", "1900", "SB 269/77/1/4"],
  ["Oron-la-Ville", "mariage", "1920", "SB 115/448"],
  ["Oron-la-Ville", "mariage", "1953", "SB 115/1217"],
  ["Pully", "naissance", "1600", "Eb 112/1"],
  ["Pully", "naissance", "1750", "Eb 112/4"],
  ["Pully", "deces", "1800", "Eb 112/6"],
  ["Pully", "mariage", "1820", "Eb 112/7"],
  ["Pully", "mariage", "07.02.1828", "Ed 112/4"],
  ["Pully", "mariage", "07.02.1828", "Ec 112/1"],
  ["Pully", "mariage", "1828", "Ed 112/8"],
  ["Pully", "naissance", "1867", "Ec 112/5"],
  ["Pully", "naissance", "1868", "Ed 112/2"],
  ["Pully", "mariage", "15.12.1814", "Eb 112/6"],
  ["Pully", "deces", "1870", "Ed 112/7"],
  ["Paudex", "naissance", "1750", "Eb 112/4"],
  ["Belmont-sur-Lausanne", "naissance", "1600", "Eb 112/1"],
  ["Belmont-sur-Lausanne", "naissance", "1780", "Eb 13/1"],
  ["Belmont-sur-Lausanne", "deces", "1790", "Eb 13/2"],
  ["Belmont-sur-Lausanne", "naissance", "1825", "Eb 13/3"],
  ["Belmont-sur-Lausanne", "mariage", "1850", "Ed 13/2"],
  ["Belmont-sur-Lausanne", "mariage", "1830", "Ec 13/2"],
  ["La Tour-de-Peilz", "naissance", "1750", "Eb 129/2"],
  ["La Tour-de-Peilz", "deces", "1750", "Eb 129/5"],
  ["La Tour-de-Peilz", "deces", "1815", "Eb 129/6"],
  ["La Tour-de-Peilz", "mariage", "1850", "Ed 129/4"],
  ["La Tour-de-Peilz", "naissance", "1840", "Ec 129/10"],
  ["La Tour-de-Peilz", "mariage", "1890", "SB 268/51/1"],
  ["La Tour-de-Peilz", "deces", "1900", "SB 269/51/3/1"],
  ["La Tour-de-Peilz", "naissance", "1895", "SB 23/2416"],
  ["La Tour-de-Peilz", "mariage", "1920", "SB 115/576"],
  ["La Tour-de-Peilz", "mariage", "1952", "SB 115/1240"],
  ["La Tour-de-Peilz", "deces", "24.01.1955", "SB 267/51/3/6"],
  ["La Tour-de-Peilz", "deces", "1964", "SB 324/1/79"],
  ["Roche", "mariage", "23.09.1859", "Ed 136/4"],
  ["Roche", "mariage", "1859", "Ec 136/3"],
  ["Roche", "naissance", "1790", "Eb 90/5"],
  ["Roche", "mariage", "1800", "Eb 90/6"],
  ["Roche", "naissance", "1830", "Ed 114 bis/1"],
  ["Roche", "naissance", "1840", "Ed 143/1"],
  ["Roche", "deces", "1850", "Ed 136/5"],
  ["Roche", "deces", "1900", "SB 267/104/3/3"],
  ["Villeneuve", "naissance", "1750", "Eb 136/3"],
  ["Villeneuve", "deces", "1750", "Eb 136/4"],
  ["Villeneuve", "deces", "1795", "Eb 136/5"],
  ["Villeneuve", "naissance", "1900", "SB 267/104/1/4"],
  ["Villeneuve", "mariage", "1900", "SB 23/1265"],
  ["Villeneuve", "naissance", "1910", "SB 269/104/1/2"],
  ["Villeneuve", "mariage", "1940", "SB 115/637"],
  ["Villeneuve", "mariage", "1952", "SB 115/1114"],
  ["Villeneuve", "mariage", "1990", "SB 268/104/3"],
  ["Noville", "naissance", "1700", "Eb 90/2"],
  ["Chessel", "naissance", "1800", "Eb 90/5"],
  ["Yvorne", "mariage", "1850", "Ed 143/2"],
  ["Vevey", "naissance", "08.05.1807", "Eb 132/7"],
  ["Vevey", "mariage", "27.07.1804", "Eb 132/8"],
  ["Vevey", "mariage", "27.07.1804", "Eb 132/12"],
  ["Vevey", "naissance", "1750", "Eb 132/14"],
  ["Vevey", "deces", "1750", "Eb 132/9"],
  ["Vevey", "naissance", "1850", "Ed 132/4"],
  ["Vevey", "mariage", "1850", "Ed 132/10"],
  ["Vevey", "deces", "1850", "Ed 132/17"],
  ["Vevey", "naissance", "1850", "Ec 132/19"],
  ["Vevey", "naissance", "1900", "SB 267/101/1/8"],
  ["Vevey", "mariage", "1900", "SB 268/101/7"],
  ["Vevey", "deces", "1900", "SB 267/101/3/6"],
  ["Vevey", "naissance", "1900", "SB 269/101/1/2"],
  ["Vevey", "mariage", "1890", "SB 23/1050"],
  ["Vevey", "mariage", "1907", "SB 23/2319"],
  ["Vevey", "mariage", "1910", "SB 115/513"],
  ["Vevey", "mariage", "1940", "SB 115/1038"],
  ["Vevey", "mariage", "1953", "SB 115/1231"],
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
  ["eb-68-2", "278", ["≈80"]],
  ["eb-68-3", "1", ["4", "6"]],
  ["ed-68-4", "30", ["35", "47"]],
  ["ed-68-bis-5", "86", []],
  ["ed-68-bis-5", "103", ["109", "111"]],
  ["eb-118-1", "21", ["≈51", "≈530"]],
  ["eb-118-1", "xv", ["≈518"]],
  ["eb-118-2", "cxi", ["423"]],
  ["ed-118-4", "165", ["≈187", "200"]],
  ["sb-267-2-1-2", "250", ["≈253"]],
  ["sb-267-2-1-2", "401", []],
  ["sb-267-12-2-1", "45", ["48", "49"]],
  ["sb-267-20-1-1", "351", ["358"]],
  ["sb-267-86-2-8", "300", ["304"]],
  ["eb-5-1-2", "318", ["213"]],
  ["ed-5-4", "44", ["88", "90"]],
  ["ed-5-5", "115", ["120"]],
  ["ed-58-2", "29", ["36", "37"]],
  ["eb-12-4", "222", ["235"]],
  ["eb-12-5", "177", ["300"]],
  ["eb-12-5", "200", ["≈324"]],
  ["ed-12-2", "26", ["35", "37"]],
  ["eb-70-2", "15", ["24", "275"]],
  ["eb-70-5", "74", ["79"]],
  ["eb-70-1", "189", ["181"]],
  ["eb-70-4", "175", ["184", "185"]],
  ["ed-70-9", "36", ["43", "44"]],
  ["ed-70-8", "146", []],
  ["ed-70-3", "41", ["52"]],
  ["ed-70-6", "141", ["200"]],
  ["ed-70-6", "372", ["476"]],
  ["ed-136-4", "68", ["73"]],
  ["eb-136-1", "21", ["30", "155"]],
  ["eb-136-6", "90", ["99", "382", "383"]],
  ["ed-136-5", "300", ["323"]],
  ["eb-90-2", "305", ["312"]],
  ["eb-90-4", "247", ["30"]],
  ["ed-90-2", "300", ["326"]],
  ["ed-114-bis-4", "30", ["35"]],
  ["ed-136-1", "100", ["134"]],
  ["ed-136-3", "2", ["12", "16"]],
  ["ed-136-3", "137", ["197"]],
  ["ed-114-bis-1", "71", ["120", "122"]],
  ["ed-114-bis-3", "34", ["68", "70"]],
  ["ed-143-1", "72", ["87"]],
  ["ed-143-2", "100", ["105"]],
  ["ed-143-4", "188", ["195"]],
  ["ed-112-4", "65", ["86"]],
  ["eb-112-4", "117", ["126", "127"]],
  ["eb-112-1", "327", ["≈130"]],
  ["ed-13-1", "194", ["213"]],
  ["eb-13-1", "1", ["6", "313"]],
  ["eb-132-7", "542", ["556"]],
  ["eb-132-8", "117", ["124"]],
  ["eb-132-4", "347", ["362", "363"]],
  ["eb-132-11", "172", ["≈89"]],
  ["eb-132-14", "310", ["280"]],
  ["eb-132-16", "10", ["17", "190"]],
  ["ed-132-2", "391", ["414"]],
  ["ed-132-5", "291", ["304", "305"]],
  ["ed-132-9", "140", ["163", "165"]],
  ["ed-132-16", "169", ["186"]],
  ["ed-132-23", "278", ["280"]],
  ["ed-132-29", "98", ["101"]],
  ["eb-19-3", "22", ["33"]],
  ["eb-19-4", "1", ["6", "127"]],
  ["ed-19-3", "130", ["153"]],
  ["ed-19-4", "129", ["159", "161", "162"]],
  ["ed-19-5", "27", ["32", "33"]],
  ["eb-121-1", "110", ["507"]],
  ["eb-121-1", "170", ["590"]],
  ["eb-121-3", "108", ["119"]],
  ["eb-121-8", "341", ["349"]],
  ["ed-121-2", "46", ["56"]],
  ["ed-121-8", "160", ["205"]],
  ["ed-121-13", "95", ["102"]],
  ["eb-129-2", "123", ["128", "129"]],
  ["eb-129-3", "258", ["267", "269"]],
  ["ed-129-1", "21", ["29", "32"]],
  ["ed-129-3", "185", ["219"]],
  ["ed-129-6", "133", ["140", "142"]],
  ["ed-129-8", "19", ["19"]],
  ["eb-97-5", "125", ["128", "129"]],
  ["eb-97-5", "170", ["164"]],
  ["eb-97-6", "1", ["8", "104"]],
  ["eb-97-6", "99", ["60"]],
  ["ed-97-1", "362", ["406"]],
  ["ed-97-4", "210", ["232"]],
  ["ed-97-9", "197", ["204", "205"]],
  ["ed-97-6", "92", ["116", "120"]],
  ["eb-8-1-2", "40", ["45", "223", "335"]],
  ["eb-8-9", "114", ["119", "121"]],
  ["eb-8-10", "410", ["419", "420"]],
  ["eb-8-16", "36", ["43", "44", "45"]],
  ["eb-8-17", "46", ["30"]],
  ["ed-8-2", "151", ["169", "170"]],
  ["ed-8-11", "285", []],
  ["ed-8-14", "500", ["46"]],
  ["ed-8-15", "178", []],
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

const cutOff = !site.unitsBySlug.get("sb-267-2-1-5").pdfParts;
failures += cutOff ? 0 : 1;
console.log(`${cutOff ? "ok  " : "FAIL"} SB 267/2/1/5 (naissances 1898-1903, publiées jusqu'en 1899) → pas de page déduite`);

const placeholderHidden = !search("Prilly", "mariage", "1850").cotes.some(cote => cote.includes("FANTOME"));
failures += placeholderHidden ? 0 : 1;
console.log(`${placeholderHidden ? "ok  " : "FAIL"} Prilly / mariage / 1850 → pas de fiche FANTOME parmi les registres`);

const aigle1950 = search("Aigle", "mariage", "1950");
const gapShown = !aigle1950.cotes.some(cote => cote.includes("FANTOME")) && /Registre non versé aux ACV : <a href="https:\/\/davel\.vd\.ch\/detail\.aspx\?ID=680326"[^>]*>SB 268\/2\/11<\/a> \(promesses de mariage, lacune du 01\.05\.1947 au 18\.01\.1961\)/.test(aigle1950.answers);
failures += gapShown ? 0 : 1;
console.log(`${gapShown ? "ok  " : "FAIL"} Aigle / mariage / 1950 → SB 268/2/11 FANTOME signalé comme registre non versé aux ACV, pas comme registre`);

const promiseNote = search("Ollon", "mariage", "15.10.1957").answers.includes("registres de promesses des 6 mois précédents (SB 268/73/10)");
const ok7 = promiseNote && !search("Ollon", "deces", "15.10.1957").cotes.some(cote => cote.startsWith("SB 268"));
failures += ok7 ? 0 : 1;
console.log(`${ok7 ? "ok  " : "FAIL"} Ollon / mariage / 15.10.1957 → promesses des six mois précédents signalées, pas pour les décès`);

const familyNote = search("Ollon", "naissance", "1932").answers.includes("registre des familles de la commune d'origine (à confirmer)") && !search("Ollon", "naissance", "1920").answers.includes("registre des familles");
failures += familyNote ? 0 : 1;
console.log(`${familyNote ? "ok  " : "FAIL"} Ollon / naissance / 1932 → notice SB 269 et registres des familles, absente en 1920`);

const consultable = aigle1950.answers.includes("Librement consultable en entier dès 2038, 80 ans après ses derniers actes.") && !search("Aigle", "mariage", "1900").answers.includes("Librement consultable en entier");
failures += consultable ? 0 : 1;
console.log(`${consultable ? "ok  " : "FAIL"} Aigle / mariage / 1950 → SB 267/2/2/13 librement consultable en entier dès 2038, rien pour 1900`);

const annexBounded = search("Arzier", "deces", "1847").cotes.includes("Ed 58/4") && !search("Arzier", "deces", "1837").cotes.includes("Ed 58/4");
failures += annexBounded ? 0 : 1;
console.log(`${annexBounded ? "ok  " : "FAIL"} Arzier / deces → Ed 58/4 de Genolier en 1847, pas en 1837 (annexe de Genolier 1846-1849)`);

const sarrazCorrected = !search("La Sarraz", "naissance", "1865").cotes.includes("Ed 70/2") && !search("La Sarraz", "naissance", "1877").cotes.includes("SB 23/165");
failures += sarrazCorrected ? 0 : 1;
console.log(`${sarrazCorrected ? "ok  " : "FAIL"} La Sarraz / naissance → ni Ed 70/2 en 1865 (jusqu'en 1860), ni SB 23/165 en 1877 (1882-1883)`);

const veveyMarriages1879 = search("Vevey", "mariage", "1879").cotes;
const veveyCorrected = !search("Vevey", "naissance", "1704").cotes.includes("Eb 132/7") && !veveyMarriages1879.includes("SB 23/1057") && !veveyMarriages1879.includes("SB 115/513");
failures += veveyCorrected ? 0 : 1;
console.log(`${veveyCorrected ? "ok  " : "FAIL"} Vevey → ni Eb 132/7 en 1704 (hors Vevey dès 1764), ni SB 23/1057 et SB 115/513 en 1879 (1894 et 1910)`);

const bullet1739 = search("Bullet", "naissance", "1739");
const bulletOwnParish = !bullet1739.cotes.includes("Eb 121/2") && bullet1739.answers.includes("Registres dès 1744") && !search("Bullet", "mariage", "1763").cotes.includes("Eb 121/6");
failures += bulletOwnParish ? 0 : 1;
console.log(`${bulletOwnParish ? "ok  " : "FAIL"} Bullet → plus Sainte-Croix après 1663 ; en 1739, l'inventaire de Bullet : « Registres dès 1744 »`);

const roche1859 = search("Roche", "mariage", "23.09.1859").cotes;
const rocheBounded = roche1859.includes("Ed 136/4") && !roche1859.includes("Ed 90/2") && !roche1859.includes("Ed 143/2");
failures += rocheBounded ? 0 : 1;
console.log(`${rocheBounded ? "ok  " : "FAIL"} Roche / mariage / 23.09.1859 → Ed 136/4 (Villeneuve 1845-1863), ni Ed 90/2 (Noville jusqu'en 1821) ni Ed 143/2 (Yvorne 1837-1845 et dès 1863)`);

const aigleForCorbeyrier = year => search("Corbeyrier", "deces", year).cotes.some(cote => cote.startsWith("Ed 3/"));
const severalPeriods = aigleForCorbeyrier("1850") && !aigleForCorbeyrier("1843") && !aigleForCorbeyrier("1870") && !search("Ballaigues", "naissance", "1800").cotes.some(cote => cote.startsWith("Eb 74/"));
failures += severalPeriods ? 0 : 1;
console.log(`${severalPeriods ? "ok  " : "FAIL"} Corbeyrier / deces → Aigle (Ed 3) en 1850, ni en 1843 ni en 1870 (jusqu'en 1840 et 1846-1865) ; Ballaigues / naissance / 1800 → pas Lignerolle (jusqu'en 1725 et 1846-1849)`);

const oronCorrected = !search("Oron-la-Ville", "mariage", "1896").cotes.includes("SB 23/2065");
failures += oronCorrected ? 0 : 1;
console.log(`${oronCorrected ? "ok  " : "FAIL"} Oron-la-Ville / mariage / 1896 → pas SB 23/2065 (mariages 1898)`);

const startNoteOnlyWhenEmpty =!search("Ollon", "naissance", "1787").answers.includes("Registres dès") && search("Ollon", "naissance", "1590").answers.includes("Registres dès 1602");
failures += startNoteOnlyWhenEmpty ? 0 : 1;
console.log(`${startNoteOnlyWhenEmpty ? "ok  " : "FAIL"} Ollon / naissance → « Registres dès 1602 » en 1590, sans registre, pas en 1787`);

const villeneuveCorrected = !search("Villeneuve", "mariage", "1940").answers.includes("1935-1951");
failures += villeneuveCorrected ? 0 : 1;
console.log(`${villeneuveCorrected ? "ok  " : "FAIL"} Villeneuve / mariage → SB 115/637 daté 1935-1941, pas 1935-1951`);

const dataJson = JSON.parse(readFileSync(new URL("../docs/data.json", import.meta.url), "utf8"));
const published = dataJson.generatedAt === site.DATA.generatedAt && dataJson.units.length === site.DATA.units.length;
failures += published ? 0 : 1;
console.log(`${published ? "ok  " : "FAIL"} docs/data.json → mêmes données et même generatedAt que docs/index.html`);

const coveragePanel = elements.get("coverage-panel").innerHTML;
const covered = coveragePanel.includes(`data-place="paroisse-15">Bex</button>`) && /Pages du PDF<\/strong> : pour [^(]*Ollon[^(]* \(\d+ registres\)/.test(coveragePanel);
failures += covered ? 0 : 1;
console.log(`${covered ? "ok  " : "FAIL"} couverture → Bex parmi les paroisses indexées, Ollon parmi les pages du PDF reliées`);

process.exit(failures ? 1 : 0);
