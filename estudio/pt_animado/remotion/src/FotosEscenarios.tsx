// Fase 2: una foto de cada escenario con el explorador en cada luz (inputProps: escenario, luz, formato).
import React from "react";
import { useVideoConfig } from "remotion";
import { Toma, Plan } from "./pt/Toma";
import { construir, NombreEscenario } from "./pt/escenarios";
import { NombreLuz } from "./pt/luces";
import { Expr } from "./pt/toon";

export type PropsFoto = { escenario: NombreEscenario; luz: NombreLuz; expr?: Expr; vista?: "frente" | "lado" };

export const FotoEscenario: React.FC<PropsFoto> = ({ escenario, luz, expr = "smile", vista = "frente" }) => {
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  const base = React.useMemo(() => construir(escenario).cam, [escenario]); // solo la cámara base (el mundo lo arma Toma)
  const plan: Plan = (f) => {
    const push = 1 - f * 0.002;
    const pos: [number, number, number] = [base.pos[0], base.pos[1], base.look[2] + (base.pos[2] - base.look[2]) * push * (vertical ? 1.25 : 1)];
    return {
      cam: { pos, look: base.look, fov: vertical ? base.fov * 1.45 : base.fov }, t: f / 30, frio: 0,
      actor: { x: -0.4, z: 0, vista, expr, fase: 0.1, modo: vista === "lado" ? "march" : "stand", parpadeo: 0 },
      animal: { x: 1.9, z: -0.6, alto: 0.9, visible: 1 },
      dof: { cInf: 6 },
    };
  };
  return <Toma escenario={escenario} luz={luz} plan={plan} animal="prueba" />;
};
