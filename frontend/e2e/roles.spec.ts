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

for (const codigo of ["JOSE02-G", "JOSE03-CH-G", "GESTOR-DE-PRUEBA"]) {
  test(`GESTOR ${codigo}: navega a OCR desde menú y botón de Documentos`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    let autenticado = false;
    await page.route("**/api/v1/**", async (route) => {
      const ruta = new URL(route.request().url()).pathname;
      const respuesta = (status: number, body: unknown) =>
        route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

      if (ruta === "/api/v1/auth/me") {
        return respuesta(autenticado ? 200 : 401, autenticado ? {
          rol: "GESTOR",
          codigo,
          nombre: `Cuenta ${codigo}`,
          miembro_id: null,
          gestor_id: `gestor-${codigo}`,
          usuario_id: `usuario-${codigo}`,
          cambio_clave_obligatorio: false,
          jerarquia: [],
        } : { detail: "Sin sesión" });
      }
      if (ruta === "/api/v1/auth/login" && route.request().method() === "POST") {
        autenticado = true;
        return respuesta(200, { rol: "GESTOR", codigo, cambio_clave_obligatorio: false });
      }
      if (ruta === "/api/v1/configuracion/permisos/secretaria") {
        return respuesta(200, { registros: true, control_documental: true, documentos: true, expedientes: true });
      }
      if (ruta === "/api/v1/documentos/capacidades") {
        return respuesta(200, { puede_retirar: true, puede_eliminar_definitivamente: true });
      }
      if (ruta === "/api/v1/documentos/resumen") {
        return respuesta(200, { total_documentos: 0, total_expedientes: 0, total_pen: 0, total_usd: 0 });
      }
      return respuesta(200, []);
    });

    await page.goto("/ingresar");
    await page.getByLabel("Espacio administrativo").fill("PRUEBAS");
    await page.getByLabel("Usuario o correo").fill(codigo);
    await page.getByLabel("Clave").fill("ClaveTemporal123!");
    await page.getByRole("button", { name: "Iniciar sesión" }).click();
    await page.goto("/documentos");

    const enlaceSubir = page.locator("nav a[href='/subir']");
    await expect(enlaceSubir).toBeVisible();
    await expect(page.locator("aside.menu")).toHaveClass(/menu-cerrado/);
    const posiciones = await page.evaluate(() => {
      const menu = document.querySelector("aside.menu");
      const enlace = document.querySelector("nav a[href='/subir']");
      if (!menu || !enlace) return null;
      menu.classList.remove("menu-abierto");
      menu.classList.add("menu-cerrado");
      const yCerrado = enlace.getBoundingClientRect().y;
      menu.classList.remove("menu-cerrado");
      menu.classList.add("menu-abierto");
      const yAbierto = enlace.getBoundingClientRect().y;
      return { yCerrado, yAbierto };
    });
    expect(posiciones).not.toBeNull();
    if (!posiciones) throw new Error("No se pudo medir el enlace Subir en ambos estados del menú");
    expect(Math.abs(posiciones.yAbierto - posiciones.yCerrado)).toBeLessThanOrEqual(1);
    await enlaceSubir.click();
    await expect(page).toHaveURL(/\/subir$/);
    await expect(page.getByRole("heading", { name: "Ingreso de documentos" })).toBeVisible();

    await page.goto("/documentos");
    await expect(page.locator("main a[href='/subir']")).toBeVisible();
    await page.locator("main a[href='/subir']").click();
    await expect(page).toHaveURL(/\/subir$/);
    await expect(page.getByRole("heading", { name: "Ingreso de documentos" })).toBeVisible();
  });
}
