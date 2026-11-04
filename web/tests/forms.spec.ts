import {test, expect} from "@playwright/test";
import {copyComponent, createRequest, fieldGroups, formErrors, initialForm, updateValue, type Component} from "../lib/form-state";
import {money} from "../lib/formatting";

const component: Component = {component_id: "synthetic-income", amount: "3.00", classification: "projected_assumption", source_reference: "synthetic-source", source_as_of: "2026-11-03T12:00:00Z", assumption_reference: "synthetic-plan"};

test("bulk copies preserve other identities, require explicit rows and forbid side changes", () => {
  const initial = initialForm();
  expect(initial.months.every(m => m.income_components === null)).toBe(true);
  const copied = copyComponent(initial, "income_components", component, 1, 60);
  const withOther = copyComponent(copied, "income_components", {...component, component_id: "other-income"}, 1, 1);
  const replaced = copyComponent(withOther, "income_components", {...component, amount: "5.00"}, 1, 1);
  expect(replaced.months[0].income_components?.map(c => c.component_id)).toEqual(["other-income", "synthetic-income"]);
  expect(replaced.months[1].income_components?.[0].amount).toBe("3.00");
  expect(() => copyComponent(replaced, "external_expenses", component, 60, 60)).toThrow("outro lado");
  expect(initial.months[0].income_components).toBeNull();
});

test("display retains exact cents beyond JS precision and signed resources", () => {
  expect(money("1152921504606846975988470784953931530.24")).toBe("R$ 1.152.921.504.606.846.975.988.470.784.953.931.530,24");
  expect(money("-1.01")).toBe("R$ -1,01");
});

test("editing periods preserves declarations through empty and intermediate values", () => {
  let form = updateValue(initialForm(), "consortiumTerm", "60");
  form.schedule = form.schedule.map(r => ({...r, credit_component: "1.00", administration_fee: "0.00", reserve_fund: "0.00", insurance: "0.00"}));
  form = updateValue(form, "consortiumTerm", "");
  expect(form.schedule).toEqual([]);
  form = updateValue(form, "consortiumTerm", "1");
  form = updateValue(form, "consortiumTerm", "12");
  form = updateValue(form, "consortiumTerm", "120");
  expect(form.schedule.slice(0, 60).every(r => r.credit_component === "1.00")).toBe(true);
  expect(form.schedule[60].credit_component).toBe("");
  form = updateValue(form, "contemplation", "60");
  form.waiting = form.waiting.map(r => ({...r, amount: "1.00"}));
  form = updateValue(form, "contemplation", "");
  form = updateValue(form, "contemplation", "6");
  form = updateValue(form, "contemplation", "60");
  expect(form.waiting).toHaveLength(60);
  expect(form.waiting.every(r => r.amount === "1.00")).toBe(true);
  form.schedule[0].credit_component = "2.00";
  form = updateValue(form, "consortiumTerm", "");
  form = updateValue(form, "consortiumTerm", "60");
  expect(form.schedule[0].credit_component).toBe("2.00");
});

test("first rent adjustment does not inherit the contractual term cap", () => {
  const form = updateValue(initialForm(), "firstAdjustment", "1000");
  for (const group of fieldGroups) for (const [key, , kind] of group.fields) if (!form.values[key]) form.values[key] = kind === "month" ? "1" : "0.00";
  const shared = createRequest(form).comparison.shared as Record<string, unknown>;
  expect(shared.first_rent_adjustment_month).toBe(1000);
});

test("review validates first-adjustment boundaries and canonical admitted rates", () => {
  for (const [value, valid] of [["1", false], ["2", true], ["1000", true]] as const) {
    const errors = formErrors(updateValue(initialForm(), "firstAdjustment", value));
    expect(errors.some(e => e.startsWith("Primeiro mês de reajuste:"))).toBe(!valid);
    if (!valid) expect(errors).toContain("Primeiro mês de reajuste: informe um mês inteiro maior que 1.");
  }
  for (const key of ["adjustment", "financeRate", "return"]) for (const [value, valid] of [["00.5", false], ["10", false], ["1.01", false], ["0,05", true], ["1.000", true]] as const) {
    const label = fieldGroups.flatMap(g => g.fields).find(([field]) => field === key)![1];
    expect(formErrors(updateValue(initialForm(), key, value)).some(e => e.startsWith(`${label}:`))).toBe(!valid);
  }
});

