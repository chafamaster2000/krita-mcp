# Plan de testing en la otra computadora — `feat/cli`

Objetivo: validar el CLI `kri` end-to-end contra un Krita real, y llenar `BASELINE.md`
(MCP vs kri) para habilitar el retiro del MCP (Task 13 del plan).

**Orden importante:** el baseline MCP (Fase 2) se corre ANTES de instalar la config
del CLI en Claude Code (Fase 3). El branch `feat/cli` mantiene `server.py` intacto y
el plugin es retro-compatible, así que ambas mediciones salen del mismo checkout.

---

## Fase 1 — Preparación común (~10 min)

```bash
cd <repo> && git fetch && git checkout feat/cli && git pull
```

1. **Redeployar el plugin** (los cambios nuevos: `doc_info`, `exec`, `stop_on_error`):

   | OS | destino |
   |----|---------|
   | Windows | `%APPDATA%\krita\pykrita\kritamcp\` |
   | Linux | `~/.local/share/krita/pykrita/kritamcp/` |
   | macOS | `~/Library/Application Support/krita/pykrita/kritamcp/` |

   Copiar `krita-plugin/kritamcp/` completo encima del instalado y **reiniciar Krita**.
2. Verificar que AI Diffusion conecta a su Comfy (abrir el panel, estado verde).
3. Elegir el `[ESTILO_B]` de BASELINE.md: un estilo instalado de **otra familia**
   que el estilo actual (ej.: si usás SDXL/Illustrious → uno Flux o Z-Image).
   Anotarlo en `BASELINE.md`.

**Check de salida:** `curl -s localhost:5678/health` → `{"status": "ok", "plugin": "kritamcp"}`.

---

## Fase 2 — Baseline MCP (ANTES de tocar la config de Claude Code)

Con la config actual de esa máquina (MCP server registrado, hook viejo si lo tenía):

1. Sesión **fresca** de Claude Code → pegar el prompt del **Test 1** de `BASELINE.md`
   (config AI Diffusion sin generar). Anotar en la tabla: **turnos** (cantidad de
   tool calls de la sesión) y **minutos** (reloj).
2. Sesión fresca → prompt del **Test 2** (casita: dibujar → mirar → corregir → mirar).
   Anotar turnos y minutos.

> Si el MCP no estaba registrado en esa máquina:
> `claude mcp add krita -- python3 /ruta/al/repo/server.py`
> (necesita el venv con fastmcp/httpx: `pip install fastmcp httpx`).

---

## Fase 3 — Instalar el CLI y su config (~5 min)

```bash
# 1. el comando
mkdir -p ~/.local/bin && ln -sf "$PWD/cli/kri" ~/.local/bin/kri
kri health   # → {"status": "ok", "plugin": "kritamcp"}

