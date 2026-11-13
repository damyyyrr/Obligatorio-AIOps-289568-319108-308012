const path = require("node:path");
const { defineConfig } = require("cypress");
const createBundler = require("@bahmutov/cypress-esbuild-preprocessor");
const { addCucumberPreprocessorPlugin } = require("@badeball/cypress-cucumber-preprocessor");
const { createEsbuildPlugin } = require("@badeball/cypress-cucumber-preprocessor/esbuild");

module.exports = defineConfig({
  video: false,
  screenshotOnRunFailure: false,
  screenshotsFolder: path.join(process.env.BDD_RUN_OUTPUT || ".runtime", "screenshots"),
  downloadsFolder: ".runtime/downloads",
  fixturesFolder: "fixtures",
  numTestsKeptInMemory: 0,
  retries: 0,
  defaultCommandTimeout: 10000,
  requestTimeout: 10000,
  responseTimeout: 20000,
  e2e: {
    baseUrl: "http://127.0.0.1:4200",
    specPattern: "features/**/*.feature",
    supportFile: false,
    testIsolation: true,
    async setupNodeEvents(on, config) {
      await addCucumberPreprocessorPlugin(on, config);
      on("file:preprocessor", createBundler({
        plugins: [createEsbuildPlugin(config)],
      }));
      on("task", {
        credentials() {
          const userName = process.env.BDD_USERNAME;
          const password = process.env.BDD_PASSWORD;
          if (!userName || !password) {
            throw new Error("Definir BDD_USERNAME y BDD_PASSWORD con la cuenta Administrator del entorno de prueba.");
          }
          return { userName, password };
        },
      });
      return config;
    },
  },
});
