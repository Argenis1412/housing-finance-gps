import {test, expect, type Page} from "@playwright/test";

const path = "/api/v1/comparison/saved-simulations";
async function review(page: Page) {
  await page.goto("/");
  const values: Record<string, string> = {opening: "200,00", property: "60,00", rent: "1,00", adjustment: "0", firstAdjustment: "13", minimum: "0,00", maximum: "200,00", principal: "60,00", down: "0,00", financeTerm: "60", financeRate: "0", fee: "0,00", invested: "0,00", contribution: "0,00", return: "0", letter: "60,00", consortiumTerm: "60", contemplation: "1", topup: "0,00"};
  for (const [name, value] of Object.entries(values)) await page.locator(`input[name="${name}"]`).fill(value);
  await page.getByLabel("Rótulo do cenário de contemplação").selectOption("early");
  await page.getByLabel("Identificação do componente", {exact: true}).fill("synthetic-income");
  await page.getByLabel("Valor do componente", {exact: true}).fill("3,00");
  await page.getByLabel("Referência da fonte", {exact: true}).fill("synthetic-source");
  await page.getByLabel("Data da fonte em UTC", {exact: true}).fill("2026-11-03T12:00:00Z");
  await page.getByLabel("Classificação", {exact: true}).selectOption("projected_assumption");
  await page.getByLabel("Referência da premissa", {exact: true}).fill("synthetic-plan");
  await page.getByRole("button", {name: "Revisar aplicação do componente"}).click();
  await expect(page.getByText("0 de 60 declarados", {exact: true})).toBeVisible();
  await page.getByRole("button", {name: "Confirmar declarações do perfil"}).click();
  await page.getByLabel("Tipo de fluxo").selectOption("external_expenses");
  // The existing identity cannot change sides, even on a different month.
  await page.getByRole("button", {name: "Revisar aplicação do componente"}).click();
  await expect(page.getByRole("alert", {name: "Erro do perfil"})).toContainText("outro lado");
  await page.getByLabel("Identificação do componente", {exact: true}).fill("synthetic-expense");
  await page.getByLabel("Valor do componente", {exact: true}).fill("1,00");
  await page.getByRole("button", {name: "Revisar aplicação do componente"}).click();
  await page.getByRole("button", {name: "Confirmar declarações do perfil"}).click();
  await expect(page.getByText("60 de 60 declarados", {exact: true})).toBeVisible();
  for (const label of ["Crédito", "Administração", "Fundo de reserva", "Seguro"]) await page.getByLabel(`${label} por mês`, {exact: true}).fill(label === "Crédito" ? "1,00" : "0,00");
  await page.getByLabel("Até o mês do cronograma", {exact: true}).fill("60");
  await page.getByRole("button", {name: "Revisar cópia do cronograma", exact: true}).click();
  await page.getByRole("button", {name: "Confirmar cópia do cronograma", exact: true}).click();
  await page.getByLabel("Valor de espera a repetir").fill("1,00");
  await page.getByRole("button", {name: "Revisar cópia dos custos de espera"}).click();
  await page.getByRole("button", {name: "Confirmar cópia do cronograma", exact: true}).click();
  await page.getByRole("checkbox").nth(0).check(); await page.getByRole("checkbox").nth(1).check();
  await page.getByRole("button", {name: "Revisar declarações", exact: true}).click();
  await expect(page.getByRole("heading", {name: "Revise o que você declarou"})).toBeVisible();
}

test.beforeEach(async ({request}) => {
  const response = await request.get(path);
  expect(response.status()).toBe(200);
  for (const item of (await response.json()).items) expect((await request.delete(`${path}/${item.simulation_id}`)).status()).toBe(204);
});

