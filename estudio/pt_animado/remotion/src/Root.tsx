import React from "react";
import { Composition } from "remotion";
import { HojaPersonaje } from "./HojaPersonaje";
import { FotoEscenario, PropsFoto } from "./FotosEscenarios";
import { Intro, Encuentro, Transicion, Cierre, PropsPlantilla, metadatos } from "./Plantillas";

const fotoDef: PropsFoto = { escenario: "finca", luz: "dia" };
const plantillaDef: PropsPlantilla = { escenario: "finca", luz: "dia", animal: "prueba", formato: "16:9", claves: {} };
export const Root: React.FC = () => (
  <>
    <Composition id="HojaPersonaje" component={HojaPersonaje} durationInFrames={1} fps={30} width={1920} height={1080} />
    <Composition id="Foto" component={FotoEscenario} durationInFrames={30} fps={30} width={1920} height={1080} defaultProps={fotoDef} />
    <Composition id="FotoVertical" component={FotoEscenario} durationInFrames={30} fps={30} width={1080} height={1920} defaultProps={fotoDef} />
    <Composition id="Intro" component={Intro} fps={30} width={1920} height={1080} durationInFrames={300} defaultProps={plantillaDef} calculateMetadata={metadatos("intro")} />
    <Composition id="Encuentro" component={Encuentro} fps={30} width={1920} height={1080} durationInFrames={240} defaultProps={plantillaDef} calculateMetadata={metadatos("encuentro")} />
    <Composition id="Transicion" component={Transicion} fps={30} width={1920} height={1080} durationInFrames={120} defaultProps={plantillaDef} calculateMetadata={metadatos("transicion")} />
    <Composition id="Cierre" component={Cierre} fps={30} width={1920} height={1080} durationInFrames={360} defaultProps={plantillaDef} calculateMetadata={metadatos("cierre")} />
  </>
);