test("profile rejects impossible UTC dates and removal cancels a pending copy", async ({page}) => {
  await page.goto("/");
  await page.getByLabel("Identificação do componente", {exact: true}).fill("synthetic-income");
  await page.getByLabel("Valor do componente", {exact: true}).fill("3,00");
  await page.getByLabel("Referência da fonte", {exact: true}).fill("synthetic-source");
  await page.getByLabel("Classificação", {exact: true}).selectOption("observed_data");
  for (const date of ["2026-02-30T12:00:00Z", "2025-02-29T12:00:00Z", "0000-01-01T00:00:00Z", "2026-01-01T24:00:00Z", "2026-01-01T12:00:00+00:00"]) {
    await page.getByLabel("Data da fonte em UTC", {exact: true}).fill(date);
    await page.getByRole("button", {name: "Revisar aplicação do componente"}).click();
    await expect(page.getByRole("alert", {name: "Erro do perfil"})).toBeVisible();
    await expect(page.getByRole("region", {name: "Revisar cópia do perfil"})).toHaveCount(0);
  }
  await page.getByLabel("Data da fonte em UTC", {exact: true}).fill("2024-02-29T12:00:00Z");
  await page.getByRole("button", {name: "Revisar aplicação do componente"}).click();
  await page.getByRole("button", {name: "Confirmar declarações do perfil"}).click();
  await page.getByRole("button", {name: "Editar este componente", exact: true}).click();
  await page.getByRole("button", {name: "Revisar aplicação do componente"}).click();
  await expect(page.getByRole("region", {name: "Revisar cópia do perfil"})).toBeVisible();
  await page.getByRole("button", {name: "Remover do mês 1", exact: true}).click();
  await expect(page.getByRole("region", {name: "Revisar cópia do perfil"})).toHaveCount(0);
  await expect(page.getByRole("button", {name: "Editar este componente", exact: true})).toHaveCount(0);
});

test("schedule and waiting copies reject previews beyond a shortened period", async ({page}) => {
  await page.goto("/");
  await page.locator('input[name="consortiumTerm"]').fill("2");
  for (const label of ["Crédito", "Administração", "Fundo de reserva", "Seguro"]) await page.getByLabel(`${label} por mês`, {exact: true}).fill("1,00");
  await page.getByLabel("Até o mês do cronograma", {exact: true}).fill("2");
  await page.getByRole("button", {name: "Revisar cópia do cronograma", exact: true}).click();
  await page.locator('input[name="consortiumTerm"]').fill("1");
  await page.getByRole("button", {name: "Confirmar cópia do cronograma", exact: true}).click();
  await expect(page.getByRole("alert", {name: "Erro do cronograma"})).toContainText("prazo mudou");
  await expect(page.getByRole("region", {name: "Revisar cópia do cronograma"})).toHaveCount(0);
  await page.getByText("Editar as 1 linhas individualmente", {exact: true}).click();
  await expect(page.getByLabel("Crédito, mês 1", {exact: true})).toHaveValue("");
  await page.getByLabel("Até o mês do cronograma", {exact: true}).fill("1");
  await page.getByRole("button", {name: "Revisar cópia do cronograma", exact: true}).click();
  await page.getByRole("button", {name: "Confirmar cópia do cronograma", exact: true}).click();
  await expect(page.getByLabel("Crédito, mês 1", {exact: true})).toHaveValue("1.00");

  await page.locator('input[name="contemplation"]').fill("2");
  await page.getByLabel("Valor de espera a repetir", {exact: true}).fill("1,00");
  await page.getByLabel("Até o mês de espera", {exact: true}).fill("2");
  await page.getByRole("button", {name: "Revisar cópia dos custos de espera", exact: true}).click();
  await page.locator('input[name="contemplation"]').fill("1");
  await page.getByRole("button", {name: "Confirmar cópia do cronograma", exact: true}).click();
  await expect(page.getByRole("alert", {name: "Erro do cronograma"})).toContainText("prazo mudou");
  await page.getByText("Editar os 1 meses de espera", {exact: true}).click();
  await expect(page.getByLabel("Espera, mês 1", {exact: true})).toHaveValue("");
  await page.getByLabel("Até o mês de espera", {exact: true}).fill("1");
  await page.getByRole("button", {name: "Revisar cópia dos custos de espera", exact: true}).click();
  await page.getByRole("button", {name: "Confirmar cópia do cronograma", exact: true}).click();
  await expect(page.getByLabel("Espera, mês 1", {exact: true})).toHaveValue("1.00");
});

test("initial form is blank, keyboard accessible and communicates incomplete declarations", async ({page}, info) => {
  await page.goto("/");
  await expect(page.getByRole("heading", {level: 1})).toContainText("Declare o cenário");
  await expect(page.locator('input[name="opening"]')).toHaveValue("");
  await page.getByRole("button", {name: "Revisar declarações", exact: true}).click();
  await expect(page.getByRole("alert", {name: "Erros de preenchimento"})).toContainText("60 meses");
  await expect(page.getByRole("alert", {name: "Erros de preenchimento"})).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({path: info.outputPath("entry.png"), fullPage: true});
});
