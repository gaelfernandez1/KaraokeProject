# 000 · El plan v3 sustituye al plan v2

- **Fecha**: 28/10/2026
- **Estado**: aceptada
- **Afecta a**: todas las áreas

## Contexto

El plan v2 (`docs/10-plan-fases-v2.md`, fases V1–V8) modernizaba el sistema por partes y mantenía
Flask/Jinja. Se decidió una mejora masiva de todo, con investigación nueva y libertad para
cambiar cómo se hace, con un objetivo claro: karaoke bien transcrito, subtítulos animados en
sincronía, gallego primero, cualquier canción y cualquier pantalla (móvil, portátil, tele).

## Decisión

Se abandona el plan v2. Manda `docs/plan-v3/00-vision.md`, y el trabajo se reparte en diez
áreas (C1–C10) coordinadas por `ESTADO.md` y por estas decisiones.

## Consecuencias

- Los documentos viejos (`docs/00–10`, `docs/planning/`) pasan a ser solo historia; C1 los archiva.
- Siguen vigentes: sin monetización y commits en inglés con tono humano.
- Las decisiones ratificadas en julio (Flask sin framework, sin SSE, etc.) ya no obligan; las
  nuevas decisiones iniciales están en `00-vision.md` §5.

---

Plantilla para nuevas decisiones (`NNN-titulo-corto.md`): Fecha · Estado (propuesta, aceptada,
sustituida por NNN) · Afecta a · Contexto · Decisión · Consecuencias. Cortas: media página.
