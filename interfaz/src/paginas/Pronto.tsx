import { useParams } from 'react-router-dom';
import { Icono } from '../componentes/Icono';

const QUE: Record<string, [string, string]> = {
  personaje: ['Asistente de personaje', 'Crea un presentador o una mascota fija que se ve igual en todos los videos. Es lo siguiente que se construye.'],
  personajes: ['Tus personajes', 'Aquí quedarán los personajes de tus canales.'],
  estilo: ['Asistente de estilo', 'Crea un estilo visual desde tus referencias o miniaturas públicas de YouTube.'],
  estilos: ['Tus estilos', 'Aquí quedarán tus estilos visuales.'],
  formato: ['Crear formato', 'Junta guion, estilo y edición en un formato propio.'],
  ideas: ['Ideas de videos', 'Temas sugeridos para tus canales.'],
};

export function Pronto() {
  const { que = '' } = useParams();
  const [titulo, texto] = QUE[que] ?? ['Pronto', 'Esta sección llega en las próximas fases.'];
  return (
    <div className="pagina pronto-pagina">
      <Icono nombre="chispa" tam={40} />
      <h1>{titulo}</h1>
      <p className="tenue">{texto}</p>
      <span className="etiqueta">En construcción</span>
    </div>
  );
}
