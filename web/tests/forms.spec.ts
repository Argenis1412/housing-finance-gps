import {test, expect} from "@playwright/test";
import {copyComponent, createRequest, fieldGroups, initialForm, updateValue, type Component} from "../lib/form-state";
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
