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
    <p class="tenue">Escribe solo el tema. Xandart elige el giro y el villano, escribe el guion, hace las imágenes, graba la voz y monta el video.</p>
    ${faltan.length ? `<div class="error">Falta configurar ${faltan.join(', ')}. Abre <b>⚙ Ajustes</b>.</div>` : ''}
    <section class="tarjeta" style="margin-top:16px">
      <h2>Nuevo video</h2>
      <label>Tema</label>
      <input id="n-tema" placeholder="Del insecto más asqueroso de tu casa al que te pica la cara mientras duermes">
      <details class="opcional"><summary>Giro y villano <span class="tenue">(opcional: si los dejas vacíos, los elige la IA)</span></summary>
      <label>Giro</label>
      <textarea id="n-giro" placeholder="Vacío = la IA propone el giro más fuerte y verdadero"></textarea>
      <label>Villano (el más peligroso, al final)</label>
      <textarea id="n-villano" placeholder="Vacío = la IA elige el más peligroso y verdadero"></textarea>
      </details>
      <label>Duración: <span id="n-min-v">9</span> minutos</label>
      <input id="n-min" type="range" min="8" max="11" step="0.5" value="9" oninput="$('#n-min-v').textContent=this.value">
      <label>Notas (opcional)</label>
      <input id="n-notas" placeholder="Algo que quieras que tenga el guion">
      <div class="fila fin"><button class="primario" onclick="crear()">Escribir el guion</button></div>
      <p class="tenue" style="font-size:13px">El guion lo escribe Claude con tu suscripción: no cuesta nada extra. Antes de gastar en imágenes te muestra el costo.</p>
    </section>
    <section class="tarjeta" style="margin-top:16px">
      <h2>¿Ya tienes un guion?</h2>
      <p class="tenue">Sube un <b>escenas.json</b> o el <b>.zip</b> que lo tenga (por ejemplo video_alacranes.zip). No cuesta nada: después eliges si probar 10 escenas o hacer todas.</p>
      <div class="fila"><input id="i-archivo" type="file" accept=".json,.zip,application/json,application/zip">
      <button onclick="importar()">Importar</button></div>
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

