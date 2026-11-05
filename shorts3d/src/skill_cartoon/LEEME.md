# Skill «cartoon-3d-short» (Claude Animated Shorts, MIT, © 2026 Mr omi — ver LICENSE)

Copia del código de la skill que mandó el dueño el 05-11-2026 (`claude-animated-shorts-main.zip`).
- `bridge/`: el corto de ejemplo completo (composición `SkillPuente`). Sus piezas de estilo (tinta, desenfoque,
  gradación, sombreado de dos tonos, texturas pintadas, personajes 2D de `toon.ts`) las usa «En este pueblo…»
  desde `src/pueblo/look/` sin modificarlas.
- `audio/`, `scripts/`: el sonido sintetizado y las herramientas de la skill.
- Las instrucciones de la skill están en `/.claude/skills/cartoon-3d-short/SKILL.md`.
- NO están (a propósito) `references/frames` ni `references/sheets`: son material de estudio privado de otro canal y la
  skill pide no publicarlo. El repo es público.
- Sin los modelos de Kenney (kenney.nl está bloqueado en la nube) la skill funciona igual: dibuja sus propias plantas.
- Velocidad: en la nube (sin GPU) ~47 s por cuadro con el puente y ~12-18 s con el pueblo: aquí solo cuadros de
  revisión; los videos completos se renderizan en el PC del dueño (NVIDIA, `--gl=angle`).
