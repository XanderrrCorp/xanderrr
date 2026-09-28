/* Administración mínima de Xandart: precios, planes, paquetes, márgenes, ajustes de créditos,
   saldos de proveedores y correo de avisos. (La versión con el diseño nuevo llega en la Fase 2.) */
const $ = s => document.querySelector(s);
async function api(ruta, opciones = {}) {
  const r = await fetch(ruta, { headers: { 'Content-Type': 'application/json' }, ...opciones,
    body: opciones.cuerpo ? JSON.stringify(opciones.cuerpo) : undefined });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.detail || `Error ${r.status}`);
  return datos;
}
const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const usd = n => (n == null ? '—' : `${Number(n).toFixed(2)} USD`);
const pct = n => (n == null ? '—' : `${n} %`);
const num = v => (v === '' || v == null ? null : Number(v));

async function pintar() {
  let d;
  try { d = await api('/api/v2/admin/resumen'); }
  catch (e) { $('#app').innerHTML = `<div class="error">${esc(e.message)}</div>`; return; }
  const m = d.margen;
  $('#app').innerHTML = `
  <h1>Administración</h1>
  <section class="tarjeta"><h2>Margen</h2>
    <div class="cifras">
      <div class="cifra"><span class="tenue">Cobrado a clientes</span><b>${usd(m.cobrado_usd)}</b></div>
      <div class="cifra"><span class="tenue">Costo real de proveedores</span><b>${usd(m.costo_real_usd)}</b></div>
      <div class="cifra"><span class="tenue">Margen</span><b>${usd(m.margen_usd)} · ${pct(m.margen_pct)}</b></div>
      <div class="cifra"><span class="tenue">A precio de lista</span><b>${usd(m.precio_lista_usd)}</b></div>
    </div>
    <p class="tenue" style="font-size:13px">Tu cuenta paga a costo real: su consumo suma al costo pero no a lo cobrado. «A precio de lista» es lo que habría pagado un cliente por todo lo producido.</p>
  </section>

  <section class="tarjeta"><h2>Saldo en los proveedores</h2>
    <p class="tenue">Anota el saldo que ves en la página de cada proveedor. Xandart le resta lo que gasta y te avisa por correo cuando baja del aviso.</p>
    <div class="desliza"><table class="tabla"><tr><th>Proveedor</th><th>Anotado</th><th>Gastado desde</th><th>Queda (estimado)</th><th>Aviso bajo</th><th></th></tr>
    ${d.proveedores.map(p => `<tr><td>${esc(p.proveedor)}</td><td>${usd(p.anotado_usd)} <span class="tenue">(${esc(p.fecha.slice(0, 10))})</span></td>
      <td>${usd(p.gastado_desde_usd)}</td><td class="${p.bajo ? 'bajo' : ''}">${usd(p.estimado_usd)}${p.bajo ? ' · recarga' : ''}</td>
      <td>${usd(p.umbral_usd)}</td><td></td></tr>`).join('')}
    <tr><td><input id="pv-nombre" class="largo" placeholder="together, minimax…"></td>
      <td><input id="pv-saldo" type="number" step="0.01" min="0" placeholder="saldo USD"></td><td></td><td></td>
      <td><input id="pv-umbral" type="number" step="0.01" min="0" placeholder="3.00"></td>
      <td><button class="mini" onclick="anotarProveedor()">Anotar saldo</button></td></tr></table></div>
  </section>

  <section class="tarjeta"><h2>Correo de avisos (Gmail)</h2>
    <p class="tenue">${d.correo_configurado ? '✓ Configurado.' : 'Sin configurar: los avisos solo se ven aquí.'}
      Usa una <b>contraseña de aplicación</b> de Google (myaccount.google.com/apppasswords), no tu contraseña normal. Se guarda solo en este computador.</p>
    <div class="fila"><input id="smtp-u" type="email" placeholder="tu_correo@gmail.com" autocomplete="off" style="max-width:260px">
      <input id="smtp-c" type="password" placeholder="contraseña de aplicación (16 letras)" autocomplete="off" style="max-width:260px">
      <button class="mini" onclick="guardarCorreo()">Guardar</button>
      <button class="mini" onclick="probarCorreo()">Mandar correo de prueba</button></div>
  </section>

  <section class="tarjeta"><h2>Precios (1 crédito = 0,01 USD)</h2>
    <div class="desliza"><table class="tabla"><tr><th>Acción</th><th>Unidad</th><th>Créditos</th><th>Costo real de referencia</th><th>Margen de referencia</th><th>Activo</th><th></th></tr>
    ${d.precios.map(p => `<tr><td><input class="largo" id="pr-n-${p.clave}" value="${esc(p.nombre)}"></td><td>${esc(p.unidad)}</td>
      <td><input id="pr-c-${p.clave}" type="number" min="0" value="${p.creditos}"></td>
      <td><input id="pr-r-${p.clave}" type="number" min="0" step="0.001" value="${p.costo_ref_usd}"></td>
      <td>${pct(p.margen_ref_pct)}</td><td><input id="pr-a-${p.clave}" type="checkbox" ${p.activo ? 'checked' : ''} style="width:auto"></td>
      <td><button class="mini" onclick="guardarPrecio('${p.clave}')">Guardar</button></td></tr>`).join('')}</table></div>
  </section>

  <section class="tarjeta"><h2>Planes</h2>
    <div class="desliza"><table class="tabla"><tr><th>Plan</th><th>USD/mes</th><th>Minutos/mes</th><th>Créditos/mes</th><th>Acumula hasta (meses)</th><th>Activo</th><th></th></tr>
    ${d.planes.map(p => `<tr><td><input id="pl-n-${p.clave}" value="${esc(p.nombre)}"></td>
      <td><input id="pl-p-${p.clave}" type="number" min="0" step="0.01" value="${p.precio_usd_mes}"></td>
      <td><input id="pl-m-${p.clave}" type="number" min="0" value="${p.minutos_mes}"></td>
      <td><input id="pl-c-${p.clave}" type="number" min="0" value="${p.creditos_mes}"></td>
      <td><input id="pl-t-${p.clave}" type="number" min="1" step="0.5" value="${p.tope_acumulado_meses}"></td>
      <td><input id="pl-a-${p.clave}" type="checkbox" ${p.activo ? 'checked' : ''} style="width:auto"></td>
      <td><button class="mini" onclick="guardarPlan('${p.clave}')">Guardar</button></td></tr>`).join('')}</table></div>
  </section>

  <section class="tarjeta"><h2>Paquetes de recarga</h2>
    <div class="desliza"><table class="tabla"><tr><th>Paquete</th><th>USD</th><th>Créditos</th><th>Activo</th><th></th></tr>
    ${d.paquetes.map(p => `<tr><td><input class="largo" id="pq-n-${p.clave}" value="${esc(p.nombre)}"></td>
      <td><input id="pq-p-${p.clave}" type="number" min="0" step="0.01" value="${p.precio_usd}"></td>
      <td><input id="pq-c-${p.clave}" type="number" min="0" value="${p.creditos}"></td>
      <td><input id="pq-a-${p.clave}" type="checkbox" ${p.activo ? 'checked' : ''} style="width:auto"></td>
      <td><button class="mini" onclick="guardarPaquete('${p.clave}')">Guardar</button></td></tr>`).join('')}</table></div>
  </section>

  <section class="tarjeta"><h2>Cuentas</h2>
    <div class="desliza"><table class="tabla"><tr><th>Cuenta</th><th>Saldo</th><th>Cobrado</th><th>Costo real</th><th>Margen</th><th>Ajuste manual</th></tr>
    ${d.espacios.map(e => `<tr><td>${esc(e.email)}${e.a_costo ? ' <span class="chip">a costo</span>' : ''}</td>
      <td>${e.saldo} créditos</td><td>${usd(e.margen.cobrado_usd)}</td><td>${usd(e.margen.costo_real_usd)}</td><td>${pct(e.margen.margen_pct)}</td>
      <td><div class="fila" style="margin:0"><input id="aj-c-${e.id}" type="number" placeholder="+/- créditos">
        <input id="aj-n-${e.id}" class="largo" placeholder="razón (obligatoria)">
        <button class="mini" onclick="ajustarCreditos('${e.id}')">Aplicar</button></div></td></tr>`).join('')}</table></div>
  </section>

  <section class="tarjeta"><h2>Bonos y avisos</h2>
    ${Object.entries(d.ajustes).map(([k, v]) => `<label>${esc(v.nota || k)}
      <textarea id="ajv-${k}" rows="2">${esc(JSON.stringify(Object.fromEntries(Object.entries(v).filter(([c]) => c !== 'nota'))))}</textarea></label>
      <div class="fila"><button class="mini" onclick="guardarAjuste('${k}')">Guardar</button></div>`).join('')}
  </section>`;
}