# 2. skills + hook (a la config personal de esa máquina)
mkdir -p ~/.claude/skills ~/.claude/hooks
cp -r claude/skills/* ~/.claude/skills/
cp claude/hooks/krita-prompt-reminder.py ~/.claude/hooks/
```

3. En `~/.claude/settings.json` de esa máquina:
   - Permisos:
     ```json
     "permissions": { "allow": ["Bash(kri:*)"], "ask": ["Bash(kri exec:*)"] }
     ```
   - Hook: el `PreToolUse` que apuntaba a `mcp__krita__...` pasa a `"matcher": "Bash"`
     (mismo command, timeout 8). Si no existía, agregarlo:
     ```json
     "PreToolUse": [{ "matcher": "Bash", "hooks": [{ "type": "command",
       "command": "python3 \"$HOME/.claude/hooks/krita-prompt-reminder.py\"", "timeout": 8 }] }]
     ```
4. Reiniciar Claude Code (o `/hooks`) para que tome hook y permisos.

---

## Fase 4 — E2E funcional de kri (a mano, sin Claude, ~10 min)

Cada paso imprime JSON; cualquier `error` corta la cadena con exit 1.

**4.1 Transporte + status**
```bash
kri health && kri status
```
✅ `status` muestra `doc` (o null) + `ai` con `model.architecture` presente.

**4.2 Pintura + look**
```bash
kri canvas 800 600 --bg "#ffffff" && kri color "#cc3333" && kri fill 400 300 120 && kri look
```
✅ Abrir el path impreso: canvas blanco con círculo rojo.

**4.3 Batch con stop-on-error**
```bash
kri batch --look fast <<'EOF'
[{"action": "set_color", "params": {"color": "#3366cc"}},
 {"action": "draw_shape", "params": {"shape": "rectangle", "x": 100, "y": 100, "width": 200, "height": 150}},
 {"action": "accion_inexistente", "params": {}},
 {"action": "fill", "params": {"x": 700, "y": 500, "radius": 60}}]
EOF
echo "exit: $?"
```
✅ exit 1, `stopped_at: 2`, solo 3 results (el fill nunca corrió), rectángulo azul visible.

**4.4 exec — doble compuerta**
```bash
echo 'print(doc.width())' | kri exec        # Krita SIN la env var
```
✅ exit 1 con mensaje que menciona `KRITAMCP_ALLOW_EXEC=1`.

Relanzar Krita con `KRITAMCP_ALLOW_EXEC=1` en su entorno y:
```bash
echo 'print(doc.width()); result = {"layers": len(doc.topLevelNodes())}' | kri exec
```
✅ `{"status": "ok", "stdout": "800\n", "result": {"layers": ...}}`.

**4.5 AI sin generar**
```bash
kri ai set-params --style "<un estilo instalado>" && kri ai status
kri ai set-prompt -p "test prompt" && kri ai status
```
✅ El estilo cambia y el prompt aparece en `prompt.positive`.

**4.6 Hook + permisos dentro de Claude Code**
En una sesión de Claude Code pedile algo tipo "cambiá el prompt de AI Diffusion a X":
✅ los `kri ...` corren **sin** pedir permiso; ✅ antes del set-prompt el modelo recibe
el recordatorio "Modelo activo: architecture=..."; ✅ `kri exec` SÍ pide permiso.

**4.7 (opcional, gasta una generación)** `kri ai generate --wait && kri ai apply && kri look`
✅ una sola invocación bloquea hasta el final; no hubo polling con `kri ai jobs`.

---

## Fase 5 — Baseline kri

Igual que la Fase 2 pero ya con el CLI configurado: sesión fresca por test, mismos
prompts textuales de `BASELINE.md`, anotar turnos y minutos en las filas `kri`.

**Veredicto:** kri ≤ 50% de los turnos de MCP en cada test = objetivo cumplido.
Entre 50-60% = revisar si la skill empujó a `batch`/`status` (mirar el transcript:
¿encadenó comandos sueltos donde había un batch obvio?). >60% = hay que iterar la skill.

---

## Fase 6 — Reporte y cierre

1. Commitear `BASELINE.md` con las 4 filas llenas (y cualquier fix que haya salido
   del E2E) en `feat/cli`, y pushear.
2. Anotar cualquier comportamiento raro (comandos que fallaron, mensajes confusos,
   falsos positivos del hook) como issues o en el commit.
3. Avisarle a Claude: "baseline listo, ejecutá la Task 13" → tag `v-mcp-final`,
   borrar `server.py`, merge a master, `claude mcp remove krita` en cada máquina.

---

## Troubleshooting

| Síntoma | Causa probable / fix |
|---|---|
| `Cannot connect to Krita at http://localhost:5678` | Krita cerrado, plugin no habilitado (Python Plugin Manager → "Krita MCP Bridge"), o falta reiniciar Krita tras el deploy |
| Warning de puerto 5678 ocupado al abrir Krita | Instancia vieja / otro proceso: cerrar todo Krita, verificar con `lsof -i :5678` (mac/linux) y reabrir |
| `kri: command not found` | `~/.local/bin` fuera del PATH → `export PATH="$HOME/.local/bin:$PATH"` en el rc del shell |
| `Unknown action: doc_info` en `kri status` | El plugin viejo sigue cargado: redeploy no copió encima o falta reiniciar Krita |
| `kri ai ...` devuelve "AI Diffusion plugin not loaded" | AI Diffusion deshabilitado o Krita recién abierto sin documento; abrir el panel primero |
| exec devuelve "exec is disabled" aunque seteaste la env var | La env var tiene que estar en el entorno DEL PROCESO de Krita (lanzarlo desde una terminal con `KRITAMCP_ALLOW_EXEC=1 krita`, o en el .desktop/launchd), no en tu shell suelta |
| El hook no inyecta el recordatorio | Matcher sigue en `mcp__krita__...` o Claude Code sin reiniciar tras editar settings |
