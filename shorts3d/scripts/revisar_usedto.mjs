// Empaqueta revisar_usedto.ts con esbuild (viene con Remotion) y lo corre.
import {build} from 'esbuild';
import {execFileSync} from 'child_process';
import path from 'path';
const out = path.resolve('out/.revisar_usedto.cjs');
await build({entryPoints: ['scripts/revisar_usedto.ts'], bundle: true, platform: 'node', format: 'cjs', outfile: out, jsx: 'automatic', logLevel: 'error'});
try { execFileSync('node', [out], {stdio: 'inherit'}); } catch (e) { process.exit(e.status ?? 1); }
