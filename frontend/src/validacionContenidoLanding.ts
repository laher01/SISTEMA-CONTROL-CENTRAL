import type { ContenidoLanding } from "./contenidoLanding";

/**
 * Validación editorial previa a guardar, previsualizar o publicar.
 * No otorga permisos, no publica y no interpreta HTML proporcionado por usuarios.
 */
export interface ErrorEditorial {
  campo: string;
  mensaje: string;
}

const LIMITES = {
  marca: 70,
  etiqueta: 120,
  titulo: 180,
  descripcion: 700,
  beneficiosTitulo: 180,
  planesTitulo: 160,
  planesDescripcion: 700,
  registroTitulo: 160,
  registroDescripcion: 700,
  beneficioTitulo: 140,
  beneficioDescripcion: 450,
} as const;

function validarTexto(campo: string, valor: unknown, maximo: number): ErrorEditorial[] {
  if (typeof valor !== "string" || valor.trim().length === 0) {
    return [{ campo, mensaje: "Campo obligatorio" }];
  }
  if (valor.trim().length > maximo) {
    return [{ campo, mensaje: `No superar ${maximo} caracteres` }];
  }
  if (/[<>\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(valor)) {
    return [{ campo, mensaje: "No se permite HTML ni caracteres de control" }];
  }
  return [];
}

export function validarContenidoLanding(entrada: unknown): ErrorEditorial[] {
  if (typeof entrada !== "object" || entrada === null || Array.isArray(entrada)) {
    return [{ campo: "contenido", mensaje: "Debe ser un objeto de contenido" }];
  }
  const contenido = entrada as Partial<ContenidoLanding>;
  const errores: ErrorEditorial[] = [];
  const simples: ReadonlyArray<[keyof typeof LIMITES, number]> = Object.entries(LIMITES)
    .filter(([nombre]) => !nombre.startsWith("beneficio"))
    .map(([nombre, limite]) => [nombre as keyof typeof LIMITES, limite]);
  for (const [campo, limite] of simples) {
    errores.push(...validarTexto(campo, contenido[campo as keyof ContenidoLanding], limite));
  }
  if (!Array.isArray(contenido.beneficios) || contenido.beneficios.length < 1 || contenido.beneficios.length > 8) {
    errores.push({ campo: "beneficios", mensaje: "Debe haber entre 1 y 8 beneficios" });
    return errores;
  }
  const ids = new Set<string>();
  for (const [indice, beneficio] of contenido.beneficios.entries()) {
    if (!beneficio || typeof beneficio !== "object") {
      errores.push({ campo: `beneficios[${indice}]`, mensaje: "Beneficio inválido" });
      continue;
    }
    const prefijo = `beneficios[${indice}]`;
    if (typeof beneficio.id !== "string" || !/^[a-z0-9-]{1,50}$/.test(beneficio.id)) {
      errores.push({ campo: `${prefijo}.id`, mensaje: "Identificador inválido" });
    } else if (ids.has(beneficio.id)) {
      errores.push({ campo: `${prefijo}.id`, mensaje: "Identificador repetido" });
    } else {
      ids.add(beneficio.id);
    }
    errores.push(...validarTexto(`${prefijo}.titulo`, beneficio.titulo, LIMITES.beneficioTitulo));
    errores.push(...validarTexto(`${prefijo}.descripcion`, beneficio.descripcion, LIMITES.beneficioDescripcion));
  }
  return errores;
}
