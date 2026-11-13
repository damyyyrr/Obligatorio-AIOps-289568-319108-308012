module.exports = function register({ Given, When, Then }) {

const api = "http://127.0.0.1:5000";
const field = (name) => cy.get('[data-cy="' + name + '"]');

function login(invalid) {
  cy.intercept("POST", api + "/api/login").as("login");
  cy.task("credentials", null, { log: false }).then(({ userName, password }) => {
    field("login-username").clear({ log: false }).type(userName, { log: false });
    field("login-password").clear({ log: false })
      .type(invalid ? password + "-invalid" : password, { log: false, parseSpecialCharSequences: false });
  });
  field("login-submit").click();
}

function catalog() {
  cy.intercept("GET", api + "/api/drug").as("catalog");
}

function checkCatalogResponse() {
  cy.wait("@catalog").then(({ response }) => {
    expect(response.statusCode).to.equal(200);
    cy.fixture("catalog").then((expected) => {
      expect(response.body.some((drug) => drug.code === expected.code && drug.name === expected.name),
        "El seed de laboratorio está disponible").to.equal(true);
    });
  });
}

Given("que estoy en la pantalla de acceso", () => {
  cy.visit("/login");
  field("login-submit").should("be.visible");
});

When("ingreso las credenciales válidas del administrador de prueba", () => login(false));
When("ingreso una contraseña incorrecta para el administrador de prueba", () => login(true));

Then("accedo al panel de administrador con una sesión válida", () => {
  cy.wait("@login").then(({ response }) => {
    expect(response.statusCode).to.equal(200);
    expect(response.body.role).to.equal("Administrator");
    expect(Boolean(response.body.token), "El servidor entrega una sesión").to.equal(true);
  });
  cy.location("pathname").should("equal", "/admin");
  cy.get("app-admin").should("be.visible");
  cy.window({ log: false }).should((win) => {
    const session = JSON.parse(win.localStorage.getItem("login"));
    expect(Boolean(session && session.token), "Se guardó la sesión").to.equal(true);
    expect(session && session.role).to.equal("Administrator");
  });
});

Then("veo el error de contraseña y permanezco sin sesión", () => {
  cy.wait("@login").its("response.statusCode").should("equal", 400);
  field("toast").should("be.visible").and("contain.text", "Invalid Password");
  cy.location("pathname").should("equal", "/login");
  cy.window({ log: false }).should((win) => {
    expect(JSON.parse(win.localStorage.getItem("login")), "No se creó sesión").to.equal(null);
  });
});

Then("puedo volver a intentar el acceso sin recargar la página", () => {
  login(false);
  cy.wait("@login").its("response.statusCode").should("equal", 200);
  cy.location("pathname").should("equal", "/admin");
  cy.get("app-admin").should("be.visible");
});

Given("que consulto el catálogo de medicamentos", () => {
  catalog();
  cy.visit("/home");
  checkCatalogResponse();
});

Then("veo el medicamento de demostración con su farmacia y precio", () => {
  cy.fixture("catalog").then((expected) => {
    cy.contains('[data-cy="drug-card"]', expected.name).as("drugCard")
      .should("be.visible").and("contain.text", expected.pharmacy);
    cy.get("@drugCard").find('[data-cy="drug-price"]')
      .should("contain.text", expected.price.toFixed(2));
  });
});

When("abro el detalle de ese medicamento", () => {
  cy.intercept("GET", api + "/api/drug/*").as("detail");
  cy.get("@drugCard").find('[data-cy="drug-details-link"]').click();
  cy.wait("@detail").then(({ response }) => {
    expect(response.statusCode).to.equal(200);
    cy.fixture("catalog").then((expected) => expect(response.body.code).to.equal(expected.code));
    cy.location("pathname").should("equal", "/home/detail/" + response.body.id);
  });
});

Then("veo su código, presentación y síntomas", () => {
  cy.fixture("catalog").then((expected) => {
    field("drug-detail").should("be.visible")
      .and("contain.text", expected.name)
      .and("contain.text", expected.code)
      .and("contain.text", expected.symptom)
      .and("contain.text", expected.presentation);
  });
  // Única captura automática: pantalla pública del catálogo, sin formulario de acceso.
  cy.screenshot("catalogo-detalle", { capture: "viewport" });
});

When("consulto el detalle de un medicamento inexistente", () => {
  cy.fixture("catalog").then(({ missingId }) => {
    cy.intercept("GET", api + "/api/drug/" + missingId).as("missingDrug");
    cy.visit("/home/detail/" + missingId);
  });
});

Then("veo un error y ningún detalle de medicamento", () => {
  cy.wait("@missingDrug").its("response.statusCode").should("equal", 404);
  field("toast").should("be.visible").and("contain.text", "Error").and("contain.text", "Get Drug");
  field("drug-detail").should("not.exist");
});

When("regreso al catálogo desde la cabecera", () => {
  catalog();
  field("home-link").click();
  checkCatalogResponse();
});
};
