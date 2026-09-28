/* Xandart · producción de miniaturas de formato escala (2x3). */
let MINI = null, MINI_SEL = 0, MINI_SONDEO = null, MINI_V = Date.now();

async function irMiniatura(slug) {
  clearInterval(SONDEO); clearInterval(MINI_SONDEO);
  ACTUAL = slug; location.hash = 'mini/' + slug;
  await pintarMini();
  MINI_SONDEO = setInterval(async () => {
    if (MINI && MINI.trabajo && MINI.trabajo.activo) await pintarMini();
  }, 2000);
}

const miniApi = (ruta, op = {}) => api(`/api/videos/${ACTUAL}/miniatura${ruta}`, op);
const archivoMini = r => `/archivos/${ACTUAL}/${r}?v=${MINI_V}`;

async function pintarMini() {
  const antes = MINI && MINI.trabajo && MINI.trabajo.activo;
  MINI = await miniApi('');
  if (antes && !(MINI.trabajo && MINI.trabajo.activo)) MINI_V = Date.now();
  const t = MINI.trabajo, p = MINI.plan, enCurso = t && t.activo;
  let html = `<div class="fila"><button class="fantasma mini" onclick="abrir('${ACTUAL}')">‹ Volver al video</button>
    <span class="crece"></span><span class="chip">Miniaturas: ${esc(MINI.gastado)}</span></div>
    <h1>Miniatura</h1>
    <p class="tenue">Claude la planifica, Gemini dibuja cada animal por separado y Xandart la arma con fuentes reales:
      el layout y los textos siempre salen perfectos.</p>`;
  if (enCurso) {
    html += `<section class="tarjeta"><b>${esc(t.mensaje)}</b>
      <div class="barra"><i style="width:${Math.round(t.progreso * 100)}%"></i></div>
      <span class="tenue">${Math.floor(t.segundos / 60)} min ${t.segundos % 60} s</span></section>`;
  } else if (t && t.error) {
    const freno = /máximo|permiso/.test(t.error);
    html += `<div class="error">No se pudo terminar: ${esc(t.error)}
      ${freno ? `<div class="fila"><button onclick="miniReintentarConPermiso('${t.paso}')">Dar permiso y seguir</button></div>` : ''}</div>`;
  }
  if (!MINI.miniatura && !enCurso) {
    html += `<section class="tarjeta" style="margin-top:14px"><h2>Hacer la miniatura</h2>
      <p>${esc(MINI.estimacion.texto)}</p>
      <div class="fila"><button class="primario" onclick="miniProducir()">Producir miniatura</button></div></section>`;
  }
  if (MINI.miniatura) html += miniVistaHtml(p) + (enCurso ? '' : miniPanelHtml(p));
  if (MINI.qa) html += miniQaHtml(MINI.qa);
  html += miniPlantillaHtml(MINI.plantilla);
  app.innerHTML = html;
  miniActivarArrastre();
}

function miniVistaHtml(p) {
  const m = MINI.mapa || { sujetos: [] };
  const cajas = m.sujetos.map(s => {
    const [x0, y0, x1, y1] = s.caja;
    return `<div class="mini-caja ${s.indice === MINI_SEL ? 'sel' : ''}" title="${esc(p.cells[s.indice].name)}"
      style="left:${x0 / 12.8}%;top:${y0 / 7.2}%;width:${(x1 - x0) / 12.8}%;height:${(y1 - y0) / 7.2}%"
      onclick="MINI_SEL=${s.indice};pintarMini()"></div>`;
  }).join('');
  return `<section class="tarjeta" style="margin-top:14px">
    <div class="mini-grande"><img src="${archivoMini(MINI.miniatura)}" alt="Miniatura">${cajas}</div>
    <div class="fila" style="align-items:flex-end;margin-top:14px">
      <div><div class="tenue" style="font-size:13px">Así se ve en el feed del celular</div>
        <img class="mini-feed" src="${archivoMini(MINI.feed)}" alt=""></div>
      <div><div class="tenue" style="font-size:13px">En videos sugeridos</div>
        <img class="mini-sugerido" src="${archivoMini(MINI.feed)}" alt=""></div>
      <span class="crece"></span>
      <a href="/archivos/${ACTUAL}/${MINI.miniatura}?descargar=true"><button class="primario">Descargar JPG (1280x720)</button></a>
    </div>
    <p class="tenue" style="font-size:13px">Toca un animal para editarlo. Arrastra las fichas de abajo para cambiar el orden
      (el primero es el protagonista).</p>
    <div class="mini-orden">${p.cells.map((c, i) => `
      <div class="mini-ficha ${i === MINI_SEL ? 'sel' : ''}" draggable="true" data-i="${i}" onclick="MINI_SEL=${i};pintarMini()">
        ${c.archivo ? `<img src="${archivoMini(MINI.carpeta + '/' + c.archivo)}" alt="">` : '<div class="sinimg">sin imagen</div>'}
        <span>${i + 1}. ${esc(c.label)}${c.is_hero ? ' ★' : ''}</span></div>`).join('')}</div>
  </section>`;
}

