"""
config.py — 集中配置管理

加载 .env，定义常量和路径。所有模块从这里导入配置。
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(override=True)

# ── 目录路径 ──────────────────────────────────────────────
WORKDIR = Path(__file__).parent.absolute()       # loop-agent/ 目录
REPO_ROOT = WORKDIR.parent                        # 父仓库根目录
S20_DIR = REPO_ROOT / "s20_comprehensive"        # s20 课程目录
STATE_DIR = WORKDIR / "state"                     # 状态文件目录
SKILLS_DIR = WORKDIR / "skills"                   # 技能文件目录
MOCK_DATA_DIR = WORKDIR / "mock_data"             # Mock 数据目录

# 将 s20 加入 sys.path，使 `from code import ...` 可用
if str(S20_DIR) not in sys.path:
    sys.path.insert(0, str(S20_DIR))

# ── 状态文件 ──────────────────────────────────────────────
STATE_FILE = STATE_DIR / ".loop-state.json"

# ── 子代理轮次限制 ────────────────────────────────────────
MAKER_MAX_TURNS = 50
CHECKER_MAX_TURNS = 20

# ── 输出限制 ──────────────────────────────────────────────
MAX_DIFF_LENGTH = 5000
MAX_TEST_OUTPUT_LENGTH = 2000
MAX_CHECKER_RETRIES = 3
CRON_CHECK_INTERVAL = 60

# ── Token 预算 ─────────────────────────────────────────────
TOKEN_BUDGET = int(os.environ.get("TOKEN_BUDGET", "0"))  # 0 = 不限制

# ── GitHub 配置（Mock 模式下可忽略）────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "owner/repo")

# ── 验证 ──────────────────────────────────────────────────
def validate_config():
    """验证关键配置项存在。"""
    errors = []
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_BASE_URL"):
        errors.append("ANTHROPIC_API_KEY 或 ANTHROPIC_BASE_URL 未设置")
    if errors:
        raise RuntimeError(f"配置错误: {'; '.join(errors)}")
