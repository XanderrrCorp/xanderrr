import guion from './guion.json';
import vo from './vo.json';
import {ESCENAS} from './escenas';
import type {Episodio, Guion} from '../tipos';
import {crearShort} from '../ShortPueblo';
import {montar} from '../montaje';
export const EP6: Episodio = {id: 'ep6', guion: guion as unknown as Guion, escenas: ESCENAS, vo: vo as Record<string, unknown>, carpetaAudio: 'pueblo/ep6'};
export const ShortEp6 = crearShort(EP6);
export const totalEp6 = () => montar(EP6).TOTAL;