async function hacer(promesa, aviso = 'Guardado') {
  try { await promesa; await pintar(); if (aviso) alert(aviso); } catch (e) { alert(e.message); }
}
function guardarPrecio(k) {
  hacer(api(`/api/v2/admin/precios/${k}`, { method: 'PUT', cuerpo: { nombre: $(`#pr-n-${k}`).value,
    creditos: num($(`#pr-c-${k}`).value), costo_ref_usd: num($(`#pr-r-${k}`).value), activo: $(`#pr-a-${k}`).checked } }));
}
function guardarPlan(k) {
  hacer(api(`/api/v2/admin/planes/${k}`, { method: 'PUT', cuerpo: { nombre: $(`#pl-n-${k}`).value,
    precio_usd_mes: num($(`#pl-p-${k}`).value), minutos_mes: num($(`#pl-m-${k}`).value), creditos_mes: num($(`#pl-c-${k}`).value),
    tope_acumulado_meses: num($(`#pl-t-${k}`).value), activo: $(`#pl-a-${k}`).checked } }));
}
function guardarPaquete(k) {
  hacer(api(`/api/v2/admin/paquetes/${k}`, { method: 'PUT', cuerpo: { nombre: $(`#pq-n-${k}`).value,
    precio_usd: num($(`#pq-p-${k}`).value), creditos: num($(`#pq-c-${k}`).value), activo: $(`#pq-a-${k}`).checked } }));
}
function ajustarCreditos(id) {
  const creditos = parseInt($(`#aj-c-${id}`).value, 10), nota = $(`#aj-n-${id}`).value.trim();
  if (!creditos || !nota) return alert('Pon los créditos (con − para quitar) y la razón del ajuste.');
  if (!confirm(`¿${creditos > 0 ? 'Sumar' : 'Quitar'} ${Math.abs(creditos)} créditos? Razón: ${nota}`)) return;
  hacer(api('/api/v2/admin/creditos', { method: 'POST', cuerpo: { espacio_id: id, creditos, nota } }), 'Ajuste aplicado');
}
function guardarAjuste(k) {
  let valor;
  try { valor = JSON.parse($(`#ajv-${k}`).value); } catch (e) { return alert('Eso no quedó bien escrito: revisa comillas y llaves.'); }
  hacer(api(`/api/v2/admin/ajustes/${k}`, { method: 'PUT', cuerpo: { valor } }));
}
function anotarProveedor() {
  const nombre = $('#pv-nombre').value.trim(), saldo = num($('#pv-saldo').value), umbral = num($('#pv-umbral').value);
  if (!nombre || saldo == null) return alert('Pon el proveedor (por ejemplo together) y el saldo que ves en su página.');
  hacer(api(`/api/v2/admin/proveedores/${encodeURIComponent(nombre)}`, { method: 'PUT', cuerpo: { saldo_usd: saldo, umbral_usd: umbral } }));
}
function guardarCorreo() {
  const u = $('#smtp-u').value.trim(), c = $('#smtp-c').value;
  if (!u || !c) return alert('Pon el Gmail y la contraseña de aplicación.');
  hacer(api('/api/claves', { method: 'POST', cuerpo: { smtp_usuario: u, smtp_clave: c } }));
}
async function probarCorreo() {
  try { const r = await api('/api/v2/admin/correo/prueba', { method: 'POST' }); alert(`Correo enviado a ${r.para}. Revisa tu bandeja.`); }
  catch (e) { alert(e.message); }
}
pintar();
