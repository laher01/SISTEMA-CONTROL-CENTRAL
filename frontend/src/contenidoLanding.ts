/** Contrato público tipado. En la siguiente fase será alimentado por el CMS aprobado. */
export interface BeneficioComercial {
  id: string;
  titulo: string;
  descripcion: string;
}
export interface ContenidoLanding {
  marca: string;
  etiqueta: string;
  titulo: string;
  descripcion: string;
  beneficiosTitulo: string;
  beneficios: BeneficioComercial[];
  planesTitulo: string;
  planesDescripcion: string;
  registroTitulo: string;
  registroDescripcion: string;
}
/** Fuente segura actual: texto aprobado y comprobable, sin datos privados ni precios inventados. */
export const contenidoLandingInicial: Readonly<ContenidoLanding> = {
  marca: "FACT CENTRAL",
  etiqueta: "GESTIÓN DOCUMENTAL TRIBUTARIA",
  titulo: "De documentos dispersos a expedientes digitales organizados.",
  descripcion: "FACT CENTRAL reúne comprobantes, guías y sustentos de compras para facilitar el control documental, el seguimiento y la revisión administrativa.",
  beneficiosTitulo: "Un solo lugar para controlar la documentación de compras",
  beneficios: [
    { id: "documentos", titulo: "Documentos", descripcion: "Organiza archivos PDF, imágenes y comprobantes por operación y empresa." },
    { id: "expedientes", titulo: "Expedientes", descripcion: "Relaciona facturas, guías y evidencias para facilitar su revisión." },
    { id: "trazabilidad", titulo: "Control y trazabilidad", descripcion: "Consulta registros, estados y permisos según el perfil autorizado." },
  ],
  planesTitulo: "Planes del servicio",
  planesDescripcion: "Los planes y sus tarifas se publicarán cuando estén aprobados. No se realizan cobros desde esta página.",
  registroTitulo: "Registro y acceso",
  registroDescripcion: "La creación de cuentas se realiza con autorización de cada administración. El formulario de solicitud de acceso aparece en la pantalla de ingreso solo cuando su administración lo tiene habilitado.",
};