function miniPanelHtml(p) {
  const c = p.cells[MINI_SEL], i = MINI_SEL, a = c.ajuste;
  const variantes = c.variantes.map(v => `<img class="mini-var ${v === c.archivo ? 'sel' : ''}"
      src="${archivoMini(MINI.carpeta + '/' + v)}" onclick="miniElegir(${i}, '${esc(v)}')" title="Usar esta">`).join('');
  const iconos = MINI.iconos.map(n => `<option ${n === p.hero_icon ? 'selected' : ''}>${n}</option>`).join('');
  return `<section class="tarjeta" style="margin-top:14px">
    <h2>${i + 1}. ${esc(c.name)} ${c.is_hero ? '<span class="chip aviso">protagonista</span>' : ''}</h2>
    ${c.is_hero ? `
      <label>Texto del protagonista (rojo, 2 a 5 palabras)</label>
      <input id="m-hero" value="${esc(p.hero_text)}" maxlength="40">
      <div class="rejilla dos">
        <div><label>Ícono</label><select id="m-icono">${iconos}</select></div>
        <div><label>Color del aura</label><input id="m-aura" type="color" value="${p.hero_glow_color}"></div>
      </div>
      <label style="font-weight:400"><input type="checkbox" id="m-censura" ${p.hero_censor ? 'checked' : ''} style="width:auto">
        Herida censurada (pixelada) en el protagonista</label>`
    : `<label>Etiqueta (máximo 20 letras)</label><input id="m-label" value="${esc(c.label)}" maxlength="20">`}
    <label>Tamaño: <span id="m-esc-v">${a.escala.toFixed(2)}</span></label>
    <input id="m-esc" type="range" min="0.4" max="2.5" step="0.05" value="${a.escala}"
      oninput="$('#m-esc-v').textContent=(+this.value).toFixed(2)">
    <div class="fila"><span class="tenue">Mover:</span>
      <button class="mini" onclick="miniMover(0,-12)">↑</button><button class="mini" onclick="miniMover(0,12)">↓</button>
      <button class="mini" onclick="miniMover(-12,0)">←</button><button class="mini" onclick="miniMover(12,0)">→</button>
      <button class="mini fantasma" onclick="miniAjuste({escala:1,dx:0,dy:0})">Restablecer</button>
      <span class="crece"></span><button class="primario" onclick="miniGuardar()">Aplicar cambios</button></div>
    <p class="tenue" style="font-size:13px">Los textos, el ícono, el aura, el orden, el tamaño y la posición no gastan nada: solo se vuelve a armar.</p>
    <h2 style="margin-top:18px">Imagen</h2>
    <div class="mini-variantes">${variantes}</div>
    <label>¿Cómo debe verse? (opcional)</label>
    <input id="m-instr" placeholder="Ej.: con la boca más abierta, de frente, más amenazante">
    <div class="fila">
      <button onclick="miniRegenerar(${i})">Regenerar (≈ ${esc(MINI.estimacion.por_imagen_usd)} USD)</button>
      ${c.is_hero ? `<button onclick="miniVariantes()">Crear 2 variantes para elegir</button>` : ''}
      <button class="fantasma" onclick="miniReferencia(${i})">Usar como referencia de estilo</button>
    </div>
  </section>`;
}

