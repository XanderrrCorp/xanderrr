import guion from './guion.json';
import vo from './vo.json';
import {ESCENAS} from './escenas';
import type {Episodio, Guion} from '../tipos';
import {crearShort} from '../ShortPueblo';
import {montar} from '../montaje';
export const EP1: Episodio = {id: 'ep1', guion: guion as unknown as Guion, escenas: ESCENAS, vo: vo as Record<string, unknown>, carpetaAudio: 'pueblo/ep1'};
export const ShortEp1 = crearShort(EP1);
export const totalEp1 = () => montar(EP1).TOTAL;
