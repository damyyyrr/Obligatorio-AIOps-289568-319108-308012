const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");
const { execFileSync } = require("node:child_process");
const summarizeTest = require("./results.cjs");

process.chdir(path.join(__dirname, ".."));
const output = path.resolve(".runtime/runs", new Date().toISOString().replace(/[:.]/g, "-") + "-" + randomUUID().slice(0, 8));
fs.mkdirSync(output, { recursive: true });
process.env.BDD_RUN_OUTPUT = output;
// Algunos launchers de Electron fijan esta variable en su proceso padre.
delete process.env.ELECTRON_RUN_AS_NODE;
const summary = { schemaVersion: 1, startedAt: new Date().toISOString(),
  mode: "live", status: "NOT_RUN", browserExecuted: false, scenarios: [] };

function save() {
  summary.finishedAt = new Date().toISOString();
  fs.writeFileSync(path.join(output, "summary.json"), JSON.stringify(summary, null, 2) + "\n");
  console.log("Resultado: " + summary.status + ". Evidencia: " + output);
}

(async () => {
  require("./credentials.cjs")();
  summary.commit = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
  summary.workingTreeDirty = Boolean(execFileSync("git", ["status", "--porcelain", "--untracked-files=normal"],
    { encoding: "utf8" }).trim());
  summary.nodeVersion = process.version;
  const ui = await fetch("http://127.0.0.1:4200/", { signal: AbortSignal.timeout(15000) });
  if (!ui.ok || !(await ui.text()).includes("<app-root")) throw new Error("Frontend no disponible.");
  const catalog = await fetch("http://127.0.0.1:5000/api/drug", { signal: AbortSignal.timeout(15000) });
  if (!catalog.ok) throw new Error("Gateway o catálogo no disponibles.");
  const rows = await catalog.json();
  const fixture = require("../fixtures/catalog.json");
  if (!Array.isArray(rows) || !rows.some((row) => row.code === fixture.code && row.name === fixture.name)) {
    throw new Error("Falta el medicamento de demostración; revisar el seed, sin resetear la base.");
  }

  const result = await require("cypress").run({ project: process.cwd(), browser: "electron",
    configFile: "cypress.config.cjs", env: { tags: "@live" } });
  if (result.status === "failed") throw new Error("Cypress no pudo ejecutar la suite; revisar la salida local.");
  summary.browserExecuted = result.totalTests > 0;
  summary.cypressVersion = result.cypressVersion;
  summary.browserName = result.browserName;
  summary.browserVersion = result.browserVersion;
  summary.counts = { total: result.totalTests, passed: result.totalPassed, failed: result.totalFailed,
    pending: result.totalPending, skipped: result.totalSkipped };
  summary.scenarios = result.runs.flatMap((run) => run.tests.map(summarizeTest));
  // No guardar el objeto completo de Cypress: incluye config, entorno y detalles privados.
  summary.status = result.totalTests === 4 && result.totalPassed === 4 && result.totalFailed === 0 &&
    result.totalPending === 0 && result.totalSkipped === 0 && result.runs.every((run) => !run.error) ? "PASS" : "FAIL";
  if (summary.status !== "PASS") process.exitCode = 1;
})().catch((error) => {
  summary.status = "BLOCKED";
  // Este archivo permanece local; se ocultan secretos conocidos y UUID de sesión.
  let message = String(error.message);
  for (const secret of [process.env.BDD_PASSWORD, process.env.BDD_USERNAME].filter(Boolean)) {
    message = message.split(secret).join("[REDACTED]");
  }
  message = message.replace(/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/gi, "[SESSION]");
  fs.writeFileSync(path.join(output, "diagnostic.txt"), message + "\n");
  console.error("No se completó la ejecución. Revisar diagnostic.txt y la salida local.");
  process.exitCode = 1;
}).finally(save);
