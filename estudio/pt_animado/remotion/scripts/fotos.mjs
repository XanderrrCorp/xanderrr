// Renderiza varias fotos (stills) con UN solo bundle. Uso: node scripts/fotos.mjs <salida> <comp> '<json lista de props>' [frame]
import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";
import path from "node:path";
const [out, comp, lista, frame = "0"] = process.argv.slice(2);
const browserExecutable = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
for (const { _frame, ...props } of JSON.parse(lista)) {
  const composition = await selectComposition({ serveUrl, id: comp, inputProps: props, browserExecutable, chromiumOptions: { gl: "swangle" } });
  const nombre = path.join(out, [comp, props.escenario, props.luz, props.formato ?? "", _frame ?? frame].join("_") + ".png");
  await renderStill({ composition, serveUrl, output: nombre, inputProps: props, frame: Number(_frame ?? frame), browserExecutable, chromiumOptions: { gl: "swangle" } });
  console.log("ok", nombre);
}
