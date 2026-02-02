"""
Unit tests for learn-claude-code agents.

These tests don't require API calls - they verify code structure and logic.
"""
import os
import sys
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Import Tests
# =============================================================================

def test_imports():
    """Test that all agent modules can be imported."""
    agents = [
        "v0_bash_agent",
        "v0_bash_agent_mini",
        "v1_basic_agent",
        "v2_todo_agent",
        "v3_subagent",
        "v4_skills_agent"
    ]

    for agent in agents:
        spec = importlib.util.find_spec(agent)
        assert spec is not None, f"Failed to find {agent}"
        print(f"  Found: {agent}")

    print("PASS: test_imports")
    return True


# =============================================================================
# TodoManager Tests
# =============================================================================

def test_todo_manager_basic():
    """Test TodoManager basic operations."""
    from v2_todo_agent import TodoManager

    tm = TodoManager()

    # Test valid update
    result = tm.update([
        {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
        {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
    ])

    assert "Task 1" in result
    assert "Task 2" in result
    assert len(tm.items) == 2

    print("PASS: test_todo_manager_basic")
    return True


def test_todo_manager_constraints():
    """Test TodoManager enforces constraints."""
    from v2_todo_agent import TodoManager

    tm = TodoManager()

    # Test: only one in_progress allowed (should raise or return error)
    try:
        result = tm.update([
            {"content": "Task 1", "status": "in_progress", "activeForm": "Doing 1"},
            {"content": "Task 2", "status": "in_progress", "activeForm": "Doing 2"},
        ])
        # If no exception, check result contains error
        assert "Error" in result or "error" in result.lower()
    except ValueError as e:
        # Exception is expected - constraint enforced
        assert "in_progress" in str(e).lower()

    # Test: max 20 items
    tm2 = TodoManager()
    many_items = [{"content": f"Task {i}", "status": "pending", "activeForm": f"Doing {i}"} for i in range(25)]
    try:
        tm2.update(many_items)
    except ValueError:
        pass  # Exception is fine
    assert len(tm2.items) <= 20

    print("PASS: test_todo_manager_constraints")
    return True


# =============================================================================
# Reminder Tests
# =============================================================================

def test_reminder_constants():
    """Test reminder constants are defined correctly."""
    from v2_todo_agent import INITIAL_REMINDER, NAG_REMINDER

    assert "<reminder>" in INITIAL_REMINDER
    assert "</reminder>" in INITIAL_REMINDER
    assert "<reminder>" in NAG_REMINDER
    assert "</reminder>" in NAG_REMINDER
    assert "todo" in NAG_REMINDER.lower() or "Todo" in NAG_REMINDER

    print("PASS: test_reminder_constants")
    return True


def test_nag_reminder_in_agent_loop():
    """Test NAG_REMINDER injection is inside agent_loop."""
    import inspect
    from v2_todo_agent import agent_loop, NAG_REMINDER

    source = inspect.getsource(agent_loop)

    # NAG_REMINDER should be referenced in agent_loop
    assert "NAG_REMINDER" in source, "NAG_REMINDER should be in agent_loop"
    assert "rounds_without_todo" in source, "rounds_without_todo check should be in agent_loop"
    assert "messages.append" in source or "messages.insert" in source, "Should inject into messages"

    print("PASS: test_nag_reminder_in_agent_loop")
    return True


# =============================================================================
# Configuration Tests
# =============================================================================

def test_env_config():
    """Test environment variable configuration."""
    # Save original values
    orig_model = os.environ.get("MODEL_ID")
    orig_base = os.environ.get("OPENAI_BASE_URL")

    try:
        # Set test values
        os.environ["MODEL_ID"] = "test-model-123"
        os.environ["OPENAI_BASE_URL"] = "https://test.example.com"

        # Re-import to pick up new env vars
        import importlib
        import v1_basic_agent
        importlib.reload(v1_basic_agent)

        assert v1_basic_agent.MODEL == "test-model-123", f"MODEL should be test-model-123, got {v1_basic_agent.MODEL}"

        print("PASS: test_env_config")
        return True

    finally:
        # Restore original values
        if orig_model:
            os.environ["MODEL_ID"] = orig_model
        else:
            os.environ.pop("MODEL_ID", None)
        if orig_base:
            os.environ["OPENAI_BASE_URL"] = orig_base
        else:
            os.environ.pop("OPENAI_BASE_URL", None)


def test_default_model():
    """Test default model when env var not set."""
    orig = os.environ.pop("MODEL_ID", None)

    try:
        import importlib
        import v1_basic_agent
        importlib.reload(v1_basic_agent)

        assert "claude" in v1_basic_agent.MODEL.lower(), f"Default model should contain 'claude': {v1_basic_agent.MODEL}"

        print("PASS: test_default_model")
        return True

    finally:
        if orig:
            os.environ["MODEL_ID"] = orig


# =============================================================================
# Tool Schema Tests
# =============================================================================

def test_tool_schemas():
    """Test tool schemas are valid."""
    from v1_basic_agent import TOOLS

    required_tools = {"bash", "read_file", "write_file", "edit_file"}
    tool_names = {t["function"]["name"] for t in TOOLS}

    assert required_tools.issubset(tool_names), f"Missing tools: {required_tools - tool_names}"

    for tool in TOOLS:
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]
        assert tool["function"]["parameters"].get("type") == "object"

    print("PASS: test_tool_schemas")
    return True


# =============================================================================
# TodoManager Edge Case Tests
# =============================================================================

def test_todo_manager_empty_list():
    """Test TodoManager handles empty list."""
    from v2_todo_agent import TodoManager

    tm = TodoManager()
    result = tm.update([])

    assert "No todos" in result or len(tm.items) == 0
    print("PASS: test_todo_manager_empty_list")
    return True


def test_todo_manager_status_transitions():
    """Test TodoManager status transitions."""
    from v2_todo_agent import TodoManager

    tm = TodoManager()

    # Start with pending
    tm.update([{"content": "Task", "status": "pending", "activeForm": "Doing task"}])
    assert tm.items[0]["status"] == "pending"

    # Move to in_progress
    tm.update([{"content": "Task", "status": "in_progress", "activeForm": "Doing task"}])
    assert tm.items[0]["status"] == "in_progress"

    # Complete
    tm.update([{"content": "Task", "status": "completed", "activeForm": "Doing task"}])
    assert tm.items[0]["status"] == "completed"

    print("PASS: test_todo_manager_status_transitions")
    return True


def test_todo_manager_missing_fields():
    """Test TodoManager rejects items with missing fields."""
    from v2_todo_agent import TodoManager

    tm = TodoManager()

    # Missing content
    try:
        tm.update([{"status": "pending", "activeForm": "Doing"}])
        assert False, "Should reject missing content"
    except ValueError:
        pass

    # Missing activeForm
    try:
        tm.update([{"content": "Task", "status": "pending"}])
        assert False, "Should reject missing activeForm"
    except ValueError:
        pass

    print("PASS: test_todo_manager_missing_fields")
    return True


def test_todo_manager_invalid_status():
    """Test TodoManager rejects invalid status values."""
    from v2_todo_agent import TodoManager

    tm = TodoManager()

    try:
        tm.update([{"content": "Task", "status": "invalid", "activeForm": "Doing"}])
        assert False, "Should reject invalid status"
    except ValueError as e:
        assert "status" in str(e).lower()

    print("PASS: test_todo_manager_invalid_status")
    return True


def test_todo_manager_render_format():
    """Test TodoManager render format."""
    from v2_todo_agent import TodoManager

    tm = TodoManager()
    tm.update([
        {"content": "Task A", "status": "completed", "activeForm": "A"},
        {"content": "Task B", "status": "in_progress", "activeForm": "B"},
        {"content": "Task C", "status": "pending", "activeForm": "C"},
    ])

    result = tm.render()
    assert "[x] Task A" in result
    assert "[>] Task B" in result
    assert "[ ] Task C" in result
    assert "1/3" in result  # Format may vary: "done" or "completed"

    print("PASS: test_todo_manager_render_format")
    return True


# =============================================================================
# v3 Agent Type Registry Tests
# =============================================================================

def test_v3_agent_types_structure():
    """Test v3 AGENT_TYPES structure."""
    from v3_subagent import AGENT_TYPES

    required_types = {"explore", "code", "plan"}
    assert set(AGENT_TYPES.keys()) == required_types

    for name, config in AGENT_TYPES.items():
        assert "description" in config, f"{name} missing description"
        assert "tools" in config, f"{name} missing tools"
        assert "prompt" in config, f"{name} missing prompt"

    print("PASS: test_v3_agent_types_structure")
    return True


def test_v3_get_tools_for_agent():
    """Test v3 get_tools_for_agent filters correctly."""
    from v3_subagent import get_tools_for_agent, BASE_TOOLS

    # explore: read-only
    explore_tools = get_tools_for_agent("explore")
    explore_names = {t["function"]["name"] for t in explore_tools}
    assert "bash" in explore_names
    assert "read_file" in explore_names
    assert "write_file" not in explore_names
    assert "edit_file" not in explore_names

    # code: all base tools
    code_tools = get_tools_for_agent("code")
    assert len(code_tools) == len(BASE_TOOLS)

    # plan: read-only
    plan_tools = get_tools_for_agent("plan")
    plan_names = {t["function"]["name"] for t in plan_tools}
    assert "write_file" not in plan_names

    print("PASS: test_v3_get_tools_for_agent")
    return True


def test_v3_get_agent_descriptions():
    """Test v3 get_agent_descriptions output."""
    from v3_subagent import get_agent_descriptions

    desc = get_agent_descriptions()
    assert "explore" in desc
    assert "code" in desc
    assert "plan" in desc
    assert "Read-only" in desc or "read" in desc.lower()

    print("PASS: test_v3_get_agent_descriptions")
    return True


def test_v3_task_tool_schema():
    """Test v3 Task tool schema."""
    from v3_subagent import TASK_TOOL, AGENT_TYPES

    assert TASK_TOOL["function"]["name"] == "Task"
    schema = TASK_TOOL["function"]["parameters"]
    assert "description" in schema["properties"]
    assert "prompt" in schema["properties"]
    assert "agent_type" in schema["properties"]
    assert set(schema["properties"]["agent_type"]["enum"]) == set(AGENT_TYPES.keys())

    print("PASS: test_v3_task_tool_schema")
    return True


# =============================================================================
# v4 SkillLoader Tests
# =============================================================================

def test_v4_skill_loader_init():
    """Test v4 SkillLoader initialization."""
    from v4_skills_agent import SkillLoader
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Empty skills dir
        loader = SkillLoader(Path(tmpdir))
        assert len(loader.skills) == 0

    print("PASS: test_v4_skill_loader_init")
    return True


def test_v4_skill_loader_parse_valid():
    """Test v4 SkillLoader parses valid SKILL.md."""
    from v4_skills_agent import SkillLoader
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test
description: A test skill for testing
---

# Test Skill

This is the body content.
""")

        loader = SkillLoader(Path(tmpdir))
        assert "test" in loader.skills
        assert loader.skills["test"]["description"] == "A test skill for testing"
        assert "body content" in loader.skills["test"]["body"]

    print("PASS: test_v4_skill_loader_parse_valid")
    return True


def test_v4_skill_loader_parse_invalid():
    """Test v4 SkillLoader rejects invalid SKILL.md."""
    from v4_skills_agent import SkillLoader
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "bad-skill"
        skill_dir.mkdir()

        # Missing frontmatter
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# No frontmatter\n\nJust content.")

        loader = SkillLoader(Path(tmpdir))
        assert "bad-skill" not in loader.skills

    print("PASS: test_v4_skill_loader_parse_invalid")
    return True


def test_v4_skill_loader_get_content():
    """Test v4 SkillLoader get_skill_content."""
    from v4_skills_agent import SkillLoader
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "demo"
        skill_dir.mkdir()

        (skill_dir / "SKILL.md").write_text("""---
name: demo
description: Demo skill
---

# Demo Instructions

Step 1: Do this
Step 2: Do that
""")

        # Add resources
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "helper.sh").write_text("#!/bin/bash\necho hello")

        loader = SkillLoader(Path(tmpdir))

        content = loader.get_skill_content("demo")
        assert content is not None
        assert "Demo Instructions" in content
        assert "helper.sh" in content  # Resources listed

        # Non-existent skill
        assert loader.get_skill_content("nonexistent") is None

    print("PASS: test_v4_skill_loader_get_content")
    return True


def test_v4_skill_loader_list_skills():
    """Test v4 SkillLoader list_skills."""
    from v4_skills_agent import SkillLoader
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two skills
        for name in ["alpha", "beta"]:
            skill_dir = Path(tmpdir) / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"""---
name: {name}
description: {name} skill
---

Content for {name}
""")

        loader = SkillLoader(Path(tmpdir))
        skills = loader.list_skills()
        assert "alpha" in skills
        assert "beta" in skills
        assert len(skills) == 2

    print("PASS: test_v4_skill_loader_list_skills")
    return True


def test_v4_skill_tool_schema():
    """Test v4 Skill tool schema."""
    from v4_skills_agent import SKILL_TOOL

    assert SKILL_TOOL["function"]["name"] == "Skill"
    schema = SKILL_TOOL["function"]["parameters"]
    assert "skill" in schema["properties"]
    assert "skill" in schema["required"]

    print("PASS: test_v4_skill_tool_schema")
    return True


# =============================================================================
# Path Safety Tests
# =============================================================================

def test_v3_safe_path():
    """Test v3 safe_path prevents path traversal."""
    from v3_subagent import safe_path, WORKDIR

    # Valid path
    p = safe_path("test.txt")
    assert str(p).startswith(str(WORKDIR))

    # Path traversal attempt
    try:
        safe_path("../../../etc/passwd")
        assert False, "Should reject path traversal"
    except ValueError as e:
        assert "escape" in str(e).lower()

    print("PASS: test_v3_safe_path")
    return True


# =============================================================================
# Configuration Tests (Extended)
# =============================================================================

def test_base_url_config():
    """Test OPENAI_BASE_URL configuration."""
    orig = os.environ.get("OPENAI_BASE_URL")

    try:
        os.environ["OPENAI_BASE_URL"] = "https://custom.api.com"

        import importlib
        import v1_basic_agent
        importlib.reload(v1_basic_agent)

        # Check client was created (we can't easily verify base_url without mocking)
        assert v1_basic_agent.client is not None

        print("PASS: test_base_url_config")
        return True

    finally:
        if orig:
            os.environ["OPENAI_BASE_URL"] = orig
        else:
            os.environ.pop("OPENAI_BASE_URL", None)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    tests = [
        # Basic tests
        test_imports,
        test_todo_manager_basic,
        test_todo_manager_constraints,
        test_reminder_constants,
        test_nag_reminder_in_agent_loop,
        test_env_config,
        test_default_model,
        test_tool_schemas,
        # TodoManager edge cases
        test_todo_manager_empty_list,
        test_todo_manager_status_transitions,
        test_todo_manager_missing_fields,
        test_todo_manager_invalid_status,
        test_todo_manager_render_format,
        # v3 tests
        test_v3_agent_types_structure,
        test_v3_get_tools_for_agent,
        test_v3_get_agent_descriptions,
        test_v3_task_tool_schema,
        # v4 tests
        test_v4_skill_loader_init,
        test_v4_skill_loader_parse_valid,
        test_v4_skill_loader_parse_invalid,
        test_v4_skill_loader_get_content,
        test_v4_skill_loader_list_skills,
        test_v4_skill_tool_schema,
        # Security tests
        test_v3_safe_path,
        # Config tests
        test_base_url_config,
    ]

    failed = []
    for test_fn in tests:
        name = test_fn.__name__
        print(f"\n{'='*50}")
        print(f"Running: {name}")
        print('='*50)
        try:
            if not test_fn():
                failed.append(name)
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed.append(name)

    print(f"\n{'='*50}")
    print(f"Results: {len(tests) - len(failed)}/{len(tests)} passed")
    print('='*50)

    if failed:
        print(f"FAILED: {failed}")
        sys.exit(1)
    else:
        print("All unit tests passed!")
        sys.exit(0)
