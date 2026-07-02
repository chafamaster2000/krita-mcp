# Baseline: MCP vs CLI `kri`

Protocolo de medición para la migración MCP → CLI. Correr **antes** de escribir el CLI
(columna MCP) y **después** de mergear `feat/cli` (columna kri), con el mismo prompt
textual, en sesión fresca de Claude Code, Krita abierto con el plugin y AI Diffusion activos.

**Qué se cuenta:**
- **Turnos**: cantidad total de tool calls de la sesión (MCP tools o invocaciones de Bash).
- **Minutos**: reloj de pared desde que se manda el prompt hasta la respuesta final.
- **Sin generar**: ninguna tarea dispara generación en Comfy — medimos orquestación, no GPU.

---

## Test 1 — Configurar AI Diffusion (sin generar)

Prompt a pegar (idéntico en ambas corridas):

> Fijate cómo está configurado AI Diffusion ahora. Después cambiá el estilo a
> [ESTILO_B, un estilo de otra familia de modelo que la actual], y escribí un
> prompt positivo y negativo para "un zorro leyendo bajo una lámpara de noche,
> ambiente cálido" formateado según la convención de la nueva familia de modelo.
> No generes nada. Al final confirmame qué quedó seteado.

Completar `[ESTILO_B]` con un estilo real instalado (anotarlo acá para reusarlo): ________

| Corrida | Fecha | Turnos | Minutos | Notas |
|---|---|---|---|---|
| MCP | | | | |
| kri | | | | |

## Test 2 — Dibujar y revisar

Prompt a pegar (idéntico en ambas corridas):

> Creá un canvas de 1024x768 fondo blanco y dibujá una casita simple: cuerpo
> cuadrado, techo triangular, puerta, dos ventanas y un sol arriba a la derecha,
> con colores distintos por elemento. Mirá el resultado, corregí lo que haya
> quedado mal ubicado, y volvé a mirar para confirmar.

| Corrida | Fecha | Turnos | Minutos | Notas |
|---|---|---|---|---|
| MCP | 2026-07-01 | 3 | ~1.4 | subagente; new_canvas + 2 batch |
| kri (skill v1) | 2026-07-01 | 5 | ~3.7 | subagente; status + exec(rechazado) + 2 batch + look — 2 turnos desperdiciados |
| kri (skill v2) | 2026-07-01 | 2 | ~1.5 | subagente; 2× batch+look fast — piso teórico del flujo dibujar→mirar→corregir→mirar |

> Metodología: no fue sesión fresca real; se usó un subagente de contexto limpio
> por interfaz (mismo prompt del Test 2), corridos en secuencia contra el mismo
> Krita. n=1 por corrida, alta varianza.
>
> **Corrida 1 (skill v1): kri 167% de MCP.** Causa: la skill forzaba
> `status`-first (overhead en canvas en blanco) y el agente probó `exec`
> (compuerta lo rechazó). Se iteró la skill: status solo cuando el estado
> existente/AI importa, exec nunca para dibujar, no duplicar look tras
> `--look fast`, guía para triángulos compuestos.
>
> **Corrida 2 (skill v2): kri 2 turnos = 67% de MCP.** Mejor que MCP en
> absoluto, pero no llega al ≤50% del criterio. Ojo: 2 turnos es el piso
> teórico de este test (1 batch dibujo + 1 batch corrección, ambos con
> `--look fast`), y el piso de MCP es ~2-3 también — el target ≤50% no es
> alcanzable en Test 2 porque ambas interfaces baten cerca del piso. El
> veredicto de la migración debería apoyarse en Test 1 (config AI), donde el
> MCP histórico encadenaba muchas tools sueltas. Test 1 pendiente: AI
> Diffusion desconectado en esta máquina (`ai: "Conexión rechazada"`).

---

## Criterio de éxito

- Target: **kri ≤ 50% de los turnos de MCP** en cada test.
- Si queda por encima del 60%, revisar la skill: probablemente no está empujando
  lo suficiente hacia `kri batch` / `kri status` como primer y único paso de orientación.
