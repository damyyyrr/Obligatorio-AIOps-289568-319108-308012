const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { build } = require("esbuild");
const { createEsbuildPlugin } = require("@badeball/cypress-cucumber-preprocessor/esbuild");

(async () => {
  process.chdir(path.join(__dirname, ".."));
  const major = Number(process.versions.node.split(".")[0]);
  if (major !== 22 || Number(process.versions.node.split(".")[1]) < 16) {
    throw new Error("Usar Node 22.16 o posterior de la serie 22.");
  }
  const cli = path.join(path.dirname(require.resolve("@cucumber/cucumber/package.json")), "bin/cucumber.js");
  const feature = process.argv[2] || "features/pharmago.feature";
  const result = spawnSync(process.execPath, [cli, "--dry-run", "--strict",
    "--format", "json", "--require", "scripts/dry-run.cjs", feature], {
    encoding: "utf8", timeout: 60000,
  });
  if (result.error || result.status !== 0) throw new Error("Gherkin: pasos ausentes, ambiguos o sintaxis inválida.");
  // Cucumber puede devolver exit 0 para pasos undefined durante --dry-run.
  // Validar el reporte estructurado impide que el CI acepte pasos sin definir.
  const scenarios = JSON.parse(result.stdout).flatMap((entry) => entry.elements || []);
  const steps = scenarios.flatMap((scenario) => scenario.steps || []);
  if (!scenarios.length || !steps.length || steps.some((step) => step.result?.status !== "skipped")) {
    throw new Error("Gherkin: pasos ausentes/ambiguos o ningún escenario comprobado.");
  }
  console.log(scenarios.length + " escenarios y " + steps.length + " pasos reconocidos (dry-run; omitidos).");
  const configFile = require("../cypress.config.cjs");
  const config = { ...configFile, ...configFile.e2e, projectRoot: process.cwd(),
    env: {}, testingType: "e2e", isTextTerminal: true, reporter: "spec", excludeSpecPattern: [] };
  const events = new Map();
  await config.e2e.setupNodeEvents((name, handler) => events.set(name, handler), config);
  if (!events.has("file:preprocessor")) throw new Error("Falta el preprocesador de Cypress.");
  await build({
    entryPoints: [feature], bundle: true, write: false,
    platform: "browser", plugins: [createEsbuildPlugin(config)],
  });
  console.log("PASS preparación: Gherkin, resolución de pasos y bundle Cypress/Cucumber.");
  console.log("No se abrió un navegador ni se verificó la aplicación.");
})().catch((error) => { console.error(error.message); process.exitCode = 1; });
