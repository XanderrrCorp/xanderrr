/* Xandart · página local. Sin dependencias: se edita y se recarga. */
const $ = s => document.querySelector(s);
const app = $('#app');
let ESTADO = null, ACTUAL = null, SONDEO = null;

async function api(ruta, opciones = {}) {
  const r = await fetch(ruta, { headers: { 'Content-Type': 'application/json' }, ...opciones,
    body: opciones.cuerpo ? JSON.stringify(opciones.cuerpo) : undefined });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.detail || `Error ${r.status}`);
  return datos;
}
const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

/* ------------------------------------------------------------ inicio */
async function irInicio() {
  clearInterval(SONDEO); ACTUAL = null; location.hash = '';
  ESTADO = await api('/api/estado');
  const faltan = [];
  if (!ESTADO.claves.together) faltan.push('la clave de Together');
  if (!ESTADO.claves.minimax) faltan.push('la clave de MiniMax');
  if (!ESTADO.claude) faltan.push('Claude');
  app.innerHTML = `
    <h1>De una idea a un video que engancha</h1>
    <p class="tenue">Escribe el tema, el giro y el villano. Xandart escribe el guion, hace las imágenes, graba la voz y monta el video.</p>
    ${faltan.length ? `<div class="error">Falta configurar ${faltan.join(', ')}. Abre <b>⚙ Ajustes</b>.</div>` : ''}
    <section class="tarjeta" style="margin-top:16px">
      <h2>Nuevo video</h2>
      <label>Tema</label>
      <input id="n-tema" placeholder="Del insecto más asqueroso de tu casa al que te pica la cara mientras duermes">
      <label>Giro</label>
      <textarea id="n-giro" placeholder="La cucaracha da asco pero es de lo menos peligroso"></textarea>
      <label>Villano (el más peligroso, al final)</label>
      <textarea id="n-villano" placeholder="La chinche besucona: pica de noche cerca de la boca y puede transmitir el mal de Chagas"></textarea>
      <label>Duración: <span id="n-min-v">9</span> minutos</label>
      <input id="n-min" type="range" min="8" max="11" step="0.5" value="9" oninput="$('#n-min-v').textContent=this.value">
      <label>Notas (opcional)</label>
      <input id="n-notas" placeholder="Algo que quieras que tenga el guion">
      <div class="fila fin"><button class="primario" onclick="crear()">Escribir el guion</button></div>
      <p class="tenue" style="font-size:13px">El guion lo escribe Claude con tu suscripción: no cuesta nada extra. Antes de gastar en imágenes te muestra el costo.</p>
    </section>
    <h2 style="margin-top:28px">Tus videos</h2>
    <div class="rejilla">${ESTADO.videos.map(v => `
      <div class="tarjeta video-item" onclick="abrir('${v.slug}')">
        <b>${esc(v.titulo)}</b>
        <div class="fila">${chipPasos(v.pasos, v.video)}<span class="chip">${esc(v.costo)}</span></div>
      </div>`).join('') || '<p class="tenue">Todavía no hay videos.</p>'}</div>`;
}

function chipPasos(p, video) {
  if (video) return '<span class="chip ok">video listo</span>';
  if (p.assets === 'completo') return '<span class="chip aviso">imágenes listas</span>';
  if (p.guionista === 'completo') return '<span class="chip aviso">guion listo</span>';
  return '<span class="chip">empezando</span>';
}

async function crear() {
  const cuerpo = { tema: $('#n-tema').value.trim(), giro: $('#n-giro').value.trim(),
    villano: $('#n-villano').value.trim(), minutos: parseFloat($('#n-min').value), notas: $('#n-notas').value.trim() };
  if (cuerpo.tema.length < 3) return alert('Escribe el tema del video');
  try { const v = await api('/api/videos', { method: 'POST', cuerpo }); abrir(v.slug); }
  catch (e) { alert(e.message); }
}

