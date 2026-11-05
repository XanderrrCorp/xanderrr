import guion from './guion.json';
import vo from './vo.json';
import {ESCENAS} from './escenas';
import type {Episodio, Guion} from '../tipos';
import {crearShort} from '../ShortPueblo';
import {montar} from '../montaje';
export const EP5: Episodio = {id: 'ep5', guion: guion as unknown as Guion, escenas: ESCENAS, vo: vo as Record<string, unknown>, carpetaAudio: 'pueblo/ep5'};
export const ShortEp5 = crearShort(EP5);
export const totalEp5 = () => montar(EP5).TOTAL;
