import React from 'react';
import {Composition} from 'remotion';
import {Short} from './Short';
import {TOTAL} from './timing';
import {ShortPantera} from './pantera/Short';
import {TOTAL as TOTAL_P} from './pantera/timing';
import {MapaColombia, TOTAL_COL} from './colombia/Mapa';
import {ShortDepartamentos} from './colombia/Short';
import {TOTAL as TOTAL_D} from './colombia/timing';
import {ShortTerror} from './terror/Short';
import {TOTAL as TOTAL_T} from './terror/timing';
import {ShortUsedTo} from './usedto/Short';
import {TOTAL as TOTAL_U} from './usedto/timing';
import {ShortEp5, totalEp5} from './pueblo/ep5';
export const Root: React.FC = () => (
  <>
    <Composition id="AvisponGigante" component={Short} durationInFrames={TOTAL} fps={30} width={1080} height={1920} />
    <Composition id="PanteraNegra" component={ShortPantera} durationInFrames={TOTAL_P} fps={30} width={1080} height={1920} />
    <Composition id="Departamentos" component={ShortDepartamentos} durationInFrames={TOTAL_D} fps={30} width={1080} height={1920} />
    <Composition id="DepartamentosPrevia" component={MapaColombia} durationInFrames={TOTAL_COL} fps={30} width={1080} height={1920} />
    <Composition id="TerrorNiebla" component={ShortTerror} durationInFrames={TOTAL_T} fps={30} width={1080} height={1920} />
    <Composition id="UsedToElevators" component={ShortUsedTo} durationInFrames={TOTAL_U} fps={30} width={1080} height={1920} />
    <Composition id="PuebloEp5Juguetes" component={ShortEp5} durationInFrames={totalEp5()} fps={30} width={1080} height={1920} />
  </>
);
