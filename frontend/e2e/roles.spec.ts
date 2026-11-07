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


for (const rol of ["ADMINISTRADOR", "GERENTE", "SECRETARIA", "RESPONSABLE", "USUARIO", "GESTOR"]) {
  test(`${rol}: meses legibles y gráficos siguen filtros, orden y vista móvil`, async ({ page }) => {
    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      const mes = url.searchParams.get("mes");
      const cantidad = mes === "2026-12" ? 0 : mes ? 3 : 5;
      const monto = String(cantidad * 100);
      const json = (body: unknown) => route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
      if (url.pathname === "/api/v1/auth/me") return json({
        rol, codigo: "PRUEBA01", nombre: "Cuenta de prueba", cambio_clave_obligatorio: false,
        jerarquia: [], es_administracion_demo: false,
      });
      if (url.pathname === "/api/v1/dashboard/opciones") return json({ responsables: [], usuarios: [], gestores: [], emisores: [], receptores: [] });
      if (url.pathname === "/api/v1/dashboard/resumen") return json({
        expedientes_total: cantidad, por_estado: { VERDE: cantidad, AMARILLO: 0, NARANJA: 0, ROJO: 0 },
        pendientes_aprobacion: 0, documentos_pendientes: {}, alertas_abiertas: {},
        montos: [{ moneda: "PEN", bancarizable: monto, no_bancarizable: "0", con_agente_retencion: "0", sin_agente_retencion: monto,
          cantidad_bancarizable: cantidad, cantidad_no_bancarizable: 0, cantidad_con_agente_retencion: 0, cantidad_sin_agente_retencion: cantidad }],
      });
      if (url.pathname === "/api/v1/dashboard/desglose") {
        const septiembre = { clave: "2026-09", etiqueta: "09/2026", ruc: null, expedientes: 3, total_pen: "300", total_usd: "0" };
        const agosto = { clave: "2026-08", etiqueta: "08/2026", ruc: null, expedientes: 2, total_pen: "200", total_usd: "0" };
        const filas = cantidad === 0 ? [] : mes ? [septiembre] : url.searchParams.get("orden") === "asc" ? [agosto, septiembre] : [septiembre, agosto];
        return json({ agrupar_por: url.searchParams.get("agrupar_por"), filas });
      }
      return route.fulfill({ status: 403, contentType: "application/json", body: JSON.stringify({ detail: "Fuera del alcance de esta prueba aislada" }) });
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/");
    await page.getByLabel("Agrupar por", { exact: true }).selectOption("mes");
    const cantidades = page.getByRole("region", { name: "Gráfico de vista ordenada", exact: true });
    const montos = page.getByRole("region", { name: "Gráfico de montos", exact: true });
    await expect(cantidades.getByRole("listitem").first()).toContainText("Septiembre/2026");
    await page.getByLabel("Orden", { exact: true }).selectOption("asc");
    await expect(cantidades.getByRole("listitem").first()).toContainText("Agosto/2026");
    await page.getByLabel("Año del mes", { exact: true }).fill("2026");
    await page.getByLabel("Mes de emisión", { exact: true }).selectOption("09");
    await expect(page.getByLabel("Mes de emisión", { exact: true }).locator("option:checked")).toHaveText("Septiembre/2026");
    await expect(cantidades.getByRole("listitem")).toHaveCount(1);
    await expect(cantidades).toContainText("Septiembre/2026");
    await expect(montos).toContainText("S/ 300.00");
    const escritorio = await cantidades.boundingBox();
    const junto = await montos.boundingBox();
    expect(junto!.x).toBeGreaterThan(escritorio!.x);
    await page.setViewportSize({ width: 390, height: 844 });
    const movil = await cantidades.boundingBox();
    const debajo = await montos.boundingBox();
    expect(debajo!.y).toBeGreaterThan(movil!.y);
    await page.getByLabel("Mes de emisión", { exact: true }).selectOption("12");
    await expect(cantidades).toContainText("Sin datos para los filtros seleccionados.");
    await expect(montos).toContainText("S/ 0.00");
    await page.getByRole("button", { name: "Limpiar filtros", exact: true }).click();
    await expect(cantidades.getByRole("listitem")).toHaveCount(2);
    await expect(montos).toContainText("S/ 500.00");
  });
}