test("review, atomic save, reload, readonly reopening and confirmed deletion", async ({page, request}, info) => {
  await review(page);
  const response = page.waitForResponse(r => r.url().endsWith(path) && r.request().method() === "POST");
  await page.getByRole("button", {name: "Comparar e salvar", exact: true}).click();
  const created = await response;
  expect(created.status()).toBe(201);
  await expect(page.getByText("Comparação salva em", {exact: false})).toBeVisible();
  const stored = await (await request.get(`${path}/${created.request().postDataJSON().operation_id}`)).json();
  await expect(page.getByRole("heading", {name: "Empate no primeiro grupo: SAC e Price"})).toBeVisible();
  await expect(page.getByRole("button", {name: "Editar dados e revisar novamente"})).toHaveCount(0);
  await page.reload();
  await expect(page.locator('input[name="opening"]')).toHaveValue("");
  await page.getByRole("link", {name: "Comparações salvas", exact: true}).first().click();
  await page.getByRole("button", {name: `Abrir ${stored.simulation_id.slice(0, 8)}`, exact: true}).click();
  await expect(page.getByRole("heading", {name: "Empate no primeiro grupo: SAC e Price"})).toBeVisible();
  await expect(page.getByText("Histórico salvo em", {exact: false})).toContainText(stored.saved_at);
  await expect(page.getByRole("button", {name: "Editar dados e revisar novamente"})).toHaveCount(0);
  await page.getByText("Examinar os 60 meses e a proveniência", {exact: true}).click();
  await expect(page.getByText("synthetic-source", {exact: false}).first()).toBeVisible();
  expect((await (await request.get(`${path}/${stored.simulation_id}`)).json())).toEqual(stored);
  await page.screenshot({path: info.outputPath("saved-result.png"), fullPage: true});
  await page.getByRole("button", {name: "Excluir esta comparação"}).click();
  await expect(page.getByRole("alertdialog")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", {name: "Confirmar exclusão"})).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", {name: "Cancelar exclusão"})).toBeFocused();
  await page.keyboard.press("Enter");
  expect((await request.get(`${path}/${stored.simulation_id}`)).status()).toBe(200);
  await page.getByRole("button", {name: "Excluir esta comparação"}).click();
  await expect(page.getByRole("alertdialog")).toBeFocused();
  await page.getByRole("button", {name: "Confirmar exclusão"}).click();
  await expect(page.getByText("Nenhuma comparação salva nesta página.")).toBeVisible();
  await expect(page.getByRole("heading", {name: "Quatro caminhos, as mesmas origens"})).toHaveCount(0);
  expect((await request.get(`${path}/${stored.simulation_id}`)).status()).toBe(410);
});

test("lost confirmation retries the same committed operation without another record", async ({page, request}) => {
  await review(page);
  const ids: string[] = [];
  let release!: () => void;
  const pause = new Promise<void>(resolve => {release = resolve;});
  let entered!: () => void;
  const intercepted = new Promise<void>(resolve => {entered = resolve;});
  await page.route(`**${path}`, async route => {
    ids.push(route.request().postDataJSON().operation_id);
    if (ids.length === 1) {
      entered(); await pause;
      const response = await route.fetch(); expect(response.status()).toBe(201);
      await route.abort("failed");
    } else await route.continue();
  });
  await page.getByRole("button", {name: "Comparar e salvar", exact: true}).click();
  await intercepted;
  await expect(page.getByRole("button", {name: "Editar dados", exact: true})).toBeDisabled();
  release();
  await expect(page.getByRole("heading", {name: "Confirmação da gravação pendente"})).toBeVisible();
  await expect(page.getByRole("heading", {name: "Revise o que você declarou"})).toBeVisible();
  const retried = page.waitForResponse(r => r.url().endsWith(path) && r.request().method() === "POST");
  await page.getByRole("button", {name: "Tentar comparar e salvar novamente"}).click();
  expect((await retried).status()).toBe(200);
  await expect(page.getByText("Comparação salva em", {exact: false})).toBeVisible();
  expect(ids).toHaveLength(2); expect(ids[0]).toBe(ids[1]);
  expect((await (await request.get(path)).json()).items).toHaveLength(1);
});

test("unavailable write preserves review and explicit retry succeeds", async ({page}) => {
  await review(page);
  await page.route(`**${path}`, route => route.fulfill({status: 503, json: {api_version: "v1", code: "storage_busy", message_pt_br: "safe"}}));
  await page.getByRole("button", {name: "Comparar e salvar", exact: true}).click();
  await expect(page.getByRole("alert", {name: "Falha na comparação"})).toContainText("banco local está ocupado");
  await expect(page.getByRole("heading", {name: "Revise o que você declarou"})).toBeVisible();
  await page.unroute(`**${path}`);
  await page.getByRole("button", {name: "Tentar comparar e salvar novamente"}).click();
  await expect(page.getByText("Comparação salva em", {exact: false})).toBeVisible();
});

