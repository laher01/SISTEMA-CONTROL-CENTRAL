import { test, expect } from "@playwright/test";

type Rol = "SUPERADMIN" | "ADMINISTRADOR";

async function entrar(page: import("@playwright/test").Page, rol: Rol) {
  let autenticado = false;
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const ruta = url.pathname;
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (ruta === "/api/v1/auth/me") {
      return json(autenticado ? 200 : 401, autenticado
        ? { rol, codigo: rol === "SUPERADMIN" ? "SUPADMIN01" : "ADMIN01",
            nombre: "Cuenta aislada", cambio_clave_obligatorio: false,
            jerarquia: [], es_administracion_demo: false }
        : { detail: "Sin sesión" });
    }
    if (ruta === "/api/v1/auth/login" && route.request().method() === "POST") {
      const datos = route.request().postDataJSON();
      if (datos.login !== (rol === "SUPERADMIN" ? "SUPADMIN01" : "ADMIN01"))
        return json(401, { detail: "Credenciales no válidas" });
      autenticado = true;
      return json(200, { rol, codigo: datos.login, cambio_clave_obligatorio: false });
    }
    if (ruta === "/api/v1/auth/administracion-publica")
      return json(200, { por_subdominio: false, nombre: "", codigo: "" });
    if (ruta === "/api/v1/auth/acceso-publico")
      return json(200, { registro_publico: false });
    if (ruta === "/api/v1/configuracion/administraciones")
      return json(rol === "SUPERADMIN" ? 200 : 403,
        rol === "SUPERADMIN" ? [] : { detail: "Prohibido" });
    if (ruta === "/api/v1/configuracion/permisos")
      return json(rol === "SUPERADMIN" ? 403 : 200,
        rol === "SUPERADMIN" ? { detail: "Prohibido" } : []);
    return json(403, { detail: "No autorizado en esta prueba aislada" });
  });
  await page.goto("/ingresar");
  await page.getByLabel("Espacio administrativo").fill(rol === "SUPERADMIN" ? "PLATFORM" : "PRUEBAS");
  await page.getByLabel("Usuario o correo").fill(rol === "SUPERADMIN" ? "SUPADMIN01" : "ADMIN01");
  await page.getByLabel("Clave").fill("ClaveTemporal123!");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.goto("/configuracion");
  await expect(page.getByRole("heading", { name: rol === "SUPERADMIN"
    ? /Consola SaaS/ : /Configuración de Administración/ })).toBeVisible();
}

test("SUPERADMIN: inicio de sesión, menú exclusivo y bloqueo de ruta operativa", async ({ page }) => {
  await entrar(page, "SUPERADMIN");
  await expect(page.getByRole("button", { name: "Administraciones SaaS" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mantenimiento" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Configuración de acceso" })).toHaveCount(0);
  await page.goto("/empresas");
  await expect(page).toHaveURL(/\/configuracion$/);
  await expect(page.getByRole("heading", { name: /Consola SaaS/ })).toBeVisible();
});

test("ADMINISTRADOR: inicio de sesión y controles de su tenant", async ({ page }) => {
  await entrar(page, "ADMINISTRADOR");
  await expect(page.getByRole("button", { name: "Configuración de acceso" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Empresas registradas" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mantenimiento" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Administraciones SaaS" })).toHaveCount(0);
  await page.getByRole("button", { name: "Configuración de acceso" }).click();
  await expect(page.getByText(/Exclusivo del ADMINISTRADOR del tenant/)).toBeVisible();
});
