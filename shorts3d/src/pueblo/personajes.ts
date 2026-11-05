// El reparto FIJO del canal: mismos colores y accesorios en los 6 videos (consistencia entre episodios).
import type {Ropa} from './Personaje';
export const DON_BRUNO: Ropa = {piel: '#f2c9a0', camisa: '#2b3a67', pantalon: '#1e2233', zapatos: '#111', bigote: '#4a2c17', barriga: true, banda: '#d62828', sombrero: {tipo: 'copa', color: '#1a1a1a', cinta: '#d62828'}};
export const NINOS: Record<string, Ropa> = {
  teo: {piel: '#f5cfa6', camisa: '#2ec4b6', pantalon: '#264653', pelo: '#3b2414', mochila: '#ff9f1c'},
  mia: {piel: '#e9b98f', camisa: '#ff70a6', pantalon: '#5e60ce', pelo: '#1d1d1d', coletas: true, pijama: false},
  lucas: {piel: '#f2c49b', camisa: '#ffbe0b', pantalon: '#3a86ff', pelo: '#7a4a1e', sombrero: {tipo: 'gorra', color: '#e63946'}},
  sofi: {piel: '#d9a679', camisa: '#8338ec', pantalon: '#22223b', pelo: '#2b1a0e', coletas: true, bufanda: '#ffd60a'},
  max: {piel: '#f3cba5', camisa: '#3a86ff', pantalon: '#283618', pelo: '#c47a2c', sombrero: {tipo: 'gorro', color: '#e63946', cinta: '#fff'}},
  leo: {piel: '#e8b48a', camisa: '#06d6a0', pantalon: '#3d405b', pelo: '#2a1b10', bufanda: '#ef476f'},
};
export const EXTRAS: Record<string, Ropa> = {
  papa: {piel: '#efc29a', camisa: '#6a994e', pantalon: '#3d3d3d', pelo: '#3a2615'},
  mama: {piel: '#e7b58c', camisa: '#e76f51', pantalon: '#264653', pelo: '#5a2d0c', falda: '#264653'},
  abuela: {piel: '#f1d1b2', camisa: '#9d4edd', pantalon: '#5a189a', pelo: '#e5e5e5', falda: '#5a189a', lentes: true},
  panadero: {piel: '#f0c39b', camisa: '#ffffff', pantalon: '#6c757d', delantal: '#f1f1f1', sombrero: {tipo: 'panadero', color: '#ffffff'}},
  cartero: {piel: '#e5b38a', camisa: '#457b9d', pantalon: '#1d3557', mochila: '#a8763e', sombrero: {tipo: 'gorra', color: '#1d3557'}},
  profe: {piel: '#f4c7a1', camisa: '#e9c46a', pantalon: '#5c4d7d', pelo: '#222', lentes: true},
  vecino: {piel: '#d99e74', camisa: '#f4a261', pantalon: '#2a9d8f', pelo: '#111', sombrero: {tipo: 'boina', color: '#2a9d8f'}},
  nino: {piel: '#f1c8a0', camisa: '#ffd166', pantalon: '#118ab2', pelo: '#4a2a12'},
};
