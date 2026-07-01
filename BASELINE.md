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
| MCP | | | | |
| kri | | | | |

---

## Criterio de éxito

- Target: **kri ≤ 50% de los turnos de MCP** en cada test.
- Si queda por encima del 60%, revisar la skill: probablemente no está empujando
  lo suficiente hacia `kri batch` / `kri status` como primer y único paso de orientación.
