import React from 'react';
import {Composition} from 'remotion';
import {Short} from './Short';
import {TOTAL} from './timing';
import {ShortPantera} from './pantera/Short';
import {TOTAL as TOTAL_P} from './pantera/timing';
import {MapaColombia, TOTAL_COL} from './colombia/Mapa';
import {ShortDepartamentos} from './colombia/Short';
import {TOTAL as TOTAL_D} from './colombia/timing';
export const Root: React.FC = () => (
  <>
    <Composition id="AvisponGigante" component={Short} durationInFrames={TOTAL} fps={30} width={1080} height={1920} />
    <Composition id="PanteraNegra" component={ShortPantera} durationInFrames={TOTAL_P} fps={30} width={1080} height={1920} />
    <Composition id="Departamentos" component={ShortDepartamentos} durationInFrames={TOTAL_D} fps={30} width={1080} height={1920} />
    <Composition id="DepartamentosPrevia" component={MapaColombia} durationInFrames={TOTAL_COL} fps={30} width={1080} height={1920} />
  </>
);
