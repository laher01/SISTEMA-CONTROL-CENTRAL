import { useEffect, useState } from "react";

import { enviarJson, useDatos } from "../api";

type Apariencia = {
  tema: "CLARO" | "OSCURO" | "SISTEMA";
  color: "AZUL" | "VERDE" | "VIOLETA" | "GRIS" | "NARANJA";
  densidad: "COMPACTO" | "NORMAL" | "AMPLIO";
  barra: "AUTOMATICO" | "MANUAL";
};
const BASE: Apariencia = { tema: "CLARO", color: "AZUL", densidad: "NORMAL", barra: "AUTOMATICO" };
const COLORES: { codigo: Apariencia["color"]; hex: string; nombre: string }[] = [
  { codigo: "AZUL", hex: "#1c4e80", nombre: "Azul" },
  { codigo: "VERDE", hex: "#13795b", nombre: "Verde" },
  { codigo: "VIOLETA", hex: "#663399", nombre: "Violeta" },
  { codigo: "GRIS", hex: "#334155", nombre: "Gris" },
  { codigo: "NARANJA", hex: "#a64b00", nombre: "Naranja" },
];

function aplicar(preferencias: Apariencia): void {
  const html = document.documentElement;
  html.dataset.fcTema = preferencias.tema.toLowerCase();
  html.dataset.fcDensidad = preferencias.densidad.toLowerCase();
  html.style.setProperty("--primario", COLORES.find((x) => x.codigo === preferencias.color)?.hex ?? COLORES[0].hex);
}

export default function AparienciaPersonal({ onBarra }: { onBarra: (modo: Apariencia["barra"]) => void }) {
  const { datos, error, cargando, recargar } = useDatos<Apariencia>("/api/v1/auth/mi-apariencia");
  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState<Apariencia>(BASE);
  const [mensaje, setMensaje] = useState("");
  const [guardando, setGuardando] = useState(false);
  useEffect(() => {
    if (datos) {
      setForm(datos);
      aplicar(datos);
      onBarra(datos.barra);
    }
  }, [datos, onBarra]);
  useEffect(() => {
    return () => {
      document.documentElement.removeAttribute("data-fc-tema");
      document.documentElement.removeAttribute("data-fc-densidad");
      document.documentElement.style.removeProperty("--primario");
    };
  }, []);
  const guardar = async (actual: Apariencia) => {
    setGuardando(true);
    setMensaje("");
    try {
      await enviarJson<Apariencia>("/api/v1/auth/mi-apariencia", "PUT", actual);
      aplicar(actual);
      onBarra(actual.barra);
      setMensaje("Apariencia guardada en tu cuenta.");
      recargar();
    } catch (err) {
      setMensaje(err instanceof Error ? err.message : String(err));
    } finally {
      setGuardando(false);
    }
  };
  return <div className="apariencia-personal">
    <button type="button" aria-expanded={editando} aria-controls="fc-apariencia-panel"
      onClick={() => setEditando(!editando)}>⚙ Apariencia</button>
    {editando && <div id="fc-apariencia-panel" className="apariencia-panel">
      <strong>Personalización personal</strong>
      <small>Solo cambia tu cuenta, no los permisos ni la información de otros usuarios.</small>
      {cargando && <span>Cargando ajustes…</span>}
      {error && <span role="alert">{error}</span>}
      <label>Tema
        <select value={form.tema} onChange={(e) => setForm({ ...form, tema: e.target.value as Apariencia["tema"] })}>
          <option value="CLARO">Claro</option>
          <option value="OSCURO">Oscuro</option>
          <option value="SISTEMA">Según dispositivo</option>
        </select>
      </label>
      <label>Color principal
        <select value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value as Apariencia["color"] })}>
          {COLORES.map((x) => <option key={x.codigo} value={x.codigo}>{x.nombre}</option>)}
        </select>
      </label>
      <label>Tamaño de interfaz
        <select value={form.densidad} onChange={(e) => setForm({ ...form, densidad: e.target.value as Apariencia["densidad"] })}>
          <option value="COMPACTO">Compacto</option>
          <option value="NORMAL">Normal</option>
          <option value="AMPLIO">Amplio</option>
        </select>
      </label>
      <label>Barra lateral
        <select value={form.barra} onChange={(e) => setForm({ ...form, barra: e.target.value as Apariencia["barra"] })}>
          <option value="AUTOMATICO">Automática</option>
          <option value="MANUAL">Manual</option>
        </select>
      </label>
      <div className="apariencia-botones">
        <button type="button" disabled={guardando || cargando} onClick={() => void guardar(form)}>Guardar</button>
        <button type="button" disabled={guardando} onClick={() => { setForm(BASE); void guardar(BASE); }}>Restaurar</button>
      </div>
      {mensaje && <small role="status">{mensaje}</small>}
    </div>}
  </div>;
}
