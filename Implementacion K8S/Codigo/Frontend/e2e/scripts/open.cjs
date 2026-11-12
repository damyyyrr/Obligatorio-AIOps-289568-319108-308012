const path = require("node:path");
process.chdir(path.join(__dirname, ".."));
delete process.env.ELECTRON_RUN_AS_NODE;
try { require("./credentials.cjs")(); }
catch (error) { console.error(error.message); process.exit(1); }
require("cypress").open({ project: process.cwd(), configFile: "cypress.config.cjs" })
  .catch(() => { console.error("No se pudo abrir Cypress; revisar instalación y entorno."); process.exitCode = 1; });
