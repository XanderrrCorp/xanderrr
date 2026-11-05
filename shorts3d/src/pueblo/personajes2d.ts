// El reparto FIJO en 2D (episodios 2, 6 y 4), dibujado con el sistema de la skill. Mismos colores que en 3D.
import type {Outfit} from './look/toon';
const INK = '#241726';
export const BRUNO_2D: Outfit = {jacket: '#2b3a67', pants: '#1e2233', boots: INK, hat: 'tophat', moustache: '#4a2c17', sash: '#d62828', build: 'stout', buttons: '#e8c45a', skin: '#f5c9a0'};
export const NINOS_2D: Record<string, Outfit> = {
  mia: {jacket: '#ff70a6', pants: '#5e60ce', boots: '#f4f1ea', hat: 'hair', hair: '#1d1d1d', build: 'kid', skin: '#ecd0b6', dress: '#ff70a6'},
  leo: {jacket: '#06d6a0', pants: '#3d405b', boots: '#5a3b2a', hat: 'hair', hair: '#2a1b10', build: 'kid', skin: '#f5c9a0'},
  dani: {jacket: '#ffbe0b', pants: '#3a86ff', boots: '#f4f1ea', hat: 'cap', cap: '#e63946', build: 'kid', skin: '#c99067'},
  sofi: {jacket: '#8338ec', pants: '#22223b', boots: '#5a3b2a', hat: 'hair', hair: '#2b1a0e', build: 'kid', skin: '#c99067', dress: '#8338ec'},
  ana: {jacket: '#f15bb5', pants: '#3b5b9a', boots: '#f4f1ea', hat: 'cap', cap: '#00bbf9', build: 'kid', skin: '#ffe2c2'},
  nino: {jacket: '#f08a2c', pants: '#3b5b9a', boots: '#f4f1ea', hat: 'cap', cap: '#e2453c', build: 'kid', skin: '#ffe2c2'},
};
export const EXTRAS_2D: Record<string, Outfit> = {
  papa: {jacket: '#6a994e', pants: '#3d3d3d', boots: '#4a3426', hat: 'hair', hair: '#3a2615', skin: '#f5c9a0'},
  mama: {jacket: '#e76f51', pants: '#264653', boots: '#4a3426', hat: 'hair', hair: '#5a2d0c', dress: '#e76f51', skin: '#ecd0b6'},
  vecino: {jacket: '#f4a261', pants: '#2a9d8f', boots: '#4a3426', hat: 'tophat', skin: '#c99067'},
  vecina: {jacket: '#9d4edd', pants: '#5a189a', boots: '#4a3426', hat: 'bonnet', dress: '#9d4edd', skin: '#ffe2c2'},
  panadero: {jacket: '#f1f1f1', pants: '#6c757d', boots: '#4a3426', hat: 'hair', hair: '#4a2c17', skin: '#f5c9a0', moustache: '#4a2c17'},
  hermano: {jacket: '#5a7a9a', pants: '#2b2d42', boots: INK, hat: 'tophat', moustache: '#6b6b6b', build: 'stout', skin: '#f5c9a0'},
};
