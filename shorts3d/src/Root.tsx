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
import {BridgeShort, BRIDGE_FRAMES} from './skill_cartoon/bridge/Bridge';
import {ShortEp2, totalEp2} from './pueblo/ep2';
import {ShortEp1, totalEp1} from './pueblo/ep1';
import {ShortEp6, totalEp6} from './pueblo/ep6';
import {ShortEp3, totalEp3} from './pueblo/ep3';
import {ShortEp4, totalEp4} from './pueblo/ep4';
export const Root: React.FC = () => (
  <>
    <Composition id="AvisponGigante" component={Short} durationInFrames={TOTAL} fps={30} width={1080} height={1920} />
    <Composition id="PanteraNegra" component={ShortPantera} durationInFrames={TOTAL_P} fps={30} width={1080} height={1920} />
    <Composition id="Departamentos" component={ShortDepartamentos} durationInFrames={TOTAL_D} fps={30} width={1080} height={1920} />
    <Composition id="DepartamentosPrevia" component={MapaColombia} durationInFrames={TOTAL_COL} fps={30} width={1080} height={1920} />
    <Composition id="TerrorNiebla" component={ShortTerror} durationInFrames={TOTAL_T} fps={30} width={1080} height={1920} />
    <Composition id="UsedToElevators" component={ShortUsedTo} durationInFrames={TOTAL_U} fps={30} width={1080} height={1920} />
    <Composition id="PuebloEp5Juguetes" component={ShortEp5} durationInFrames={totalEp5()} fps={30} width={1080} height={1920} />
    <Composition id="SkillPuente" component={BridgeShort} durationInFrames={BRIDGE_FRAMES} fps={30} width={1080} height={1920} />
    <Composition id="PuebloEp2Criatura" component={ShortEp2} durationInFrames={totalEp2()} fps={30} width={1080} height={1920} />
    <Composition id="PuebloEp1Invisible" component={ShortEp1} durationInFrames={totalEp1()} fps={30} width={1080} height={1920} />
    <Composition id="PuebloEp6Rompes" component={ShortEp6} durationInFrames={totalEp6()} fps={30} width={1080} height={1920} />
    <Composition id="PuebloEp3Sombra" component={ShortEp3} durationInFrames={totalEp3()} fps={30} width={1080} height={1920} />
    <Composition id="PuebloEp4Mentiras" component={ShortEp4} durationInFrames={totalEp4()} fps={30} width={1080} height={1920} />
  </>
);
