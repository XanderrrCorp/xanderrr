// Íconos de trazo propios (24×24), sin librerías.
const TRAZOS: Record<string, string> = {
  inicio: 'M3 11.5 12 4l9 7.5M5.5 10v9.5h5v-5h3v5h5V10',
  video: 'M4 5.5h11v13H4zM15 10l5-3v10l-5-3',
  short: 'M8 3h8a1.5 1.5 0 0 1 1.5 1.5v15A1.5 1.5 0 0 1 16 21H8a1.5 1.5 0 0 1-1.5-1.5v-15A1.5 1.5 0 0 1 8 3zM11 18h2',
  miniatura: 'M3.5 5h17v14h-17zM3.5 15l5-4.5 4 3.5 3-2.5 5 4',
  personaje: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20.5c1.2-3.8 4-5.5 7.5-5.5s6.3 1.7 7.5 5.5',
  estilo: 'M12 3.5a8.5 8.5 0 1 0 0 17c1.4 0 1.8-1 1.3-2-.7-1.3.2-2.5 1.6-2.5H17a3.5 3.5 0 0 0 3.5-3.5c0-5-3.8-9-8.5-9zM7.5 11.5h.01M10 7.5h.01M14.5 7.5h.01',
  formatos: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  videos: 'M3.5 6h17v12h-17zM10 9.5l4.5 2.5-4.5 2.5z',
  canal: 'M5 19a10 10 0 0 1 0-14M19 5a10 10 0 0 1 0 14M8.2 15.8a5.5 5.5 0 0 1 0-7.6M15.8 8.2a5.5 5.5 0 0 1 0 7.6M12 12h.01',
  sonidos: 'M9 18V6l11-2v12M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
  ideas: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z',
  explorar: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM15.5 8.5l-2 5-5 2 2-5z',
  planes: 'M4 8l4 3 4-6 4 6 4-3-2 10H6z',
  admin: 'M12 3l7 3v5c0 4.5-3 8.3-7 10-4-1.7-7-5.5-7-10V6z',
  ajustes: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 13a7.5 7.5 0 0 0 0-2l2-1.6-2-3.4-2.4 1a7.5 7.5 0 0 0-1.7-1L15 3.5h-4l-.4 2.5a7.5 7.5 0 0 0-1.7 1l-2.4-1-2 3.4 2 1.6a7.5 7.5 0 0 0 0 2l-2 1.6 2 3.4 2.4-1c.5.4 1.1.8 1.7 1l.4 2.5h4l.4-2.5c.6-.2 1.2-.6 1.7-1l2.4 1 2-3.4z',
  chispa: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z',
  flecha: 'M5 12h14M13 6l6 6-6 6',
  menu: 'M4 7h16M4 12h16M4 17h16',
  cerrar: 'M6 6l12 12M18 6 6 18',
  ok: 'M5 12.5l4.5 4.5L19 7.5',
  candado: 'M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 0 1 7 0v3',
};

export function Icono({ nombre, tam = 20 }: { nombre: string; tam?: number }) {
  return (
    <svg width={tam} height={tam} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={TRAZOS[nombre] ?? TRAZOS.chispa} />
    </svg>
  );
}
