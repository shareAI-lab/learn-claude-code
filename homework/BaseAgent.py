import os,json,ast,subprocess,difflib,yaml,time,re,copy
from pathlib import Path

try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN",None)

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"
MEMORY_DIR = WORKDIR / ".memory"; MEMORY_DIR.mkdir(exist_ok=True)
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
TRANSCRIPTS_DIR = WORKDIR / ".transcripts"
TOOL_RESULT_DIR = WORKDIR / ".task_outputs" / "tool_results"
TODO_FILE = REPO_ROOT / ".todo.json"
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL=os.environ["MODEL_ID"]
CURRENT_TODOS:list[dict] = []

def safe_path(p:str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

#==================== MEMORY SYSTEM ====================
MEMORY_TYPES = ['user', 'feedback', 'project', 'reference']

def _parse_memory_frontmatter(text:str) -> tuple[dict,str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3: return {}, text
    meta = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k,v = line.split(":",1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2].strip()

def write_memory_file(name:str, mem_type:str, description:str, body:str):
    slug = name.lower().replace(" ","-").replace("/","-")
    filename = f"{slug}.md"
    filepath = MEMORY_DIR / filename
    filepath.write_text(
        f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}\n---\n\n{body}\n"
    )
    _rebuild_index()
    return filepath

def _rebuild_index():
    lines = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md": continue
        raw = f.read_text()
        meta, body = _parse_memory_frontmatter(raw)
        name = meta.get("name", f.stem)
        desc = meta.get("description", body.split("\n")[0][:80])
        lines.append(f"- [{name}]({f.name}) — {desc}")
    MEMORY_INDEX.write_text("\n".join(lines) + "\n" if lines else "")

def read_memory_index() -> str:
    if not MEMORY_INDEX.exists():
        return ""
    text = MEMORY_INDEX.read_text().strip()
    return text if text else ""

def read_memory_file(filename:str) -> str | None:
    path = MEMORY_DIR / filename
    if not path.exists():
        return None
    return path.read_text()

def list_memory_files() -> list[dict]:
    result = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md": continue
        raw = f.read_text()
        meta, body = _parse_memory_frontmatter(raw)
        result.append({
            "filename": f.name,
            "name": meta.get("name", f.stem),
            "description": meta.get("description", ""),
            "type": meta.get("type", "user"),
            "body":body,
        })
    return result

def select_relevant_memories(messages: list, max_items: int = 5) -> list[str]:
    files = list_memory_files()
    if not files:
        return []
    
    recent_texts = []
    for msg in reversed(messages):
        content = msg.get("content","")
        if isinstance(content,list):
            content = " ".join(
                str(getattr(b,"text","")) for b in content
                if getattr(b,"type",None) == "text"
            )
        if _is_internal_reminder_text(content.strip()):
            continue
        if isinstance(content, str):
            recent_texts.append(content)
        if len(recent_texts) >= 5:
            break

    recent = " ".join(reversed(recent_texts))[:2000]

    if not recent.strip():
        return []
    
    catalog_lines = []
    for i, f in enumerate(files):
        catalog_lines.append(f"{i}: {f['name']} — {f['description']}")
    catalog = "\n".join(catalog_lines)

    prompt = (
        "Given the recent conversation and the memory catalog below, "
        "select the indices of memories that are clearly relevant. "
        "Return ONLY a JSON array of integers, e.g. [0, 3]. "
        "If none are relevant, return [].\n\n"
        f"Recent conversation:\n{recent}\n\n"
        f"Memory catalog:\n{catalog}"
    )

    try:
        response = client.messages.create(
            model = MODEL, messages = [{"role": "user", "content": prompt}], max_tokens = 200,
        )
        text = extract_text(response.content).strip()

        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            indices = json.loads(match.group())
            selected = []
            for idx in indices:
                if isinstance(idx, int) and 0<= idx < len(files):
                    selected.append(files[idx]["filename"])
                    if len(selected) >= max_items:
                        break
            return selected
    except Exception:
        pass

    keywords = [w.lower() for w in recent.split() if len(w) > 3]
    selected = []
    for f in files:
        text = (f["name"] + " " + f["description"]).lower()
        if any(kw in text for kw in keywords):
            selected.append(f["filename"])
            if len(selected) >= max_items:
                break
    return selected

def load_memories(messages:list) -> str:
    selected_files = select_relevant_memories(messages)
    if not selected_files:
        return ""
    
    parts = ["<relevant_memories>"]
    for filename in selected_files:
        content = read_memory_file(filename)
        if content:
            parts.append(content)
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)