async function importar() {
  const f = $('#i-archivo').files[0];
  if (!f) return alert('Escoge el archivo escenas.json o el .zip');
  const datos = new FormData(); datos.append('archivo', f);
  const r = await fetch('/api/importar', { method: 'POST', body: datos });
  const v = await r.json().catch(() => ({}));
  if (!r.ok) return alert(v.detail || `Error ${r.status}`);
  if (v.avisos && v.avisos.length) alert('Importado. Avisos:\n- ' + v.avisos.slice(0, 8).join('\n- '));
  abrir(v.slug);
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
        ${e.pasa_maximo ? `<div class="error">Ojo: todas las imágenes de este guion (${e.faltan}) pasan del máximo de ${esc(e.maximo_texto)} por video. Xandart se frena al llegar al máximo y te pide permiso para seguir. Para bajar el costo, que más escenas reutilicen imágenes.</div>` : ''}
        ${pruebaHtml(v)}
        <div class="fila"><button class="primario" onclick="accion('imagenes')">Aprobar y hacer las imágenes (${e.faltan} imágenes ≈ ${esc(e.texto)})</button>
        ${e.prueba ? `<button onclick="accion('prueba')">Probar primero 10 escenas (${e.prueba} imágenes ≈ ${esc(e.prueba_texto)})</button>` : ''}
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

function pruebaHtml(v) {
  const p = v.prueba;
  if (!p) return '';
  return `<div class="tarjeta" style="margin:12px 0">
    <b>Prueba real: primeras ${p.escenas} escenas</b>
    ${p.hoja ? `<a href="/archivos/${v.slug}/${p.hoja}" target="_blank"><img style="width:100%;border-radius:10px;margin:8px 0" src="/archivos/${v.slug}/${p.hoja}?v=${Date.now() % 100000}" alt="Hoja de contacto"></a>` : ''}
    <div>Costo real de la prueba: <b>${esc(p.costo_corrida)}</b>${p.costo_medio_imagen ? ` · por imagen: <b>${esc(p.costo_medio_imagen)}</b>` : ''}</div>
    ${p.proyeccion ? `<div>Todas las imágenes del video (${p.proyeccion.imagenes}): <b>≈ ${esc(p.proyeccion.texto)}</b> <span class="tenue">(${esc(p.proyeccion.base)})</span></div>` : ''}
    <div class="tenue" style="font-size:13px">${esc(p.proveedor)} · ${esc(p.modelo)} · ${p.generadas} nuevas, ${p.ya_estaban} ya estaban, ${p.llamadas} llamadas pagadas</div>
  </div>`;
}

function nombrePaso(p) {
  return { guion: 'Escribiendo el guion', imagenes: 'Haciendo las imágenes', video: 'Haciendo el video', regenerar: 'Regenerando una imagen', prueba: 'Probando las primeras 10 escenas' }[p] || p;
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

/* ------------------------------------------------------------ biblioteca de audio */
const NOMBRES_AUDIO = {
  golpe_grave: 'Golpe grave · giros y revelación', pop: 'Pop · cuando entra un dato clave',
  barrido: 'Barrido (whoosh) · cambios de sección', latido: 'Latido · ráfagas de tensión',
  subida_tension: 'Subida de tensión · antes de la revelación', zumbido: 'Zumbido grave · amenaza',
  alerta: 'Alerta corta · advertencias', comico: 'Cómico · humor',
  tension: 'Tensión', misterio: 'Misterio', epico: 'Épico', alivio: 'Alivio', curiosidad: 'Curiosidad', final: 'Final',
};
let BIB = null;

async function irBiblioteca() {
  clearInterval(SONDEO); ACTUAL = null; location.hash = 'sonidos';
  BIB = await api('/api/biblioteca');
  const fila = (clase, t) => {
    const n = BIB.cuenta[`${clase}:${t}`] || 0;
    return `<div class="fila-audio"><span>${esc(NOMBRES_AUDIO[t] || t)}</span>
      <span class="chip ${n >= 3 ? 'ok' : n ? 'aviso' : ''}">${n ? n + (n === 1 ? ' archivo' : ' archivos') : 'falta'}</span></div>`;
  };
  const opciones = (lista) => lista.map(t => `<option value="${t}">${esc(NOMBRES_AUDIO[t] || t)}</option>`).join('');
  app.innerHTML = `
    <div class="fila"><button class="fantasma mini" onclick="irInicio()">‹ Tus videos</button></div>
    <h1>Música y efectos de sonido</h1>
    <p class="tenue">Xandart no descarga audio por su cuenta. Tú bajas los archivos de una fuente con licencia
      (por ejemplo la <b>Biblioteca de audio de YouTube</b>, en YouTube Studio → Biblioteca de audio) y aquí los registras
      con su fuente y su licencia. Mientras falte un tipo, el video usa un sonido provisional.</p>
    <div class="rejilla dos">
      <section class="tarjeta"><h2>Efectos</h2>${BIB.tipos_sfx.map(t => fila('sfx', t)).join('')}
        <p class="tenue" style="font-size:13px">Ideal: 3 o 4 variantes de cada uno, para que no se repita el mismo sonido.</p></section>
      <section class="tarjeta"><h2>Música (por estado de ánimo)</h2>${BIB.animos_musica.map(t => fila('musica', t)).join('')}</section>
    </div>
    <section class="tarjeta" style="margin-top:16px">
      <h2>Agregar archivos</h2>
      <label>Archivos (.mp3, .wav…) · puedes escoger varios del mismo tipo</label>
      <input id="b-archivos" type="file" multiple accept=".wav,.mp3,.ogg,.flac,.m4a,.aac,audio/*">
      <div class="rejilla dos">
        <div><label>Es</label><select id="b-clase" onchange="tiposAudio()"><option value="sfx">Efecto de sonido</option><option value="musica">Música</option></select></div>
        <div><label>Tipo</label><select id="b-tipo">${opciones(BIB.tipos_sfx)}</select></div>
      </div>
      <label>¿De dónde sale? (enlace o nombre de la fuente)</label>
      <input id="b-fuente" placeholder="YouTube Studio · Biblioteca de audio">
      <label>Licencia</label>
      <select id="b-licencia" onchange="camposLicencia()">${Object.entries(BIB.licencias).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select>
      <div id="b-extra"></div>
      <div class="fila fin"><button class="primario" onclick="subirAudios()">Registrar</button></div>
      <p class="tenue" style="font-size:13px">También puedes soltar archivos en la carpeta de entrada
        <button class="mini" onclick="api('/api/biblioteca/abrir-entrada',{method:'POST'})">Abrir carpeta</button>
        y registrarlos aquí abajo con estos mismos datos.</p>
      ${BIB.entrada.length ? `<div class="entrada">${BIB.entrada.map(n => `<div class="fila-audio"><span>${esc(n)}</span>
        <button class="mini" onclick="registrarEntrada('${esc(n).replace(/'/g, "\\'")}')">Registrar con estos datos</button></div>`).join('')}</div>` : ''}
    </section>
    <h2 style="margin-top:24px">Registrados (${BIB.archivos.length})</h2>
    <div class="lista-audio">${BIB.archivos.map(a => `
      <div class="tarjeta audio-item">
        <div><b>${esc(NOMBRES_AUDIO[a.tipo] || a.tipo)}</b> <span class="tenue">· ${esc(a.nombre_original)}</span>
          ${a.revisar_licencia ? '<span class="chip aviso">licencia por revisar: no se usa</span>' : ''}</div>
        <audio controls preload="none" src="/api/biblioteca/${a.huella}/escuchar"></audio>
        <div class="tenue" style="font-size:13px">${esc(BIB.licencias[a.licencia] || a.licencia)}${a.detalle_licencia ? ' · ' + esc(a.detalle_licencia) : ''}
          · fuente: ${esc(a.fuente)}${a.atribucion ? ' · atribución: «' + esc(a.atribucion) + '»' : ''}</div>
        <div class="fila fin"><button class="mini fantasma" onclick="borrarAudio('${a.huella}')">Quitar</button></div>
      </div>`).join('') || '<p class="tenue">Todavía no hay archivos.</p>'}</div>`;
  camposLicencia();
}

function tiposAudio() {
  const lista = $('#b-clase').value === 'sfx' ? BIB.tipos_sfx : BIB.animos_musica;
  $('#b-tipo').innerHTML = lista.map(t => `<option value="${t}">${esc(NOMBRES_AUDIO[t] || t)}</option>`).join('');
}

function camposLicencia() {
  const l = $('#b-licencia').value;
  let html = '';
  if (l === 'otra') html += '<label>Detalle de la licencia</label><input id="b-detalle" placeholder="Qué dice la licencia y dónde está">';
  if (l === 'cc_by' || l === 'youtube_audio_library_atribucion')
    html += '<label>Texto de atribución (va en la descripción del video)</label><input id="b-atribucion" placeholder="Música: Título de Autor (licencia)">';
  $('#b-extra').innerHTML = html;
}

function datosAudio() {
  return { clase: $('#b-clase').value, tipo: $('#b-tipo').value, fuente: $('#b-fuente').value.trim(),
    licencia: $('#b-licencia').value, detalle_licencia: ($('#b-detalle') || {}).value || '',
    atribucion: ($('#b-atribucion') || {}).value || '' };
}

async function subirAudios() {
  const archivos = [...$('#b-archivos').files];
  if (!archivos.length) return alert('Escoge uno o más archivos');
  const d = datosAudio();
  const errores = [];
  for (const f of archivos) {
    const fd = new FormData();
    fd.append('archivo', f);
    Object.entries(d).forEach(([k, v]) => fd.append(k, v));
    const r = await fetch('/api/biblioteca', { method: 'POST', body: fd });
    if (!r.ok) errores.push(`${f.name}: ${(await r.json().catch(() => ({}))).detail || r.status}`);
  }
  if (errores.length) alert('No se registraron:\n' + errores.join('\n'));
  irBiblioteca();
}

async function registrarEntrada(nombre) {
  try { await api('/api/biblioteca/entrada', { method: 'POST', cuerpo: { nombre, ...datosAudio() } }); irBiblioteca(); }
  catch (e) { alert(e.message); }
}

async function borrarAudio(huella) {
  if (!confirm('¿Quitar este archivo de la biblioteca?')) return;
  await api(`/api/biblioteca/${huella}`, { method: 'DELETE' });
  irBiblioteca();
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

(location.hash === '#sonidos' ? irBiblioteca()
  : location.hash.length > 1 ? (async () => { ESTADO = await api('/api/estado'); abrir(location.hash.slice(1)); })() : irInicio());