test("unsupported saved response is not rendered and remains deletable from list", async ({page}) => {
  await review(page);
  await page.getByRole("button", {name: "Comparar e salvar", exact: true}).click();
  await expect(page.getByText("Comparação salva em", {exact: false})).toBeVisible();
  await page.goto("/saved");
  await expect(page.getByRole("button", {name: /^Abrir /})).toHaveCount(1);
  await page.route(`**${path}/*`, async route => {
    const response = await route.fetch();
    const value = await response.json(); value.result.engine_version = "unknown";
    await route.fulfill({response, json: value});
  });
  await page.getByRole("button", {name: /^Abrir /}).click();
  await expect(page.getByRole("alert", {name: "Falha nas comparações salvas"})).toContainText("versões recebidas são incompatíveis");
  await expect(page.getByRole("heading", {name: "Quatro caminhos, as mesmas origens"})).toHaveCount(0);
  await page.unroute(`**${path}/*`);
  await page.getByRole("button", {name: /^Excluir /}).click();
  await page.getByRole("button", {name: "Confirmar exclusão"}).click();
  await expect(page.getByText("Nenhuma comparação salva nesta página.")).toBeVisible();
});


test("an illegible index date does not hide or prevent deleting a saved record", async ({page}) => {
  await review(page);
  await page.getByRole("button", {name: "Comparar e salvar", exact: true}).click();
  await expect(page.getByText("Comparação salva em", {exact: false})).toBeVisible();
  await page.route(`**${path}?*`, async route => {
    const response = await route.fetch(); const value = await response.json();
    if (value.items.length) value.items[0].saved_at = "broken";
    await route.fulfill({response, json: value});
  });
  await page.goto("/saved");
  await expect(page.getByText("Data de gravação ilegível", {exact: false})).toBeVisible();
  await page.getByRole("button", {name: /^Excluir /}).click();
  await page.getByRole("button", {name: "Confirmar exclusão"}).click();
  await expect(page.getByText("Nenhuma comparação salva nesta página.")).toBeVisible();
});

test("damaged index IDs use safe locators through the proxy and remain deletable", async ({page}) => {
  let damaged = "", remaining = true;
  await page.route(`**${path}?*`, route => route.fulfill({json: {api_version: "v1", kind: "saved_comparison_list", items: remaining ? [{simulation_id: damaged, saved_at: "2026-11-04T12:00:00Z"}] : [], next_offset: null}}));
  await page.route(`**${path}/*`, async route => {
    const locator = "~" + Buffer.from(damaged, "utf8").toString("base64url");
    expect(new URL(route.request().url()).pathname).toBe(`${path}/${locator}`);
    // The real proxy/backend must receive the locator as one path segment.
    const response = await route.fetch();
    expect(response.status()).toBe(404);
    expect((await response.json()).code).toBe("simulation_not_found");
    if (route.request().method() === "DELETE") {
      remaining = false; await route.fulfill({status: 204, body: ""});
    } else await route.fulfill({status: 500, json: {api_version: "v1", code: "stored_simulation_corrupt", message_pt_br: "safe"}});
  });
  for (damaged of ["broken-id", "", ".", "..", "broken/id?#%", "índice\u0000"]) {
    remaining = true;
    await page.goto("/saved");
    await page.getByRole("button", {name: /^Abrir(?: |$)/}).click();
    await expect(page.getByRole("alert", {name: "Falha nas comparações salvas"})).toBeVisible();
    await page.getByRole("button", {name: /^Excluir(?: |$)/}).click();
    await expect(page.getByRole("alertdialog")).toBeFocused();
    await page.getByRole("button", {name: "Confirmar exclusão"}).click();
    await expect(page.getByText("Nenhuma comparação salva nesta página.")).toBeVisible();
  }
});