/* ------------------------------------------------------------ un video */
async function abrir(slug) {
  ACTUAL = slug; location.hash = slug;
  await pintar();
  clearInterval(SONDEO);
  SONDEO = setInterval(async () => {
    const t = ACTUAL && window.__ultimo && window.__ultimo.trabajo;
    if (t && t.activo) await pintar();
  }, 2000);
}

async function pintar() {
  const v = await api(`/api/videos/${ACTUAL}`);
  const antes = window.__ultimo;
  window.__ultimo = v;
  const t = v.trabajo;
  const guionOk = v.pasos.guionista === 'completo', imgOk = v.pasos.assets === 'completo', vidOk = !!v.video;
  const enCurso = t && t.activo;
  const paso = (n, nombre, hecho, actual) =>
    `<div class="paso ${hecho ? 'hecho' : ''} ${actual ? 'actual' : ''}"><span class="tenue">Paso ${n}</span><b>${nombre}${hecho ? ' ✓' : ''}</b></div>`;
  let cuerpo = '';
  if (enCurso) {
    cuerpo = `<section class="tarjeta"><b>${esc(nombrePaso(t.paso))}</b>
      <div class="barra"><i style="width:${Math.round(t.progreso * 100)}%"></i></div>
      <span class="tenue">${esc(t.mensaje)} · ${Math.floor(t.segundos / 60)} min ${t.segundos % 60} s</span></section>`;
  } else if (t && t.error) {
    cuerpo = `<div class="error">No se pudo terminar «${esc(nombrePaso(t.paso))}»: ${esc(t.error)}</div>`;
  }
  if (vidOk && !enCurso) {
    cuerpo += `<section class="tarjeta"><h2>Tu video está listo</h2>
      <video controls preload="metadata" src="/archivos/${v.slug}/${v.video}"></video>
      <div class="fila">
        <a href="/archivos/${v.slug}/${v.video}?descargar=true"><button class="primario">Descargar MP4 (1080p)</button></a>
        <a href="/archivos/${v.slug}/render/final.srt?descargar=true"><button>Subtítulos (SRT)</button></a>
        <button onclick="api('/api/abrir-carpeta',{method:'POST'})">Abrir carpeta de videos</button>
      </div>
      <p class="tenue" style="font-size:13px">También quedó guardado en tu carpeta Videos › Xandart.</p></section>`;
  }
  if (guionOk && !enCurso) {
    const e = v.estimacion_imagenes || {};
    if (!imgOk) {
      cuerpo += `<section class="tarjeta"><h2>Revisa el guion</h2>
        <p class="tenue">Puedes cambiar el texto de cualquier escena tocándolo. Cuando te guste, aprueba y se hacen las imágenes.</p>
        <div class="fila"><button class="primario" onclick="accion('imagenes')">Aprobar y hacer las imágenes (${e.faltan} imágenes ≈ ${esc(e.texto)})</button>
        <button onclick="if(confirm('¿Escribir otro guion desde cero?')) accion('guion')">Escribir otro guion</button></div></section>`;
    } else if (!vidOk) {
      cuerpo += `<section class="tarjeta"><h2>Revisa las imágenes</h2>
        <p class="tenue">Si alguna no te gusta, dale «Regenerar» (≈ 125 pesos). Cuando todo esté bien, haz el video.</p>
        <div class="fila"><button class="primario" onclick="accion('video')">Hacer el video</button>
        ${e.faltan ? `<button onclick="accion('imagenes')">Completar imágenes que faltan (${e.faltan})</button>` : ''}</div></section>`;
    } else {
      cuerpo += `<div class="fila"><button onclick="accion('video')">Volver a montar el video</button></div>`;
    }
    cuerpo += escenasHtml(v, imgOk);
  }
  app.innerHTML = `
    <div class="fila"><button class="fantasma mini" onclick="irInicio()">‹ Tus videos</button><span class="crece"></span><span class="chip">Gastado: ${esc(v.costo)}</span></div>
    <h1>${esc(v.titulo)}</h1>
    <div class="pasos">${paso(1, 'Guion', guionOk, !guionOk)}${paso(2, 'Imágenes', imgOk, guionOk && !imgOk)}${paso(3, 'Video', vidOk, imgOk && !vidOk)}</div>
    ${cuerpo}`;
  if (antes && antes.trabajo && antes.trabajo.activo && !(t && t.activo) && !t.error) {
    /* terminó un paso: aviso discreto */
    document.title = 'Xandart · listo';
  }
}

