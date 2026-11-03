import React from "react";
import { Composition } from "remotion";
import { HojaPersonaje } from "./HojaPersonaje";
import { FotoEscenario, PropsFoto } from "./FotosEscenarios";

const fotoDef: PropsFoto = { escenario: "finca", luz: "dia" };
export const Root: React.FC = () => (
  <>
    <Composition id="HojaPersonaje" component={HojaPersonaje} durationInFrames={1} fps={30} width={1920} height={1080} />
    <Composition id="Foto" component={FotoEscenario} durationInFrames={30} fps={30} width={1920} height={1080} defaultProps={fotoDef} />
    <Composition id="FotoVertical" component={FotoEscenario} durationInFrames={30} fps={30} width={1080} height={1920} defaultProps={fotoDef} />
  </>
);