def _is_internal_reminder_text(text:str) -> bool:
    text = text.strip().lower()
    return text.startswith("<reminder>") or text.startswith("</reminder>")

def extract_memories(messages:list) -> list[dict]:
    dialoge_parts = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content,list):
            content = " ".join(
                str(getattr(b,"text","")) for b in content
                if getattr(b,"type",None) == "text"
            )
        if isinstance(content,str) and content.strip():

            if role == "user" and _is_internal_reminder_text(content.strip()):
                continue

            dialoge_parts.append(f"{role}: {content}")
    dialogue = "\n".join(dialoge_parts)

    if not dialogue.strip():
        return
    
    existing = list_memory_files()
    existing_desc = "\n".join(f"- {m['name']}: {m['description']}" for m in existing) if existing else "(none)"

    prompt = (
        "Extract user preferences, constraints, or project facts from this dialogue.\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n"
        "- name: short kebab-case identifier (e.g. 'user-preference-tabs')\n"
        "- type: one of 'user' (user preference), 'feedback' (guidance), "
        "'project' (project fact), 'reference' (external pointer)\n"
        "- description: one-line summary for index lookup\n"
        "- body: full detail in markdown\n"
        "If nothing new or already covered by existing memories, return [].\n\n"
        f"Existing memories:\n{existing_desc}\n\n"
        f"Dialogue:\n{dialogue[:4000]}"
    )

    try:
        response = client.messages.create(
            model = MODEL, messages = [{"role": "user", "content": prompt}], max_tokens = 800,
        )
        text = extract_text(response.content).strip()

        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        if not items:
            return 
        count = 0
        for mem in items:
            name = mem.get("name",f"memory_{int(time.time())}")
            mem_type = mem.get("type","user")
            desc = mem.get("description","")
            body = mem.get("body","")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)
                count += 1
        if count:
            print(f"\n\033[33m[Memory: extracted {count} new memories]\033[0m")
    except Exception:
        pass

CONSOLIDATE_THRESHOLD = 10

def consolidate_memories():
    files = list_memory_files()
    if len(files) < CONSOLIDATE_THRESHOLD:
        return
    
    catalog = "\n".join(
        f"## {f['filename']}\nname: {f['name']}\ndescription: {f['description']}\n{f['body']}"
        for f in files
    )

    prompt = (
        "Consolidate the following memory files. Rules:\n"
        "1. Merge duplicates into one\n"
        "2. Remove outdated/contradicted memories\n"
        "3. Keep the total under 30 memories\n"
        "4. Preserve important user preferences above all\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n\n"
        f"{catalog[:16000]}"
    )

    try:
        response = client.messages.create(
            model = MODEL, messages = [{"role": "user", "content": prompt}], max_tokens = 3000,
        )
        text = extract_text(response.content).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        
        for f in MEMORY_DIR.glob("*.md"):
            if f.name != "MEMORY.md":
                f.unlink()

        for mem in items:
            name = mem.get("name",f"memory_{int(time.time())}")
            mem_type = mem.get("type","user")
            desc = mem.get("description","")
            body = mem.get("body","")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)

        print(f"\n\033[33m[Memory: consolidated {len(files)} → {len(items)} memories]\033[0m")
    except Exception:
        pass

def find_latest_text_user_message(messages: list) -> int | None:
      for i in range(len(messages) - 1, -1, -1):
          msg = messages[i]
          if msg.get("role") != "user":
              continue

          content = msg.get("content")
          if not isinstance(content, str) or not content.strip():
              continue

          if content.strip().startswith("<reminder>"):
              continue

          return i

      return None

def build_request_messages_with_memories(messages:list):
    memories = load_memories(messages)
    if not memories:
        return messages

    target = find_latest_text_user_message(messages)
    if target is None:
        return messages

    request_messages = messages.copy()
    request_messages[target] = {
        **messages[target],
        "content": messages[target]["content"] + "\n\n" + memories,
    }
    return request_messages

