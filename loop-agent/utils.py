"""工具函数模块 — 用于 Loop Agent 练习。

包含若干数据处理工具函数，其中有多个 bug 等待被发现和修复。
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


def calculate_moving_average(values: List[float], window: int) -> List[float]:
    """计算滑动平均值。

    Args:
        values: 数值列表
        window: 窗口大小（必须 >= 1）

    Returns:
        滑动平均值列表，长度与输入相同

    Examples:
        >>> calculate_moving_average([1, 2, 3, 4, 5], 3)
        [1.0, 1.5, 2.0, 3.0, 4.0]
    """
    if window < 1:
        raise ValueError("window must be >= 1")

    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start:i]  # BUG: 少取了一个元素，应该是 values[start:i+1]
        result.append(sum(chunk) / len(chunk))
    return result


def merge_sorted_lists(list1: List[int], list2: List[int]) -> List[int]:
    """合并两个已排序列表，返回新的已排序列表。

    Examples:
        >>> merge_sorted_lists([1, 3, 5], [2, 4, 6])
        [1, 2, 3, 4, 5, 6]
    """
    result = []
    i, j = 0, 0
    while i < len(list1) and j < len(list2):
        if list1[i] <= list2[j]:
            result.append(list1[i])
            i += 1
        else:
            result.append(list2[j])
            j += 1

    result.extend(list1[i:])
    # BUG: 漏掉了 list2 的剩余元素
    return result


def flatten_dict(d: Dict[str, Any], prefix: str = "", sep: str = ".") -> Dict[str, Any]:
    """将嵌套字典展平为单层字典。

    Examples:
        >>> flatten_dict({"a": {"b": 1, "c": 2}, "d": 3})
        {"a.b": 1, "a.c": 2, "d": 3}
    """
    result = {}
    for key, value in d.items():
        new_key = f"{prefix}{sep}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, new_key, sep))
        else:
            result[new_key] = value
    return result


def sanitize_filename(name: str) -> str:
    """清理文件名，移除不安全字符。

    保留字母、数字、连字符、下划线和点。
    空字符串返回 "unnamed"。

    Examples:
        >>> sanitize_filename("my file (1).txt")
        "my_file__1_.txt"
    """
    import re
    cleaned = re.sub(r'[^\w\-\.]', '_', name)
    # 移除开头的点（避免隐藏文件）
    cleaned = cleaned.lstrip('.')
    # BUG: 空字符串时没有兜底，直接返回空字符串
    return cleaned


def chunk_text(text: str, max_length: int) -> List[str]:
    """将文本按最大长度切分，优先在换行符处切分。

    Args:
        text: 待切分文本
        max_length: 每块最大字符数（必须 > 0）

    Returns:
        切分后的文本块列表

    Examples:
        >>> chunk_text("abc\\ndef\\nghi", 5)
        ["abc\\n", "def\\n", "ghi"]
    """
    if max_length <= 0:
        raise ValueError("max_length must be positive")

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_length
        if end >= len(text):
            chunks.append(text[start:])
            break

        # 尝试在最近的换行符处切分
        newline_pos = text.rfind('\n', start, end)
        if newline_pos > start:
            end = newline_pos
        # BUG: 当没有找到换行符时，end 应该回退到 start + max_length
        # 但这里 else 分支缺失，end 保持为 newline_pos 的值（可能是 -1+偏移）
        chunks.append(text[start:end])
        start = end

    return chunks


def count_words(text: str) -> Dict[str, int]:
    """统计文本中每个单词出现的次数（不区分大小写）。

    Examples:
        >>> count_words("Hello hello World")
        {"hello": 2, "world": 1}
    """
    words = text.split()
    result = {}
    for word in words:
        word = word.lower()
        # BUG: 使用了 result[word] + 1，但 key 不存在时会 KeyError
        # 应该用 result.get(word, 0) + 1 或 collections.Counter
        result[word] = result[word] + 1
    return result
