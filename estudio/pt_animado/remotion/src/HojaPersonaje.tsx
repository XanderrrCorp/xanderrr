// Hoja de prueba del explorador: 14 caras de frente + 8 cuadros del caminado de lado (solo para revisar el dibujo).
import React, { useEffect, useRef } from "react";
import { AbsoluteFill } from "remotion";
import { Pen, bodyFront, bodySide, EXPLORADOR, Expr } from "./pt/toon";

const CARAS: Expr[] = ["neutral", "stern", "grin", "laugh", "whistle", "nervous", "shock", "relief", "relief_open", "dazed", "pained", "smile", "smile_closed", "lick"];

export const HojaPersonaje: React.FC = () => {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const g = ref.current!.getContext("2d")!;
    g.fillStyle = "#e9efe4"; g.fillRect(0, 0, 1920, 1080);
    const p = new Pen(g);
    CARAS.forEach((e, i) => {
      g.save(); g.translate(20 + (i % 7) * 270, (i < 7 ? 0 : 1) * 330 + 10); g.scale(0.32, 0.32);
      bodyFront(p, EXPLORADOR, { expr: e, mode: "stand", seed: 3 });
      g.restore();
      g.fillStyle = "#333"; g.font = "20px sans-serif"; g.fillText(e, 60 + (i % 7) * 270, (i < 7 ? 330 : 660));
    });
    for (let k = 0; k < 8; k++) {
      g.save(); g.translate(20 + k * 235, 690); g.scale(0.38, 0.38);
      bodySide(p, EXPLORADOR, { phase: k / 8, mode: "march", stride: 0.7, stomp: 0.8, seed: 3 });
      g.restore();
    }
  }, []);
  return <AbsoluteFill><canvas ref={ref} width={1920} height={1080} /></AbsoluteFill>;
};
