const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { randomUUID } = require("node:crypto");
const { spawnSync } = require("node:child_process");

process.chdir(path.join(__dirname, ".."));
const env = { ...process.env };
delete env.BDD_USERNAME;
delete env.BDD_PASSWORD;
const result = spawnSync(process.execPath, ["scripts/run.cjs"], {
  cwd: process.cwd(), env, encoding: "utf8", timeout: 15000,
});
assert.equal(result.status, 1, "Faltan credenciales: el runner debe fallar antes de abrir un navegador");
const runFolder = result.stdout.trim().split("Evidencia: ").at(-1);
const summary = JSON.parse(fs.readFileSync(path.join(runFolder, "summary.json"), "utf8"));
assert.equal(summary.status, "BLOCKED");
assert.equal(summary.browserExecuted, false);
assert.deepEqual(summary.scenarios, []);
assert.equal("env" in summary, false);
console.log("PASS sin credenciales: exit 1, BLOCKED y ningún navegador ejecutado.");

const folder = path.resolve(".runtime/guard-checks", randomUUID());
fs.mkdirSync(folder, { recursive: true });
const missing = path.join(folder, "missing-step.feature");
fs.writeFileSync(missing, "# language: es\nCaracterística: Control negativo\n  Escenario: Paso inexistente\n    Dado un paso que no tiene definición\n");
const bad = spawnSync(process.execPath, ["scripts/check.cjs", missing], {
  cwd: process.cwd(), encoding: "utf8", timeout: 60000,
});
assert.equal(bad.status, 1, "Un paso ausente debe impedir el PASS de preparación");
assert.match(bad.stderr, /pasos ausentes/);
console.log("PASS paso inexistente: la preparación rechaza el dry-run con exit 1.");
