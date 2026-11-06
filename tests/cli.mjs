import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const CLI = fileURLToPath(new URL("../cli/acv.mjs", import.meta.url));
const acv = (...args) => {
  const { status, stdout, stderr } = spawnSync(process.execPath, [CLI, ...args], { encoding: "utf8" });
  return { status, stdout, stderr };
};
const json = (...args) => JSON.parse(acv(...args, "--json").stdout);

const checks = [
  ["chercher Ollon naissance 1787 → Eb 92/3", () => json("chercher", "Ollon", "naissance", "1787").registers.map(unit => unit.cote).includes("Eb 92/3")],
  ["chercher accepte « baptême » pour naissance", () => json("chercher", "Ollon", "baptême", "1787").kind.id === "naissance"],
  ["chercher Huémoz naissance 17.02.1889 → SB 267/49/1/1", () => json("chercher", "Huémoz", "naissance", "17.02.1889").registers.some(unit => unit.cote === "SB 267/49/1/1")],
  ["chercher Ollon deces 1760 → répertoire des décès d'Eb 92/4 en PDF p. 382", () => {
    const unit = json("chercher", "Ollon", "deces", "1760").registers.find(candidate => candidate.cote === "Eb 92/4");
    return unit.pdfParts.some(part => part.relevant && part.pdf[0] === 382 && part.content.startsWith("Répertoire des décès"));
  }],
  ["chercher Ollon deces 1760 --page 177 → Eb 92/4 en PDF p. 380", () => {
    const unit = json("chercher", "Ollon", "deces", "1760", "--page", "177").registers.find(candidate => candidate.cote === "Eb 92/4");
    return unit.page.length === 1 && unit.page[0].pdf === 380 && unit.page[0].url.endsWith("#page=380");
  }],
  ["chercher Lutry naissance 1850 → pièces justificatives Ec 78/6", () => json("chercher", "Lutry", "naissance", "1850").justificatives.some(unit => unit.cote === "Ec 78/6")],
  ["page Eb 92/2 466 → PDF p. 544", () => JSON.stringify(json("page", "Eb 92/2", "466").targets.map(target => target.pdf)) === "[544]"],
  ["page Eb 118/1 xv → ≈ PDF p. 518", () => {
    const [target] = json("page", "eb 118/1", "xv").targets;
    return target.pdf === 518 && target.approx;
  }],
  ["page Ed 92/7 999 → aucune page", () => json("page", "Ed 92/7", "999").targets.length === 0],
  ["lieux chesi → Chesières", () => json("lieux", "chesi").some(entry => entry.name === "Chesières")],
  ["texte : chercher Ollon naissance 1787 affiche la cote et le PDF", () => {
    const { status, stdout } = acv("chercher", "Ollon", "naissance", "1787");
    return status === 0 && stdout.includes("Eb 92/3 · Registres paroissiaux") && stdout.includes("CH-ACV_RN-EB-92-3.pdf");
  }],
  ["texte : --page sur un registre sans pages reliées le dit", () => {
    const { stdout } = acv("chercher", "Huémoz", "naissance", "17.02.1889", "--page", "10");
    return stdout.includes("Page demandée : les pages de ce registre ne sont pas encore reliées au PDF.");
  }],
  ["lieu inconnu → code 2 et lieux proches", () => {
    const { status, stderr } = acv("chercher", "Olon", "naissance", "1787");
    return status === 2 && stderr.includes("Lieu inconnu") && stderr.includes("Molondin");
  }],
  ["date invalide → code 2", () => acv("chercher", "Ollon", "naissance", "31.02.1787").status === 2],
  ["acte inconnu → code 2", () => acv("chercher", "Ollon", "communion", "1787").status === 2],
  ["registre sans pages reliées → code 2", () => acv("page", "SB 267/49/1/1", "10").status === 2],
];

let failures = 0;
for (const [label, check] of checks) {
  const ok = check();
  failures += ok ? 0 : 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${label}`);
}
process.exit(failures ? 1 : 0);
