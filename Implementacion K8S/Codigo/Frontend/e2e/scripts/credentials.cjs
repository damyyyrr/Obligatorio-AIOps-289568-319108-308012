const fs = require("node:fs");
const path = require("node:path");

module.exports = function credentials() {
  if (process.argv.includes("--demo")) {
    // Opt-in explícito y exclusivo para el baseline local con el seed docente.
    const seed = fs.readFileSync(path.join(__dirname, "../../../Backend/seed-data.sql"), "utf8");
    const match = seed.match(/VALUES\s*\('admin',\s*'[^']+',\s*'([^']+)'/i);
    if (!match) throw new Error("No se pudo leer la cuenta de demostración del seed.");
    process.env.BDD_USERNAME = "admin";
    process.env.BDD_PASSWORD = match[1];
  }
  if (!process.env.BDD_USERNAME || !process.env.BDD_PASSWORD) {
    throw new Error("Definir BDD_USERNAME y BDD_PASSWORD (Administrator), o usar test:demo en el baseline de laboratorio.");
  }
};
