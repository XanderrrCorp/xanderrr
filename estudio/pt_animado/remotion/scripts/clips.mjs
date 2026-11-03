// Renderiza clips de las plantillas con UN solo bundle. Uso: node scripts/clips.mjs <salida> '<json [{comp, nombre, props}]>' [concurrencia]
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "node:path";
const [out, lista, conc = "2"] = process.argv.slice(2);
const browserExecutable = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
const chromiumOptions = { gl: "swangle" };
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
for (const { comp, nombre, props } of JSON.parse(lista)) {
  const composition = await selectComposition({ serveUrl, id: comp, inputProps: props, browserExecutable, chromiumOptions });
  const t0 = Date.now();
  await renderMedia({ composition, serveUrl, codec: "h264", crf: 18, outputLocation: path.join(out, nombre + ".mp4"), inputProps: props,
    browserExecutable, chromiumOptions, concurrency: Number(conc), muted: true, timeoutInMilliseconds: 120000 });
  console.log("ok", nombre, ((Date.now() - t0) / 1000).toFixed(0) + " s");
}
