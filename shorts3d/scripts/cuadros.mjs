// Saca cuadros sueltos (PNG) para revisar a ojo: node scripts/cuadros.mjs 20,70,110
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'path';
const frames = process.argv[2].split(',').map(Number);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public')});
import fs from 'fs';
// en la nube se usa el Chromium ya instalado; en el PC, el que baja Remotion solo
const NUBE = '/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell';
const browserExecutable = fs.existsSync(NUBE) ? NUBE : null;
const chromiumOptions = {gl: 'swangle'};
const composition = await selectComposition({serveUrl, id: process.env.COMP || 'AvisponGigante', browserExecutable, chromiumOptions, timeoutInMilliseconds: 300000});
for (const f of frames) {
  const t = Date.now();
  await renderStill({serveUrl, composition, frame: f, output: `out/${process.argv[3] || 'cuadros'}/c${String(f).padStart(4, '0')}.png`, browserExecutable, chromiumOptions, timeoutInMilliseconds: 300000});
  console.log('cuadro', f, ((Date.now() - t) / 1000).toFixed(1) + ' s');
}
