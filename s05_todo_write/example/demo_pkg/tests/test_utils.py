"""Unit tests for :mod:`demo_pkg.utils`.

Runs with the standard library only, from any working directory::

    python s05_todo_write/example/demo_pkg/tests/test_utils.py

It is also collectable by ``pytest`` when that is available.
"""

import sys
import unittest
from pathlib import Path

# Make ``demo_pkg`` importable no matter where this file is run from: the
# package's parent directory is ``s05_todo_write/example``.
EXAMPLE_DIR = Path(__file__).resolve().parents[2]
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))

import demo_pkg  # noqa: E402  (import must follow the sys.path setup)
from demo_pkg.utils import (  # noqa: E402  (import must follow the sys.path setup)
    ELLIPSIS,
    STATUS_MARKERS,
    VALID_STATUSES,
    count_by_status,
    normalize_title,
    render_progress,
    slugify,
    truncate,
)


class NormalizeTitleTests(unittest.TestCase):
    def test_collapses_whitespace_and_strips(self):
        self.assertEqual(
            normalize_title("  inspect \t the\n repo  "),
            "inspect the repo",
        )

    def test_accepts_already_clean_title(self):
        self.assertEqual(normalize_title("write tests"), "write tests")

    def test_rejects_empty_and_whitespace_only(self):
        for bad in ["", "   ", "\t\n"]:
            with self.subTest(title=bad):
                with self.assertRaises(ValueError):
                    normalize_title(bad)

    def test_rejects_non_string(self):
        for bad in [None, 42, ["a"]]:
            with self.subTest(title=bad):
                with self.assertRaises(TypeError):
                    normalize_title(bad)


class SlugifyTests(unittest.TestCase):
    def test_builds_hyphen_separated_slug(self):
        self.assertEqual(slugify("Inspect the Repo!"), "inspect-the-repo")

    def test_collapses_repeated_separators(self):
        self.assertEqual(slugify("fix  ---  flaky test"), "fix-flaky-test")

    def test_keeps_digits(self):
        self.assertEqual(slugify("issue 340"), "issue-340")

    def test_rejects_text_without_letters_or_digits(self):
        with self.assertRaises(ValueError):
            slugify("!!!")

    def test_rejects_empty_title(self):
        with self.assertRaises(ValueError):
            slugify("   ")


class TruncateTests(unittest.TestCase):
    def test_returns_short_text_unchanged(self):
        self.assertEqual(truncate("short", 10), "short")

    def test_returns_text_exactly_at_limit_unchanged(self):
        self.assertEqual(truncate("exact", 5), "exact")

    def test_truncates_and_fits_within_limit(self):
        result = truncate("a very long todo title", 10)
        self.assertEqual(result, "a very ...")
        self.assertEqual(len(result), 10)

    def test_limit_equal_to_ellipsis_length(self):
        self.assertEqual(truncate("anything", len(ELLIPSIS)), ELLIPSIS)

    def test_rejects_limit_below_ellipsis_length(self):
        with self.assertRaises(ValueError):
            truncate("anything", 2)

    def test_rejects_non_int_limit_including_bool(self):
        for bad in ["5", 5.0, True]:
            with self.subTest(limit=bad):
                with self.assertRaises(TypeError):
                    truncate("anything", bad)

    def test_rejects_non_string_text(self):
        with self.assertRaises(TypeError):
            truncate(None, 5)


class CountByStatusTests(unittest.TestCase):
    def test_counts_each_status(self):
        items = [
            {"content": "a", "status": "completed"},
            {"content": "b", "status": "in_progress"},
            {"content": "c", "status": "completed"},
        ]
        self.assertEqual(
            count_by_status(items),
            {"pending": 0, "in_progress": 1, "completed": 2},
        )

    def test_empty_input_returns_all_zero_keys(self):
        self.assertEqual(
            count_by_status([]),
            {status: 0 for status in VALID_STATUSES},
        )

    def test_result_key_order_matches_valid_statuses(self):
        self.assertEqual(list(count_by_status([])), list(VALID_STATUSES))

    def test_accepts_any_iterable_once(self):
        items = ({"status": "pending"} for _ in range(3))
        self.assertEqual(count_by_status(items)["pending"], 3)

    def test_rejects_invalid_status(self):
        with self.assertRaises(ValueError):
            count_by_status([{"content": "a", "status": "done"}])

    def test_rejects_item_without_status_key(self):
        with self.assertRaises(TypeError):
            count_by_status([{"content": "a"}])

    def test_rejects_non_mapping_item(self):
        with self.assertRaises(TypeError):
            count_by_status(["not a mapping"])


class RenderProgressTests(unittest.TestCase):
    def test_renders_summary_and_markers(self):
        items = [
            {"content": "inspect repo", "status": "completed"},
            {"content": "write tests", "status": "in_progress"},
        ]
        result = render_progress(items)
        self.assertTrue(result.startswith("(1/2 completed)"))
        self.assertIn("[x] inspect repo", result)
        self.assertIn("[>] write tests", result)

    def test_empty_input_renders_summary_only(self):
        self.assertEqual(render_progress([]), "(0/0 completed)")

    def test_every_valid_status_has_a_marker(self):
        self.assertEqual(set(STATUS_MARKERS), set(VALID_STATUSES))

    def test_rejects_item_without_content_key(self):
        with self.assertRaises(TypeError):
            render_progress([{"status": "pending"}])

    def test_rejects_invalid_status(self):
        with self.assertRaises(ValueError):
            render_progress([{"content": "a", "status": "done"}])


class PackageSurfaceTests(unittest.TestCase):
    def test_package_reexports_the_same_objects(self):
        self.assertIs(demo_pkg.count_by_status, count_by_status)
        self.assertIs(demo_pkg.normalize_title, normalize_title)
        self.assertIs(demo_pkg.truncate, truncate)

    def test_dunder_all_entries_all_resolve(self):
        for name in demo_pkg.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(demo_pkg, name))

    def test_expected_public_names_are_exported(self):
        expected = {
            "__version__",
            "ELLIPSIS",
            "STATUS_MARKERS",
            "VALID_STATUSES",
            "count_by_status",
            "normalize_title",
            "render_progress",
            "slugify",
            "truncate",
        }
        self.assertEqual(set(demo_pkg.__all__), expected)


if __name__ == "__main__":
    unittest.main()
