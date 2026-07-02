# kri (ex krita-mcp) — estado e instrucciones para continuar

## Qué es esto

CLI `kri` (single-file, stdlib, `cli/kri`) que controla Krita vía el plugin
`krita-plugin/kritamcp/` (HTTP localhost:5678). Reemplaza al MCP server
(`server.py`), que se retira al final de la migración. Skill de uso en
`claude/skills/kri/SKILL.md` — **usala siempre que haya que tocar Krita**.

## Estado de la migración (branch `feat/cli`)

- ✅ Implementado y testeado (20 tests: `python3 -m unittest discover -s tests`):
  CLI completo, plugin con `doc_info`/`exec` gateado/`stop_on_error`, skill kri,
  hook `claude/hooks/krita-prompt-reminder.py` con matcher Bash, skills de
  prompt-formatting retargeteadas, README reescrito.
- ⏳ **PENDIENTE — seguir acá:**
  1. **Testing + benchmarking en la máquina con Krita**: seguir `TESTING.md`
     de arriba a abajo (fases 1-6). Incluye el E2E funcional del CLI y el
     benchmark MCP vs kri. Regla de oro: el baseline MCP (fase 2) se corre
     ANTES de instalar la config del CLI (fase 3).
  2. **Llenar `BASELINE.md`** (4 filas: MCP y kri × 2 tests, turnos + minutos).
     Target: kri ≤ 50% de los turnos de MCP.
  3. **Task 13 (GATEADA al punto 2)**: tag `v-mcp-final` en master → borrar
     `server.py` → merge `feat/cli` a master → `claude mcp remove krita` en
     cada máquina. Pasos exactos en
     `docs/superpowers/plans/2026-07-01-kri-cli.md` (Task 13).

## Reglas de trabajo en este repo

- El plugin corre DENTRO de Krita: cambios en `krita-plugin/` requieren
  redeploy a `pykrita` + reiniciar Krita. Verificar con `python3 -m py_compile`.
- No tocar `server.py` hasta la Task 13 (el baseline MCP depende de él).
- Contrato CLI↔plugin: cada subcomando de `kri` mapea 1:1 a un método `cmd_*`
  del plugin; si agregás una action nueva, va en ambos lados + test en
  `tests/test_kri.py` (fake server, TDD).
- Los tests corren sin Krita: `python3 -m unittest discover -s tests -v`.
- Push directo a master está bloqueado por permisos; el usuario lo hace con
  `! git push` si hace falta.
