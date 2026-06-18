"""tests/test_config.py — 配置验证测试"""

import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_validate_config_missing_key():
    """缺少 API key 时应抛出 RuntimeError。"""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "ANTHROPIC_BASE_URL": ""}, clear=False):
        with patch("config.os.environ.get") as mock_get:
            mock_get.side_effect = lambda k, d="": {"ANTHROPIC_API_KEY": "", "ANTHROPIC_BASE_URL": ""}.get(k, d)
            from config import validate_config
            with pytest.raises(RuntimeError):
                validate_config()


def test_validate_config_with_key():
    """有 API key 时应正常通过。"""
    from config import validate_config
    with patch("config.os.environ.get") as mock_get:
        mock_get.side_effect = lambda k, d="": {"ANTHROPIC_API_KEY": "sk-test-key", "ANTHROPIC_BASE_URL": ""}.get(k, d)
        validate_config()  # 不应抛出异常


def test_validate_config_with_base_url():
    """有 ANTHROPIC_BASE_URL 时应正常通过（无需 API key）。"""
    from config import validate_config
    with patch("config.os.environ.get") as mock_get:
        mock_get.side_effect = lambda k, d="": {"ANTHROPIC_API_KEY": "", "ANTHROPIC_BASE_URL": "http://localhost:8080"}.get(k, d)
        validate_config()  # 不应抛出异常


def test_constants_defined():
    """配置常量应已定义且为合理值。"""
    from config import (
        MAKER_MAX_TURNS, CHECKER_MAX_TURNS,
        MAX_DIFF_LENGTH, MAX_TEST_OUTPUT_LENGTH,
        MAX_CHECKER_RETRIES, CRON_CHECK_INTERVAL,
    )
    assert MAKER_MAX_TURNS > 0
    assert CHECKER_MAX_TURNS > 0
    assert MAX_DIFF_LENGTH > 0
    assert MAX_TEST_OUTPUT_LENGTH > 0
    assert MAX_CHECKER_RETRIES >= 0
    assert CRON_CHECK_INTERVAL > 0
