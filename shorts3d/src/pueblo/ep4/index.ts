import guion from './guion.json';
import vo from './vo.json';
import {ESCENAS} from './escenas';
import type {Episodio, Guion} from '../tipos';
import {crearShort} from '../ShortPueblo';
import {montar} from '../montaje';
export const EP4: Episodio = {id: 'ep4', guion: guion as unknown as Guion, escenas: ESCENAS, vo: vo as Record<string, unknown>, carpetaAudio: 'pueblo/ep4'};
export const ShortEp4 = crearShort(EP4);
export const totalEp4 = () => montar(EP4).TOTAL;
