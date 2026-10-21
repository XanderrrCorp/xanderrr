import {
  ArrowRight, Check, Clapperboard, Compass, Crown, Film, Folder, House, Image, LayoutGrid, LayoutTemplate,
  Lightbulb, ListVideo, Lock, Menu, Music, Palette, Radio, Settings, Shield, Smartphone, Smile, Sparkles,
  SwatchBook, Users, X, type LucideIcon,
} from 'lucide-react';

// Íconos de Lucide con los nombres de siempre (las páginas piden «video», «ok»…; aquí se traducen).
const ICONOS: Record<string, LucideIcon> = {
  inicio: House, video: Clapperboard, short: Smartphone, miniatura: LayoutTemplate, personaje: Smile,
  personajes: Users, estilo: Palette, estilos: SwatchBook, formatos: LayoutGrid, videos: ListVideo, proyectos: Folder,
  media: Film, canal: Radio, sonidos: Music, ideas: Lightbulb, explorar: Compass, planes: Crown, admin: Shield,
  ajustes: Settings, chispa: Sparkles, flecha: ArrowRight, menu: Menu, cerrar: X, ok: Check, candado: Lock,
  imagen: Image,
};

export function Icono({ nombre, tam = 20 }: { nombre: string; tam?: number }) {
  const C = ICONOS[nombre] ?? Sparkles;
  return <C size={tam} strokeWidth={1.8} aria-hidden="true" />;
}
