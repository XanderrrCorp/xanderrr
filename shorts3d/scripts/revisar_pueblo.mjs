// Empaqueta revisar_pueblo.ts con esbuild (viene con Remotion) y lo corre.
import {build} from 'esbuild';
import {execFileSync} from 'child_process';
import path from 'path';
const out = path.resolve('out/.revisar_pueblo.cjs');
await build({entryPoints: ['scripts/revisar_pueblo.ts'], bundle: true, platform: 'node', format: 'cjs', outfile: out, jsx: 'automatic', logLevel: 'error', loader: {'.ttf': 'empty', '.png': 'empty'}});
try { execFileSync('node', [out], {stdio: 'inherit'}); } catch (e) { process.exit(e.status ?? 1); }
