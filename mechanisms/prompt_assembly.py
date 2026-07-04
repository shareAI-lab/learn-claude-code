"""
mechanisms/prompt_assembly.py — Prompt Assembly mechanism, sourced from s10.

First-appearance rule: s10 introduces this inline (full version with cache-hit
logging and loaded-sections report). s11-s16 reuse it verbatim (verbose=True).
s17-s18 reuse the structure but silent (verbose=False — they dropped the cache
logging). s19-s20 extend ``assemble_system_prompt`` with lesson-specific
sections (MCP servers, skills catalog, current time) so they keep it inline.

Design — ``make_prompt_assembly(sections, verbose)`` returns a
``(assemble_system_prompt, get_system_prompt)`` tuple of closures bound to the
lesson's own ``PROMPT_SECTIONS`` dict (the ``tools`` string differs per
lesson because each lesson adds new tools). The ``get_system_prompt`` closure
carries its own memoization state.
"""

import json


def assemble_system_prompt(context: dict, sections: dict) -> str:
    """Join identity + tools + workspace, append memories if present.

    Pure function — no side effects, no logging. Shared by every variant.
    """
    parts = [sections["identity"], sections["tools"], sections["workspace"]]
    memories = context.get("memories", "")
    if memories:
        parts.append(f"Relevant memories:\n{memories}")
    return "\n\n".join(parts)


def make_prompt_assembly(sections: dict, verbose: bool = True):
    """Build (assemble_system_prompt, get_system_prompt) bound to *sections*.

    Args:
        sections: the lesson's PROMPT_SECTIONS dict (tools string is lesson-specific).
        verbose: True for s11-s16 (cache-hit + assembled-sections logging, matches
            s10's teaching version); False for s17-s18 (silent, matches their
            simplification).

    Returns:
        (assemble_system_prompt, get_system_prompt) — both module-level-style
        functions. ``get_system_prompt`` memoizes on the json-serialized context.
    """
    # Closure-private memoization state (avoids module-level globals that would
    # collide across lessons in the same process).
    state = {"key": None, "prompt": None}

    def _assemble(context: dict) -> str:
        return assemble_system_prompt(context, sections)

    def _get(context: dict) -> str:
        key = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str)
        if key == state["key"] and state["prompt"]:
            if verbose:
                print("  \033[90m[cache hit] system prompt unchanged\033[0m")
            return state["prompt"]
        state["key"] = key
        state["prompt"] = _assemble(context)
        if verbose:
            loaded = ["identity", "tools", "workspace"]
            if context.get("memories"):
                loaded.append("memory")
            print(f"  \033[32m[assembled] sections: {', '.join(loaded)}\033[0m")
        return state["prompt"]

    return _assemble, _get
