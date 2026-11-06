// Renderiza las partes de un video de Código del Éxito con UN solo bundle. Los archivos del video (stock, Profesor, voz)
// se sirven desde su carpeta de trabajo con un servidor local (con rangos, para que el video se pueda adelantar).
// Uso: node scripts/partes.mjs <carpeta_trabajo> <partes.json> [concurrencia]
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
const [trabajo, lista, conc = "2"] = process.argv.slice(2);
const NUBE = "/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell";
const browserExecutable = fs.existsSync(NUBE) ? NUBE : null;
const tipos = { ".mp4": "video/mp4", ".wav": "audio/wav", ".mp3": "audio/mpeg", ".png": "image/png", ".jpg": "image/jpeg" };
const servidor = http.createServer((req, res) => {
  const ruta = path.join(trabajo, decodeURIComponent(req.url.split("?")[0]));
  if (!ruta.startsWith(path.resolve(trabajo)) || !fs.existsSync(ruta)) { res.writeHead(404); return res.end(); }
  const tam = fs.statSync(ruta).size, tipo = tipos[path.extname(ruta)] || "application/octet-stream";
  const rango = /bytes=(\d*)-(\d*)/.exec(req.headers.range || "");
  const cab = { "Content-Type": tipo, "Accept-Ranges": "bytes", "Access-Control-Allow-Origin": "*" };
  if (rango) {
    const a = rango[1] ? +rango[1] : 0, b = rango[2] ? +rango[2] : tam - 1;
    res.writeHead(206, { ...cab, "Content-Range": `bytes ${a}-${b}/${tam}`, "Content-Length": b - a + 1 });
    return fs.createReadStream(ruta, { start: a, end: b }).pipe(res);
  }
  res.writeHead(200, { ...cab, "Content-Length": tam });
  fs.createReadStream(ruta).pipe(res);
});
await new Promise((ok) => servidor.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${servidor.address().port}/`;
const conUrl = (x) => (typeof x === "string" && x.startsWith("@/") ? base + x.slice(2) : x);
const resolver = (o) => Array.isArray(o) ? o.map(resolver) : o && typeof o === "object" ? Object.fromEntries(Object.entries(o).map(([k, v]) => [k, resolver(v)])) : conUrl(o);
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), publicDir: path.resolve("public") });
for (const { nombre, props } of JSON.parse(fs.readFileSync(lista, "utf8"))) {
  const inputProps = resolver(props);
  const composition = await selectComposition({ serveUrl, id: "Parte", inputProps, browserExecutable, chromiumOptions: { gl: "angle" } });
  const t0 = Date.now();
  await renderMedia({ composition, serveUrl, codec: "h264", crf: 18, outputLocation: path.join(trabajo, "partes", nombre + ".mp4"), inputProps,
    browserExecutable, concurrency: Number(conc), muted: true, timeoutInMilliseconds: 180000 });
  console.log("ok", nombre, ((Date.now() - t0) / 1000).toFixed(0) + " s");
}
servidor.close();