function miniMedidasHtml(m) {
  if (!m) return '';
  const ok = v => v ? '<span class="chip ok">bien</span>' : '<span class="chip aviso">revisar</span>';
  return `<ul class="mini-medidas">
    <li>Protagonista: <b>${m.protagonista_vs_mayor ?? '—'}×</b> el más grande de los otros (mínimo 1,3×) ${ok(m.protagonista_ok)}</li>
    <li>Encimado máximo entre dos sujetos: <b>${Math.round((m.solape_max || 0) * 100)} %</b> (máximo 5 %) ${ok(m.solape_ok)}</li>
    <li>Ícono libre (sin tocar a nadie): <b>${m.icono_libre ? 'sí' : 'no'}</b> ${ok(m.icono_libre)}</li>
    <li>Cabezas sin cortar por arriba ${ok(m.cabeza_sin_cortar)}</li></ul>`;
}

function miniQaHtml(qa) {
  const r = qa.rondas[qa.rondas.length - 1];
  const filas = Object.entries(r.sujetos).filter(([, s]) => !s.ok || s.problemas.length).map(([k, s]) =>
    `<li><b>${+k + 1}. ${esc(MINI.plan.cells[+k] ? MINI.plan.cells[+k].name : '')}</b>: ${esc(s.problemas.join('; ') || 'revisar')}</li>`).join('');
  return `<section class="tarjeta" style="margin-top:14px"><h2>Control de calidad
    <span class="chip ${qa.aprobada ? 'ok' : 'aviso'}">${qa.aprobada ? 'aprobada' : 'con observaciones'}</span></h2>
    <p>${esc(r.resumen || '')}</p>${filas ? `<ul>${filas}</ul>` : '<p class="tenue">Sin problemas.</p>'}
    <b>Medidas del armado (por código)</b>${miniMedidasHtml((MINI.mapa && MINI.mapa.medidas) || r.medidas)}
    <p class="tenue" style="font-size:13px">${qa.rondas.length} ronda(s) de revisión · cada sujeto se regenera como mucho 2 veces.</p></section>`;
}

function miniPlantillaHtml(pl) {
  const refs = pl.referencias.map(r => `<div class="mini-ref ${r.activa ? '' : 'apagada'}">
      <img src="/canales/${pl.canal}/referencias/${encodeURIComponent(r.archivo)}?v=${MINI_V}" alt="">
      <div class="fila"><label style="margin:0;font-weight:400"><input type="checkbox" style="width:auto" ${r.activa ? 'checked' : ''}
        onchange="miniRefActiva('${esc(r.archivo)}', this.checked)"> usar</label>
      <span class="crece"></span><button class="mini fantasma" onclick="miniRefBorrar('${esc(r.archivo)}')">Borrar</button></div></div>`).join('');
  return `<section class="tarjeta" style="margin-top:14px"><h2>Plantilla del canal · ${esc(pl.nombre)}</h2>
    <p class="tenue">Referencias de estilo: 3 a 6 animales sueltos recortados, <b>sin texto y sin cuadrículas</b>
      (si subes miniaturas completas, Gemini copia la cuadrícula y los textos). En cada imagen se mandan como mucho 3.</p>
    <div class="mini-refs">${refs || '<p class="tenue">Sin referencias todavía.</p>'}</div>
    <div class="fila"><input id="m-ref" type="file" accept="image/png,image/jpeg,image/webp">
      <button onclick="miniRefSubir()">Subir referencia</button></div></section>`;
}

