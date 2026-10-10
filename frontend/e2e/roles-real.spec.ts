import { test, expect, type Page } from "@playwright/test";

async function login(page: Page, espacio: string, usuario: string) {
  await page.goto("/ingresar");
  await page.getByLabel("Espacio administrativo").fill(espacio);
  await page.getByLabel("Usuario o correo").fill(usuario);
  await page.getByLabel("Clave").fill("ClaveE2e123!");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByText("Iniciar sesión", { exact: true })).toHaveCount(0);
  await page.goto("/configuracion");
}

test("SUPERADMIN real: consola exclusiva y backend rechaza operaciones", async ({ page }) => {
  await login(page, "PLATFORM", "SUPADMIN01");
  await expect(page.getByRole("heading", { name: /Consola SaaS/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Administraciones SaaS" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mantenimiento" })).toHaveCount(0);
  const inventario = await page.request.get("/api/v1/configuracion/administraciones");
  expect(inventario.status()).toBe(200);
  expect((await inventario.json()).length).toBe(2);
  expect((await page.request.get("/api/v1/configuracion/permisos")).status()).toBe(403);
  expect((await page.request.get("/api/v1/registros/opciones")).status()).toBe(403);
  await page.goto("/empresas");
  await expect(page).toHaveURL(/\/configuracion$/);
});

test("ADMINISTRADOR real: menú tenant y prohibición de inventario global", async ({ page }) => {
  await login(page, "PRUEBAS", "ADMIN01");
  await expect(page.getByRole("heading", { name: /Configuración de Administración/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Configuración de acceso" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Empresas registradas" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mantenimiento" })).toBeVisible();
  expect((await page.request.get("/api/v1/configuracion/permisos")).status()).toBe(200);
  expect((await page.request.get("/api/v1/configuracion/administraciones")).status()).toBe(403);
  await page.getByRole("button", { name: "Configuración de acceso" }).click();
  await expect(page.getByText(/Exclusivo del ADMINISTRADOR del tenant/)).toBeVisible();
});

test("credenciales ADMIN01 no funcionan en PLATFORM", async ({ request }) => {
  const r = await request.post("/api/v1/auth/login", {
    data: { espacio: "PLATFORM", login: "ADMIN01", clave: "ClaveE2e123!" },
  });
  expect(r.status()).toBe(401);
});
