import json
import re
import time
from dataclasses import dataclass
from pathlib import Path


MEMORY_TYPES = ["user", "feedback", "project", "reference"]
CONSOLIDATE_THRESHOLD = 10


@dataclass(frozen=True, slots=True)
class MemoryStore:
    root: Path
    index_path: Path


def _parse_memory_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    metadata = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, parts[2].strip()


def write_memory_file(
    store: MemoryStore,
    name: str,
    memory_type: str,
    description: str,
    body: str,
):
    slug = name.lower().replace(" ", "-").replace("/", "-")
    path = store.root / f"{slug}.md"
    store.root.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\ntype: {memory_type}\n---\n\n{body}\n"
    )
    rebuild_index(store)
    return path


def rebuild_index(store: MemoryStore):
    lines = []
    for path in sorted(store.root.glob("*.md")):
        if path.name == "MEMORY.md":
            continue
        raw = path.read_text()
        metadata, body = _parse_memory_frontmatter(raw)
        name = metadata.get("name", path.stem)
        description = metadata.get("description", body.split("\n")[0][:80])
        lines.append(f"- [{name}]({path.name}) — {description}")
    store.index_path.write_text("\n".join(lines) + "\n" if lines else "")


def read_memory_index(store: MemoryStore) -> str:
    if not store.index_path.exists():
        return ""
    text = store.index_path.read_text().strip()
    return text if text else ""


def read_memory_file(store: MemoryStore, filename: str) -> str | None:
    path = store.root / filename
    if not path.exists():
        return None
    return path.read_text()


def list_memory_files(store: MemoryStore) -> list[dict]:
    result = []
    if not store.root.exists():
        return result
    for path in sorted(store.root.glob("*.md")):
        if path.name == "MEMORY.md":
            continue
        raw = path.read_text()
        metadata, body = _parse_memory_frontmatter(raw)
        result.append(
            {
                "filename": path.name,
                "name": metadata.get("name", path.stem),
                "description": metadata.get("description", ""),
                "type": metadata.get("type", "user"),
                "body": body,
            }
        )
    return result


def is_internal_reminder_text(text: str) -> bool:
    text = text.strip().lower()
    return text.startswith("<reminder>") or text.startswith("</reminder>")


def select_relevant_memories(
    store: MemoryStore,
    messages: list,
    summarize,
    max_items: int = 5,
) -> list[str]:
    files = list_memory_files(store)
    if not files:
        return []
    recent_texts = []
    for message in reversed(messages):
        content = message.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(getattr(block, "text", ""))
                for block in content
                if getattr(block, "type", None) == "text"
            )
        if is_internal_reminder_text(content.strip()):
            continue
        if isinstance(content, str):
            recent_texts.append(content)
        if len(recent_texts) >= 5:
            break
    recent = " ".join(reversed(recent_texts))[:2000]
    if not recent.strip():
        return []
    catalog = "\n".join(
        f"{index}: {file['name']} — {file['description']}"
        for index, file in enumerate(files)
    )
    prompt = (
        "Given the recent conversation and the memory catalog below, "
        "select the indices of memories that are clearly relevant. "
        "Return ONLY a JSON array of integers, e.g. [0, 3]. "
        "If none are relevant, return [].\n\n"
        f"Recent conversation:\n{recent}\n\nMemory catalog:\n{catalog}"
    )
    try:
        text = summarize(prompt, 200).strip()
        match = re.search(r"\[.*?\]", text, re.DOTALL)
        if match:
            indices = json.loads(match.group())
            selected = []
            for index in indices:
                if isinstance(index, int) and 0 <= index < len(files):
                    selected.append(files[index]["filename"])
                    if len(selected) >= max_items:
                        break
            return selected
    except Exception:
        pass
    keywords = [word.lower() for word in recent.split() if len(word) > 3]
    selected = []
    for file in files:
        text = (file["name"] + " " + file["description"]).lower()
        if any(keyword in text for keyword in keywords):
            selected.append(file["filename"])
            if len(selected) >= max_items:
                break
    return selected


def load_memories(store: MemoryStore, messages: list, summarize) -> str:
    selected_files = select_relevant_memories(store, messages, summarize)
    if not selected_files:
        return ""
    parts = ["<relevant_memories>"]
    for filename in selected_files:
        content = read_memory_file(store, filename)
        if content:
            parts.append(content)
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)


def extract_memories(store: MemoryStore, messages: list, summarize) -> list[dict]:
    dialogue_parts = []
    for message in messages:
        role = message.get("role", "?")
        content = message.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(getattr(block, "text", ""))
                for block in content
                if getattr(block, "type", None) == "text"
            )
        if isinstance(content, str) and content.strip():
            if role == "user" and is_internal_reminder_text(content.strip()):
                continue
            dialogue_parts.append(f"{role}: {content}")
    dialogue = "\n".join(dialogue_parts)
    if not dialogue.strip():
        return
    existing = list_memory_files(store)
    existing_description = (
        "\n".join(f"- {item['name']}: {item['description']}" for item in existing)
        if existing
        else "(none)"
    )
    prompt = (
        "Extract user preferences, constraints, or project facts from this dialogue.\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n"
        "- name: short kebab-case identifier (e.g. 'user-preference-tabs')\n"
        "- type: one of 'user' (user preference), 'feedback' (guidance), "
        "'project' (project fact), 'reference' (external pointer)\n"
        "- description: one-line summary for index lookup\n"
        "- body: full detail in markdown\n"
        "If nothing new or already covered by existing memories, return [].\n\n"
        f"Existing memories:\n{existing_description}\n\nDialogue:\n{dialogue[:4000]}"
    )
    try:
        text = summarize(prompt, 800).strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        if not items:
            return
        count = 0
        for memory in items:
            name = memory.get("name", f"memory_{int(time.time())}")
            memory_type = memory.get("type", "user")
            description = memory.get("description", "")
            body = memory.get("body", "")
            if description and body:
                write_memory_file(store, name, memory_type, description, body)
                count += 1
        if count:
            print(f"\n\033[33m[Memory: extracted {count} new memories]\033[0m")
    except Exception:
        pass


def consolidate_memories(store: MemoryStore, summarize):
    files = list_memory_files(store)
    if len(files) < CONSOLIDATE_THRESHOLD:
        return
    catalog = "\n".join(
        f"## {file['filename']}\nname: {file['name']}\n"
        f"description: {file['description']}\n{file['body']}"
        for file in files
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
        text = summarize(prompt, 3000).strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        for path in store.root.glob("*.md"):
            if path.name != "MEMORY.md":
                path.unlink()
        for memory in items:
            name = memory.get("name", f"memory_{int(time.time())}")
            memory_type = memory.get("type", "user")
            description = memory.get("description", "")
            body = memory.get("body", "")
            if description and body:
                write_memory_file(store, name, memory_type, description, body)
        print(
            f"\n\033[33m[Memory: consolidated {len(files)} → {len(items)} memories]\033[0m"
        )
    except Exception:
        pass


def find_latest_text_user_message(messages: list) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        if content.strip().startswith("<reminder>"):
            continue
        return index
    return None


def build_request_messages_with_memories(
    store: MemoryStore,
    messages: list,
    summarize,
):
    memories = load_memories(store, messages, summarize)
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