function nombrePaso(p) {
  return { guion: 'Escribiendo el guion', imagenes: 'Haciendo las imágenes', video: 'Haciendo el video', regenerar: 'Regenerando una imagen' }[p] || p;
}

function escenasHtml(v, conImagenes) {
  let html = '<div class="escenas">', seccion = null;
  for (const e of v.escenas) {
    if (e.seccion !== seccion) { html += `<div class="seccion">${esc(e.seccion)}</div>`; seccion = e.seccion; }
    const img = e.imagen ? `<img loading="lazy" src="/archivos/${v.slug}/${e.imagen}?v=${Date.now() % 100000}" alt="">`
      : `<div class="sinimg">${e.accion === 'generar' ? (conImagenes ? 'sin imagen' : 'imagen pendiente') : e.accion === 'componer' ? 'tira de niveles' : 'reutiliza otra imagen'}</div>`;
    html += `<div class="escena">${img}<div class="cuerpo"><span class="num">Escena ${e.id}${e.medico ? ' · revisar dato de salud' : ''}</span>
      <div contenteditable="${!conImagenes}" onblur="guardarTexto(${e.id}, this.innerText)">${esc(e.narracion)}</div>
      ${conImagenes && e.puede_regenerar ? `<div class="fila"><button class="mini" onclick="regenerar(${e.id})">Regenerar</button></div>` : ''}</div></div>`;
  }
  return html + '</div>';
}

async function guardarTexto(id, texto) {
  texto = texto.trim();
  const e = window.__ultimo.escenas.find(x => x.id === id);
  if (!texto || !e || e.narracion === texto) return;
  await api(`/api/videos/${ACTUAL}/escenas/${id}`, { method: 'PUT', cuerpo: { narracion: texto } });
  e.narracion = texto;
}

async function accion(que, cuerpo = {}) {
  try { await api(`/api/videos/${ACTUAL}/${que}`, { method: 'POST', cuerpo }); await pintar(); }
  catch (e) {
    if (/máximo|FRENO|tope/.test(e.message) && confirm(e.message + '\n\n¿Das permiso para seguir?')) {
      return accion(que, { permiso: true });
    }
    alert(e.message);
  }
}

async function regenerar(id) {
  const instruccion = prompt('¿Qué quieres cambiar? (déjalo vacío para otra versión igual)', '');
  if (instruccion === null) return;
  await accion(`escenas/${id}/regenerar`, { instruccion });
}

/* ------------------------------------------------------------ ajustes */
function abrirAjustes() {
  const c = (ESTADO && ESTADO.claves) || {};
  $('#e-together').textContent = c.together ? 'guardada' : 'falta';
  $('#e-minimax').textContent = c.minimax ? 'guardada' : 'falta';
  $('#e-claude').textContent = ESTADO && ESTADO.claude ? 'instalado' : 'no instalado';
  $('#ajustes').showModal();
}
async function guardarClaves() {
  ESTADO = await api('/api/claves', { method: 'POST', cuerpo: { together: $('#k-together').value, minimax: $('#k-minimax').value } });
  $('#k-together').value = $('#k-minimax').value = '';
  abrirAjustes();
}
async function probar(servicio) {
  const el = $('#e-' + servicio);
  el.textContent = 'probando…';
  const r = await api(`/api/probar/${servicio}`, { method: 'POST' });
  el.textContent = r.ok ? '✓ funciona' : '✗ ' + r.detalle;
}
async function sesionClaude() {
  try { await api('/api/claude/sesion', { method: 'POST' }); alert('Se abrió una ventana de Claude: sigue los pasos para iniciar sesión y luego ciérrala.'); }
  catch (e) { alert(e.message); }
}

(location.hash.length > 1 ? (async () => { ESTADO = await api('/api/estado'); abrir(location.hash.slice(1)); })() : irInicio());
