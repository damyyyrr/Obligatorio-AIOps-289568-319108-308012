const assert = require("node:assert/strict");
const test = require("node:test");
const summarizeTest = require("./results.cjs");

test("Cypress 15 aporta la duración del test aunque sus intentos solo tengan estado", () => {
  assert.deepEqual(summarizeTest({ title: ["Acceso", "Login"], state: "passed", duration: 2576,
    attempts: [{ state: "passed" }] }), {
    title: "Acceso > Login", state: "passed", durationMs: 2576,
  });
});

test("una duración ausente o inválida queda indeterminada, nunca se inventa cero", () => {
  for (const duration of [undefined, null, NaN, Infinity, -1, "123"]) {
    assert.equal(summarizeTest({ title: ["Consulta"], state: "failed", duration }).durationMs, null);
  }
});

test("cero medido se conserva y el resumen excluye detalles privados del resultado", () => {
  assert.deepEqual(summarizeTest({ title: ["Consulta"], state: "passed", duration: 0,
    attempts: [{ state: "passed", error: "private-response" }], env: { password: "private" } }), {
    title: "Consulta", state: "passed", durationMs: 0,
  });
});
