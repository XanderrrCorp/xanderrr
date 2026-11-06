import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { Parte, PropsParte } from "./Parte";

const def: PropsParte = { fps: 30, bloques: [{ tipo: "aura", dur: 5 }], subtitulos: [], audio: null, inicio: 0, cola: 0 };
const medidas: CalculateMetadataFunction<PropsParte> = ({ props }) => ({
  durationInFrames: Math.max(1, props.bloques.reduce((a, b) => a + Math.round(b.dur * 30), 0) + props.cola),
});
export const Root: React.FC = () => (
  <Composition id="Parte" component={Parte} fps={30} width={1920} height={1080} durationInFrames={150} defaultProps={def} calculateMetadata={medidas} />
);
