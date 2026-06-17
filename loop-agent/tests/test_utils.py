"""utils.py 的单元测试。"""

import pytest
from utils import (
    calculate_moving_average,
    merge_sorted_lists,
    flatten_dict,
    sanitize_filename,
    chunk_text,
    count_words,
)


class TestCalculateMovingAverage:
    def test_basic(self):
        result = calculate_moving_average([1, 2, 3, 4, 5], 3)
        assert result == [1.0, 1.5, 2.0, 3.0, 4.0]

    def test_single_element(self):
        result = calculate_moving_average([10], 1)
        assert result == [10.0]

    def test_window_larger_than_data(self):
        result = calculate_moving_average([1, 2, 3], 5)
        assert result == [1.0, 1.5, 2.0]

    def test_empty_list(self):
        result = calculate_moving_average([], 3)
        assert result == []

    def test_window_of_1(self):
        result = calculate_moving_average([10, 20, 30], 1)
        assert result == [10.0, 20.0, 30.0]

    def test_invalid_window(self):
        with pytest.raises(ValueError):
            calculate_moving_average([1, 2, 3], 0)


class TestMergeSortedLists:
    def test_basic(self):
        result = merge_sorted_lists([1, 3, 5], [2, 4, 6])
        assert result == [1, 2, 3, 4, 5, 6]

    def test_first_empty(self):
        result = merge_sorted_lists([], [1, 2, 3])
        assert result == [1, 2, 3]

    def test_second_empty(self):
        result = merge_sorted_lists([1, 2, 3], [])
        assert result == [1, 2, 3]

    def test_both_empty(self):
        result = merge_sorted_lists([], [])
        assert result == []

    def test_different_lengths(self):
        result = merge_sorted_lists([1, 2], [3, 4, 5, 6])
        assert result == [1, 2, 3, 4, 5, 6]

    def test_duplicates(self):
        result = merge_sorted_lists([1, 2, 2], [2, 3, 3])
        assert result == [1, 2, 2, 2, 3, 3]


class TestFlattenDict:
    def test_basic(self):
        result = flatten_dict({"a": {"b": 1, "c": 2}, "d": 3})
        assert result == {"a.b": 1, "a.c": 2, "d": 3}

    def test_deeply_nested(self):
        result = flatten_dict({"a": {"b": {"c": 1}}})
        assert result == {"a.b.c": 1}

    def test_flat_dict(self):
        result = flatten_dict({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_custom_separator(self):
        result = flatten_dict({"a": {"b": 1}}, sep="/")
        assert result == {"a/b": 1}

    def test_empty_dict(self):
        result = flatten_dict({})
        assert result == {}


class TestSanitizeFilename:
    def test_basic(self):
        result = sanitize_filename("my file (1).txt")
        assert result == "my_file__1_.txt"

    def test_leading_dots(self):
        result = sanitize_filename("...hidden")
        assert result == "hidden"

    def test_empty_string(self):
        result = sanitize_filename("")
        assert result == "unnamed"

    def test_only_dots(self):
        result = sanitize_filename("...")
        assert result == "unnamed"

    def test_safe_filename(self):
        result = sanitize_filename("readme.md")
        assert result == "readme.md"


class TestChunkText:
    def test_basic(self):
        result = chunk_text("abc\ndef\nghi", 5)
        assert result == ["abc\n", "def\n", "ghi"]

    def test_no_newlines(self):
        result = chunk_text("abcdefghij", 3)
        assert result == ["abc", "def", "ghi", "j"]

    def test_single_chunk(self):
        result = chunk_text("abc", 10)
        assert result == ["abc"]

    def test_empty_string(self):
        result = chunk_text("", 10)
        assert result == []

    def test_invalid_max_length(self):
        with pytest.raises(ValueError):
            chunk_text("abc", 0)


class TestCountWords:
    def test_basic(self):
        result = count_words("Hello hello World")
        assert result == {"hello": 2, "world": 1}

    def test_empty_string(self):
        result = count_words("")
        assert result == {}

    def test_single_word(self):
        result = count_words("Python")
        assert result == {"python": 1}

    def test_case_insensitive(self):
        result = count_words("Go GO gO")
        assert result == {"go": 3}

    def test_punctuation(self):
        result = count_words("hello, world! hello!")
        assert result == {"hello,": 1, "world!": 1, "hello!": 1}
