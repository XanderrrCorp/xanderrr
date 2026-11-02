// Montserrat ExtraBold (SIL Open Font License), cargada antes del primer cuadro: la usan los subtítulos y la placa.
import {continueRender, delayRender} from 'remotion';
import montserrat from './fuentes/Montserrat-ExtraBold.ttf';
export const FUENTE = 'Montserrat, "Arial Black", sans-serif';
export const fuenteLista: Promise<void> = typeof document === 'undefined' ? Promise.resolve() : (() => {
  const espera = delayRender('Montserrat');
  const ff = new FontFace('Montserrat', `url(${montserrat})`, {weight: '800'});
  return ff.load().then((f) => { document.fonts.add(f); continueRender(espera); }).catch(() => continueRender(espera));
})();
