// Renderiza clips de las plantillas con UN solo bundle. Uso: node scripts/clips.mjs <salida> <lista.json | '<json [{comp, nombre, props}]>'> [concurrencia] [escala]
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "node:path";
const [out, lista, conc = "2", escala = "1"] = process.argv.slice(2);
import fs from "node:fs";
// en la nube: el Chromium de /opt/pw-browsers sin tarjeta de video (swangle); en el PC (Windows): el que baja Remotion, con la tarjeta (angle)
const NUBE = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
const browserExecutable = fs.existsSync(NUBE) ? NUBE : null;
const chromiumOptions = { gl: process.env.PT_GL || (browserExecutable ? "swangle" : "angle") };
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
for (const { comp, nombre, props } of JSON.parse(lista.endsWith(".json") ? fs.readFileSync(lista, "utf8") : lista)) {
  const composition = await selectComposition({ serveUrl, id: comp, inputProps: props, browserExecutable, chromiumOptions });
  const t0 = Date.now();
  await renderMedia({ composition, serveUrl, codec: "h264", crf: 18, outputLocation: path.join(out, nombre + ".mp4"), inputProps: props,
    browserExecutable, chromiumOptions, concurrency: Number(conc), muted: true, onBrowserLog: (l) => { if (l.text.startsWith("[pt]")) console.log(l.text); }, scale: Number(escala), timeoutInMilliseconds: 120000 });
  console.log("ok", nombre, ((Date.now() - t0) / 1000).toFixed(0) + " s");
}
