import guion from './guion.json';
import vo from './vo.json';
import {ESCENAS} from './escenas';
import type {Episodio, Guion} from '../tipos';
import {crearShort} from '../ShortPueblo';
import {montar} from '../montaje';
export const EP2: Episodio = {id: 'ep2', guion: guion as unknown as Guion, escenas: ESCENAS, vo: vo as Record<string, unknown>, carpetaAudio: 'pueblo/ep2'};
export const ShortEp2 = crearShort(EP2);
export const totalEp2 = () => montar(EP2).TOTAL;