def build_memory_system() -> str:
    index = read_memory_index()
    memories_section = f"\n\nMemories available:\n{index}" if index else ""
    return (
        f"You are a coding agent at {WORKDIR}."
        f"{memories_section}\n"
        "Relevant memories are injected below. Respect user preferences from memory.\n"
        "When the user says 'remember' or expresses a clear preference, extract it as a memory."
    )


#==================== TODO SYSTEM ====================
def save_todos():
    TODO_FILE.parent.mkdir(parents=True, exist_ok=True)

    if all_todos_completed():
        if TODO_FILE.exists():
            TODO_FILE.unlink()
        return

    TODO_FILE.write_text(json.dumps(CURRENT_TODOS, ensure_ascii=False, indent=2))

def read_saved_todos() -> list:
      if not TODO_FILE.exists():
          return []
      try:
          todos = json.loads(TODO_FILE.read_text())
      except json.JSONDecodeError:
          return []
      return todos if isinstance(todos, list) else []

def all_todos_completed() -> bool:
    return bool(CURRENT_TODOS) and all(t.get('status') == 'completed' for t in CURRENT_TODOS)

def ask_resume_todos() -> str | None:
    global CURRENT_TODOS

    todos = read_saved_todos()
    if not todos:
        return None

    unfinished = [
        t for t in todos
        if t.get("status") != "completed"
    ]

    if not unfinished:
        if TODO_FILE.exists():
            TODO_FILE.unlink()
        return None

    print("\n检测到上次未完成的任务：")
    for i, todo in enumerate(unfinished, 1):
        print(f"  {i}. [{todo.get('status')}] {todo.get('content')}")

    choice = input("是否需要继续上次未完成的任务？[y/N] ").strip().lower()
    if choice not in ("y", "yes"):
        if TODO_FILE.exists():
            TODO_FILE.unlink()
        return None

    CURRENT_TODOS = todos
    return (
        "继续上次未完成的任务。请先读取当前 todo 状态，"
        "然后从第一个 pending 或 in_progress 项开始继续执行。"
    )

def format_current_todos() -> str:
    if not CURRENT_TODOS:
        return ""
    return "\n".join(
        f"- [{t['status']}] {t['content']}"
        for t in CURRENT_TODOS
    )

