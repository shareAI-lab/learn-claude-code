import ast
import types
import unittest
from pathlib import Path


def load_micro_compact():
    source = Path("agents/s06_context_compact.py").read_text()
    tree = ast.parse(source)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"KEEP_RECENT", "PRESERVE_RESULT_TOOLS"}:
                    selected.append(node)
                    break
        elif isinstance(node, ast.FunctionDef) and node.name == "micro_compact":
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {}
    exec(compile(module, "micro_compact_subset", "exec"), namespace)
    return namespace["micro_compact"], namespace["KEEP_RECENT"]


def make_tool_use(tool_use_id: str, name: str):
    return types.SimpleNamespace(type="tool_use", id=tool_use_id, name=name)


class MicroCompactTests(unittest.TestCase):
    def setUp(self):
        self.micro_compact, self.keep_recent = load_micro_compact()

    def test_preserves_old_read_file_results_but_compacts_old_command_output(self):
        long_read = "A" * 200
        long_bash = "B" * 200
        recent_1 = "C" * 200
        recent_2 = "D" * 200
        recent_3 = "E" * 200
        messages = [
            {"role": "assistant", "content": [make_tool_use("u1", "read_file")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u1", "content": long_read}]},
            {"role": "assistant", "content": [make_tool_use("u2", "bash")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u2", "content": long_bash}]},
            {"role": "assistant", "content": [make_tool_use("u3", "bash")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u3", "content": recent_1}]},
            {"role": "assistant", "content": [make_tool_use("u4", "read_file")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u4", "content": recent_2}]},
            {"role": "assistant", "content": [make_tool_use("u5", "edit_file")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u5", "content": recent_3}]},
        ]

        self.micro_compact(messages)

        self.assertEqual(messages[1]["content"][0]["content"], long_read)
        self.assertEqual(messages[3]["content"][0]["content"], "[Previous: used bash]")
        self.assertEqual(messages[5]["content"][0]["content"], recent_1)
        self.assertEqual(messages[7]["content"][0]["content"], recent_2)
        self.assertEqual(messages[9]["content"][0]["content"], recent_3)

    def test_does_nothing_when_tool_results_do_not_exceed_keep_recent(self):
        messages = [
            {"role": "assistant", "content": [make_tool_use("u1", "read_file")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u1", "content": "A" * 200}]},
            {"role": "assistant", "content": [make_tool_use("u2", "bash")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u2", "content": "B" * 200}]},
            {"role": "assistant", "content": [make_tool_use("u3", "edit_file")]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "u3", "content": "C" * 200}]},
        ]
        before = repr(messages)
        self.micro_compact(messages)
        self.assertEqual(repr(messages), before)
        self.assertEqual(self.keep_recent, 3)


if __name__ == "__main__":
    unittest.main()
