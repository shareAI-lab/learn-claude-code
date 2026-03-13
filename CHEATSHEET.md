# Claude Agent Cheatsheet — learn-claude-code

## El Loop (nunca modificar)
```python
while True:
    response = client.messages.create(model=MODEL, system=SYS, messages=msgs, tools=TOOLS, max_tokens=8000)
    msgs.append({"role": "assistant", "content": response.content})
    if response.stop_reason != "tool_use": return
    results = []
    for block in response.content:
        if block.type == "tool_use":
            output = HANDLERS[block.name](**block.input)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
    msgs.append({"role": "user", "content": results})
```

## Sesiones y qué añaden

| S | Mecanismo | Clave |
|---|-----------|-------|
| 01 | Loop base | exit: `stop_reason != "tool_use"` |
| 02 | Tool dispatch + seguridad | dict handlers, safe_path, truncate 50k |
| 03 | TodoWrite | 1 solo in_progress, nag cada 3 rondas |
| 04 | Subagentes | contexto fresco, sin tool `task`, solo retorna texto |
| 05 | Skills | SKILL.md, 2-layer injection |
| 06 | Compression | micro + auto (50k) + explicit, transcripts en disco |
| 07 | Task system | .tasks/*.json, DAG blockedBy/blocks |
| 08 | Background | daemon threads, drain_notifications() pre-LLM |
| 09 | Teams | JSONL inboxes, .team/config.json |
| 10 | Protocols | request_id correlation, FSM pending→approved/rejected |
| 11 | Autonomy | idle poll 5s/60s, task scan+claim, identity re-injection |
| 12 | Worktrees | git worktree, EventBus JSONL, control↔execution planes |

## Patrones de estado

```
messages[]          → volátil, solo en memoria
.tasks/*.json       → durable, sobrevive compression
.team/              → durable, teammates + inboxes
.transcripts/       → durable, historial comprimido
.worktrees/         → durable, aislamiento por tarea git
```

## Seguridad
```python
DANGEROUS = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
safe_path: (WORKDIR / p).resolve() — raise si escapa
output[:50000]  # truncar siempre
timeout=120     # bash; 300 background
```

## Subagente vs Teammate
```
Subagente:  spawn → trabajo → muere  (s04)
            contexto fresco, 30 iter max, retorna solo texto final

Teammate:   spawn → WORK → IDLE → WORK → shutdown  (s09+)
            thread daemon, JSONL inbox, identidad, 50 iter max
            idle: poll 5s × 12 = 60s → shutdown si sin trabajo
```

## Compression
```
micro_compact:  cada turno, silencioso, retiene 3 últimos tool_results
auto_compact:   >50k tokens, LLM resume, guarda transcript .jsonl
explicit:       model llama tool compact(), misma lógica
```

## SKILL.md
```markdown
---
name: skill-name
description: one line
tags: a, b
---
# Body
```
Layer 1: descripciones → system prompt
Layer 2: contenido → tool_result on demand

## Worktree workflow (s12)
```
task_create("feature") → .tasks/task_1.json
worktree_create("feat-branch", task_id=1) → git worktree add -b wt/feat-branch
worktree_run("feat-branch", "npm test")
worktree_remove("feat-branch", complete_task=True) → task completo
```