#==================== SKILL LOADING ====================
def _parse_skill_frontmatter(text:str) -> dict:
    """Parse YAML frontmatter from SKILL.md. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3: return {}, text
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2].strip()

SKILL_REGISTRY:dict[str, dict] = {}

def _scan_skills():
    if not SKILLS_DIR.exists():
        return
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        manifest = d / "SKILL.md"
        if manifest.exists():
            raw = manifest.read_text()
            meta, body = _parse_skill_frontmatter(raw)
            name = meta.get("name", d.name)
            desc = meta.get("description", raw.split("\n")[0].lstrip("#").strip())
            SKILL_REGISTRY[d.name] = {"name": name, "description": desc, "content": raw}

_scan_skills()

def list_skills() -> str:
    if not SKILL_REGISTRY:
        return "(no skills found)"
    return "\n".join(f"- **{s['name']}**: {s['description']}" for s in SKILL_REGISTRY.values())


#==================== TOOL SYSTEM ====================
def run_bash(command:str) -> str:
    try:
        r = subprocess.run(command, shell=True, cwd = WORKDIR,
                           capture_output=True, text=True, timeout = 120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    
def run_read(path:str,limit:int | None = None) -> str:
    try:
        lines = safe_path(path).read_text().splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"
    
def run_write(path:str,content:str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_edit(path:str,old_text:str,new_text:str) -> str:
    try:
        file_path = safe_path(path)
        text = file_path.read_text()
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text,new_text,1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"
    
def run_glob(pattern:str) -> str:
    import glob as g
    try:
        results = []
        for match in g.glob(pattern,root_dir=WORKDIR):
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"
    
def _normalize_todos(todos):
    if isinstance(todos,str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"
    if not isinstance(todos,list):
        return None, "Error: todos must be a list"
    for i, t in enumerate(todos):
        if not isinstance(t, dict):
            return None, f"Error: todos[{i}] must be an object"
        if "content" not in t or "status" not in t:
            return None, f"Error: todos[{i}] missing 'content' or 'status'"
        if t["status"] not in ("pending", "in_progress", "completed"):
            return None, f"Error: todos[{i}] has invalid status '{t['status']}'"
    return todos, None

def run_todo_write(todos:list) -> str:
    global CURRENT_TODOS
    todos, error = _normalize_todos(todos)
    if error:
        return error
    CURRENT_TODOS = todos
    save_todos()
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for t in CURRENT_TODOS:
        icon = {"pending": " ", "in_progress": "\033[36m▸\033[0m", "completed": "\033[32m✓\033[0m"}[t["status"]]
        #print(t, icon)
        lines.append(f"  [{icon}] {t['content']}")
    print("\n".join(lines))
    return f"Updated {len(CURRENT_TODOS)} tasks"

def load_skill(name:str) -> str:
    skill = SKILL_REGISTRY.get(name)
    if not skill:
        return f"Skill not found: {name}"
    return skill["content"]


TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "todo_write", "description": "Create and manage a task list for your current coding session.",
     "input_schema": {"type": "object", "properties": {"todos": {"type": "array", "items": {"type": "object", "properties": {"content": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["content", "status"]}}}, "required": ["todos"]}},
    {"name": "load_skill", "description": "Load the content of a skill by name.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
]

TOOL_HANDLERS = {
    "bash":run_bash,
    "read_file":run_read,
    "write_file":run_write,
    "edit_file":run_edit,
    "glob":run_glob,
    "todo_write":run_todo_write,
    "load_skill":load_skill,
}

#==================== SUBAGENT SYSTEM ====================
SUB_SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Complete the task you were given, then return a concise summary. "
    "Do not delegate further."
)

SUB_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
]

SUB_HANDLERS = {
    "bash":run_bash,
    "read_file":run_read,
    "write_file":run_write,
    "edit_file":run_edit,
    "glob":run_glob,
}

def extract_text(content) -> str:
    if not isinstance(content,list):
        return str(content)
    return "\n".join(getattr(b,"text","") for b in content if getattr(b,"type",None) == "text")

def spawn_subagent(description:str) -> str:
    print(f"\n\033[35m[Subagent spawned]\033[0m")
    messages = [{"role": "user", "content": description}]  # fresh context

    for _ in range(30):
        response = client.messages.create(
            model = MODEL, system=SUB_SYSTEM, messages = messages,
            tools = SUB_TOOLS, max_tokens = 8000,
        )
        messages.append({"role":"assistant","content":response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                blocked = trigger_hook("PreToolUse", block)
                if blocked:
                    results.append({"type": "tool_result", "tool_use_id": block.id,
                                    "content": str(blocked)})
                    continue
                handler = SUB_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
                trigger_hook("PostToolUse", block, output)
                print(f"  \033[90m[sub] {block.name}: {str(output)[:100]}\033[0m")
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output})
        messages.append({"role":"user","content":results})

    result = extract_text(messages[-1]["content"])
    if not result:
        for msg in reversed(messages):
            result = extract_text(msg["content"])
            if result:
                break
        if not result:
            result = "Subagent stopped after 30 turns without final answer."
    print(f"\033[35m[Subagent done]\033[0m")
    return result

TOOLS.append({
    "name": "task",
    "description": "Launch a subagent to handle a complex subtask. Returns only the final conclusion.",
    "input_schema": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]},
})
TOOL_HANDLERS["task"] = spawn_subagent

#==================== COMPACTION PIPELINE ====================
CONTEXT_LIMIT = 50000
KEEP_RECENT = 3
PERSIST_THRESHOLD = 30000

def estimate_size(messages:list) -> int: return len(str(messages))

def _block_get(block, key, default=None):
    if isinstance(block,dict):
        return block.get(key, default)
    return getattr(block, key, default)

def _block_type(block) -> str:
    return _block_get(block, "type")

def _message_has_tool_use(msg:list) -> bool:
    if msg.get("role") != "assistant":
        return False
    content = msg.get("content")
    if not isinstance(content,list):
        return False
    return any(_block_type(b) == "tool_use" for b in content)

def _is_tool_result_message(msg):
    if msg.get("role") != "user":
        return False
    content = msg.get("content")
    if not isinstance(content,list):
        return False
    return all(isinstance(b,dict) and b.get("type") == "tool_result" for b in content)

# L1:snipCompact
def snip_compact(messages,max_messages=500):
    if len(messages) <= max_messages: return messages
    keep_head, keep_tail = 3, max_messages - 3
    head_end, tail_start = keep_head, len(messages) - keep_tail
    if head_end > 0 and _message_has_tool_use(messages[head_end-1]):
        while head_end < len(messages) and _is_tool_result_message(messages[head_end]):
            head_end += 1
    if (tail_start > 0 and tail_start < len(messages) 
        and _message_has_tool_use(messages[tail_start - 1]) 
        and _is_tool_result_message(messages[tail_start])):
            tail_start -= 1
    if head_end >= tail_start:
        return messages
    snipped = tail_start - head_end
    return messages[: head_end] + [{"role": "user", "content":f"[snipped {snipped} messages]"}] + messages[tail_start:]

#L2: microCompact
PRESERVE_TOOL_RESULTS = ["task","load_skill"]

def collect_tool_results(messages:list) -> list:
    blocks = []
    for mi,msg in enumerate(messages):
        if msg.get("role") != "user" or not isinstance(msg.get("content"),list): continue
        for bi,block in enumerate(msg["content"]):
            if isinstance(block,dict) and block.get("type") == "tool_result":
                blocks.append((mi,bi,block))
    return blocks

def build_tool_use_name_map(messages: list) -> dict[str, str]:
    mapping = {}
    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if _block_type(block) == "tool_use":
                tool_id = _block_get(block, "id", None)
                tool_name = _block_get(block, "name", None)
                
                if tool_id and tool_name:
                    mapping[str(tool_id)] = tool_name

    return mapping

def micro_compact(messages):
    tool_results = collect_tool_results(messages)
    if len(tool_results) < KEEP_RECENT:
        return messages
    
    tool_name = build_tool_use_name_map(messages)

    for _, _, block in tool_results[:-KEEP_RECENT]:
        content = str(block.get("content", ""))
        tid = block.get("tool_use_id")
        tname = tool_name.get(tid)

        if "<persisted-output>" in content:
            continue

        if tname in PRESERVE_TOOL_RESULTS:
            continue

        if len(content) > 120:
            block["content"] = "[Earlier tool result compacted. Re-run if needed.]"
    return messages

#L3: toolResultBudget
def persist_large_output(tool_use_id, output):
    if len(output) <= PERSIST_THRESHOLD: return output
    TOOL_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = TOOL_RESULT_DIR / f"{tool_use_id}.txt"
    if not path.exists(): path.write_text(output)
    return f"<persisted-output>\nFull output: {path}\nPreview:\n{output[:2000]}\n</persisted-output>"


def tool_result_budget(messages,max_bytes=200_000):
    last = messages[-1] if messages else None
    if not last or last.get("role") != "user" or not isinstance(last.get("content"),list): return messages
    blocks = [(i, b) for i, b in enumerate(last["content"]) if isinstance(b,dict) and b.get("type") == "tool_result"]
    total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    if total <= max_bytes: return messages
    ranked = sorted(blocks, key=lambda p: len(str(p[1].get("content", ""))), reverse=True)
    for _, block in ranked:
        if total <= max_bytes: break
        content = str(block.get("content", ""))
        if len(content) <= PERSIST_THRESHOLD: continue
        tid = block.get("tool_use_id", "unknown")
        block["content"] = persist_large_output(tid, content)
        total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    return messages

#L4: autoCompact
def write_transcript(messages):
    TRANSCRIPTS_DIR.mkdir(parents=True,exist_ok=True)
    path=TRANSCRIPTS_DIR / f"transcript_{int(time.time())}.jsonl"
    with path.open("w") as f:
        for msg in messages: f.write(json.dumps(msg,default=str) + "\n")
    return path

def summarize_history(messages):
    conversation = json.dumps(messages, default=str)[:80000]
    prompt = ("Summarize this coding-agent conversation so work can continue.\n"
              "Preserve: 1. current goal, 2. key findings/decisions, 3. files read/changed, "
              "4. remaining work, 5. user constraints.\nBe compact but concrete.\n\n" + conversation)
    response = client.messages.create(model=MODEL, messages=[{"role": "user", "content": prompt}], max_tokens=2000)
    return "\n".join(
        getattr(block, "text", "")
        for block in response.content
        if getattr(block, "type", None) == "text").strip() or "(empty summary)"

def compact_history(messages):
    transcript_path = write_transcript(messages)
    print(f"[transcript saved: {transcript_path}]")
    summary = summarize_history(messages)
    return [{"role": "user", "content": f"[Compacted]\n\n{summary}"}]

#Emergency: reactiveCompact
def reactive_compact(messages):
    transcript = write_transcript(messages)
    tail_start = max(0, len(messages) - 5)
    if (tail_start > 0 and tail_start < len(messages)
            and _is_tool_result_message(messages[tail_start])
            and _message_has_tool_use(messages[tail_start - 1])):
        tail_start -= 1
    summary = summarize_history(messages[:tail_start])
    return [{"role": "user", "content": f"[Reactive compact]\n\n{summary}"}, *messages[tail_start:]]



#==================== HOOK SYSTEM ====================
HOOKS = {"UserPromptSubmit":[],"PreToolUse":[],"PostToolUse":[],"Stop":[]}

def register_hook(event:str,callback):
    HOOKS[event].append(callback)

def trigger_hook(event:str,*args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None

DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777", "curl"]

def permission_hook(block):
    if block.name == "bash":
        for pattern in DENY_LIST:
            if pattern in block.input.get("command",""):
                print(f"\n\033[31m⛔ Blocked: '{pattern}'\033[0m")
                return "Permission denied by deny list"
        for kw in DESTRUCTIVE:
            if kw in block.input.get("command",""):
                print(f"\n\033[33m⚠  Potentially destructive command\033[0m")
                print(f"   Tool: {block.name}({block.input})")
                choice = input("   Allow? [y/N] ").strip().lower()
                if choice not in ("y","yes"):
                    return "Permission denied by user"
    return None

def log_hook(block):
    args_preview = str(list(block.input.values())[:2])[:60]
    print(f"\033[90m[HOOK] {block.name}({args_preview})\033[0m")
    return None

def large_output_hook(block,output):
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] ⚠ Large output from {block.name}: {len(str(output))} chars\033[0m")
    return None

def context_inject_hook(query:str):
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None

def summary_hook(messages:list):
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"),list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None

def diff_preview_hook(block):
    if block.name not in ("write_file","edit_file"):
        return None
    
    path = block.input.get("path","")
    try:
        file_path = safe_path(path)
    except Exception as e:
        return(f"[HOOK] Error: {e}")

    old_text = file_path.read_text() if file_path.exists() else ""

    if block.name == "write_file":
        new_text = block.input.get("content","")
    else:
        old_price = block.input.get("old_text","")
        new_price = block.input.get("new_text","")
        if old_price not in old_text:
            return None
        new_text = old_text.replace(old_price,new_price,1)

    diff = difflib.unified_diff(
        old_text.splitlines(), 
        new_text.splitlines(),
        fromfile=f"{path}before",
        tofile=f"{path}after",
        lineterm="",
        )
    
    print("\n".join(diff) or "(no diff)")
    choice = input("   Apply change? [y/N] ").strip().lower()
    if choice not in ("y","yes"):
        return "File change rejected by user"
    
    return None

register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PreToolUse", diff_preview_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)

#==================== SYSTEM PROMPT ASSEMBLY ====================
PROMPT_SECTIONS = {
    "identity": "You are a coding agent. Act, don't explain.",
    "workspace": f"Working directory: {WORKDIR}",
    "tools": f"Available tools: {','.join([t['name'] for t in TOOLS])}.",
    "skills": "Skills available:" + list_skills(),
    "memory": "Memory index:" + build_memory_system(),
}

def assemble_system_prompt(context:dict) -> str:
    sections = []
    sections.append(PROMPT_SECTIONS["identity"])
    sections.append(PROMPT_SECTIONS["tools"])
    sections.append(PROMPT_SECTIONS["workspace"])

    memories = context.get("memories","")
    if memories:
        sections.append(f"Memory index:\n{memories}")

    skills = context.get("skills")
    if skills:
        sections.append(PROMPT_SECTIONS["skills"])

    todos = context.get("todos", "")
    if todos:
        sections.append(f"Current tasks:\n{todos}")

    return "\n\n".join(sections)

_last_context_key = None
_last_prompt = None

def get_system_prompt(context:dict) -> str:
    global _last_context_key, _last_prompt
    key = json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)
    if key == _last_context_key and _last_prompt:
        print("  \033[90m[cache hit] system prompt unchanged\033[0m")
        return _last_prompt
    _last_context_key = key
    _last_prompt = assemble_system_prompt(context)
    
    loaded = ["identity","tools","workspace"]
    if context.get("memories"):
        loaded.append("memory")
    if context.get("todos"):
        loaded.append("todos")
    print(f"  \033[32m[assembled] sections: {', '.join(loaded)}\033[0m")
    return _last_prompt

def update_context(context:dict,messages:list) -> dict:
    memories = ""
    if MEMORY_INDEX.exists():
        content = MEMORY_INDEX.read_text().strip()
        if content:
            memories = content
    skills = ""
    if SKILL_REGISTRY:
        skills = str(','.join([s['name'] for s in SKILL_REGISTRY.values()]))

    todos = format_current_todos()

    return {
        "enabled_tools": TOOL_HANDLERS.keys(),
        "workspace": str(WORKDIR),
        "memories": memories,
        "skills": skills,
        "todos": todos,
    }

#==================== AGENT LOOP ====================
rounds_since_todo = 0
MAX_REACTIVE_RETRIES = 1

def agent_loop(messages:list, context:dict):
    global rounds_since_todo
    reactive_retries = 0

    while True:

        pre_compact_messages = copy.deepcopy(messages)

        messages[:] = tool_result_budget(messages)
        messages[:] = snip_compact(messages)
        messages[:] = micro_compact(messages)

        if estimate_size(messages) > CONTEXT_LIMIT:
            print("[auto compact]")
            messages[:] = compact_history(messages)

        if rounds_since_todo >=3:
            messages.append(
                {"role":"user",
                 "content":"<reminder> Update your todos.</reminder>"}
            )
            rounds_since_todo = 0
        
        context = update_context(context, messages)
        system = get_system_prompt(context)

        request_messages = build_request_messages_with_memories(messages)

        try:
            response = create_message_streaming(system, request_messages)
            reactive_retries = 0

        except Exception as e:
            if ("prompt too long" in str(e).lower() or "too many tokens" in str(e).lower()) and reactive_retries < MAX_REACTIVE_RETRIES:
                print("[reactive compact]")
                messages[:] = reactive_compact(messages)
                reactive_retries += 1
                continue
            raise

        messages.append({"role":"assistant","content":response.content})
        if response.stop_reason != "tool_use":
            force = trigger_hook("Stop",messages)
            if force:
                messages.append({"role":"user","content": force})
                continue

            extract_memories(pre_compact_messages)
            consolidate_memories()

            context = update_context(context, messages)
            return context
        
        rounds_since_todo += 1
        results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            blocked = trigger_hook("PreToolUse", block)
            if blocked:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": str(blocked)})
                continue

            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"

            trigger_hook("PostToolUse", block, output)

            if block.name == "todo_write":
                rounds_since_todo = 0
            
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
            
        messages.append({"role":"user","content":results})

def run_agent_turn(history:list, content:str, context:dict):
    history.append({"role":"user","content":content})
    context = agent_loop(history, context)
    print()
    return context

def create_message_streaming(system, request_messages):
      with client.messages.stream(
          model=MODEL,
          system=system,
          messages=request_messages,
          tools=TOOLS,
          max_tokens=8000,
      ) as stream:
          for text in stream.text_stream:
              print(text, end="", flush=True)

          print()
          return stream.get_final_message()

def main():
    print("欢迎使用最小功能Agent，输入 'q'，'exit'或 '空格符' 退出。")
    
    history = []
    context = update_context({}, [])
    resume_prompt = ask_resume_todos()
    if resume_prompt:
        context = run_agent_turn(history, resume_prompt, context)

    while True:
        try:
            query = input("\033[36m>> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        trigger_hook("UserPromptSubmit", query)
        context = run_agent_turn(history, query, context)

if __name__ == "__main__":
    main()
