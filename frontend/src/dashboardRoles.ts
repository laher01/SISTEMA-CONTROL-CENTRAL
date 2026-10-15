import type { SesionActual } from "./tipos";

export function controlesDashboard(rol: SesionActual["rol"]) {
  const administracion = ["SUPERADMIN", "ADMINISTRADOR", "GERENTE", "SECRETARIA"].includes(rol);
  return {
    responsable: administracion,
    usuario: administracion || rol === "RESPONSABLE",
    gestor: administracion || rol === "RESPONSABLE" || rol === "USUARIO",
  };
}

export function agrupacionInicial(rol: SesionActual["rol"]) {
  if (rol === "GESTOR") return "receptor";
  if (rol === "USUARIO") return "gestor";
  return "usuario";
}