/* --------- acciones */
async function miniAccion(ruta, cuerpo = {}, metodo = 'POST') {
  try { MINI = await miniApi(ruta, { method: metodo, cuerpo }); MINI_V = Date.now(); await pintarMini(); }
  catch (e) { alert(e.message); }
}
function miniProducir() {
  if (confirm(MINI.estimacion.texto + '\n\n¿Producir la miniatura?')) miniAccion('/producir');
}
function miniReintentarConPermiso(paso) {
  if (!confirm('Esto pasa el máximo por video. ¿Das permiso para seguir?')) return;
  if (paso === 'variantes') return miniAccion('/variantes', { n: 2, permiso: true });
  if (paso === 'regenerar') return miniAccion(`/sujetos/${MINI_SEL}/regenerar`, { instruccion: '', permiso: true });
  miniAccion('/producir', { permiso: true });
}
function miniRegenerar(i) { miniAccion(`/sujetos/${i}/regenerar`, { instruccion: $('#m-instr').value.trim() }); }
function miniVariantes() {
  if (confirm(`Se dibujan 2 versiones más del protagonista (≈ ${MINI.estimacion.por_imagen_usd} USD cada una). ¿Seguir?`))
    miniAccion('/variantes', { n: 2 });
}
function miniElegir(i, archivo) { miniAccion(`/sujetos/${i}/elegir`, { archivo }); }
function miniReferencia(i) {
  if (confirm('Esta imagen se agrega a las referencias de estilo del canal. ¿Seguir?')) miniAccion(`/sujetos/${i}/referencia`);
}
function miniCambios() {
  const c = MINI.plan.cells[MINI_SEL], cambios = { ajustes: { [MINI_SEL]: { ...c.ajuste, escala: +$('#m-esc').value } } };
  if (c.is_hero) {
    cambios.hero_text = $('#m-hero').value; cambios.hero_icon = $('#m-icono').value;
    cambios.hero_glow_color = $('#m-aura').value.toUpperCase(); cambios.hero_censor = $('#m-censura').checked;
  } else cambios.labels = { [MINI_SEL]: $('#m-label').value };
  return cambios;
}
function miniGuardar() { miniAccion('', miniCambios(), 'PUT'); }
function miniAjuste(a) { miniAccion('', { ajustes: { [MINI_SEL]: a } }, 'PUT'); }
function miniMover(dx, dy) {
  const a = MINI.plan.cells[MINI_SEL].ajuste;
  miniAjuste({ escala: +$('#m-esc').value, dx: a.dx + dx, dy: a.dy + dy });
}
function miniActivarArrastre() {
  let desde = null;
  document.querySelectorAll('.mini-ficha').forEach(f => {
    f.addEventListener('dragstart', () => { desde = +f.dataset.i; });
    f.addEventListener('dragover', e => e.preventDefault());
    f.addEventListener('drop', e => {
      e.preventDefault();
      const hacia = +f.dataset.i;
      if (desde === null || desde === hacia) return;
      const orden = [0, 1, 2, 3, 4, 5];
      orden.splice(hacia, 0, orden.splice(desde, 1)[0]);
      MINI_SEL = hacia;
      miniAccion('', { orden }, 'PUT');
    });
  });
}
async function miniRefSubir() {
  const f = $('#m-ref').files[0];
  if (!f) return alert('Escoge una imagen');
  const datos = new FormData(); datos.append('archivo', f);
  const r = await fetch(`/api/canales/${MINI.plantilla.canal}/miniatura/referencias`, { method: 'POST', body: datos });
  const v = await r.json().catch(() => ({}));
  if (!r.ok) return alert(v.detail || `Error ${r.status}`);
  MINI_V = Date.now(); pintarMini();
}
async function miniRefActiva(archivo, activa) {
  await api(`/api/canales/${MINI.plantilla.canal}/miniatura/referencias/${encodeURIComponent(archivo)}`,
    { method: 'PUT', cuerpo: { activa } });
  pintarMini();
}
async function miniRefBorrar(archivo) {
  if (!confirm('¿Borrar esta referencia de estilo?')) return;
  await api(`/api/canales/${MINI.plantilla.canal}/miniatura/referencias/${encodeURIComponent(archivo)}`, { method: 'DELETE' });
  pintarMini();
}
