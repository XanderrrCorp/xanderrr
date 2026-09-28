"""Plataforma multiusuario de Xandart (SaaS en preparación).

Todo pertenece a un espacio de trabajo: canales, estilos, personajes, plantillas,
fórmulas de guion, voces, videos y créditos. Lo que no tiene espacio (espacio_id
NULL) es el catálogo público de Xandart, de solo lectura para los usuarios.

Hoy corre en el PC del dueño con SQLite y un único usuario que entra solo; está
hecho para pasar a la nube sin rehacer nada:
- db.py        motor y sesiones (SQLite ahora, Postgres después: solo cambia la URL)
- modelos.py   las tablas
- almacen.py   dónde viven los archivos de cada espacio (carpeta local ahora, S3/R2 después)
- cuentas.py   quién es el usuario actual (local ahora, login después)
- creditos.py  libro de créditos: recargas, bonos, reservas, consumos y devoluciones
- precios.py   tabla de precios, planes y bonos (datos editables, nada en el código)
"""
