// Contrato público de Cypress 15: la duración pertenece al test, no al intento.
module.exports = function summarizeTest(test) {
  return {
    title: test.title.join(" > "),
    state: test.state,
    durationMs: Number.isFinite(test.duration) && test.duration >= 0 ? test.duration : null,
  };
};
