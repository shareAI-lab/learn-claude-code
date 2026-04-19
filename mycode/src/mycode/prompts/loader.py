"""Prompt 加载器: 从 prompts/{en,zh}/*.md 读取带变量占位符的模板。

设计:
- 所有 LLM 用的 prompt 都外置在仓库根的 prompts/ 目录
- en/ 和 zh/ 各放一份同名 .md;用户通过 config.prompt_lang 选(默认 en)
- 模板用 `{变量名}` 风格的占位符,str.format 展开
- 支持项目级覆盖: 若存在 `.mycode/prompts/{lang}/<name>.md` 则优先用它(允许用户微调)
- 找不到文件时给出清晰错误,便于调试
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


VALID_LANGS = ("en", "zh")
DEFAULT_LANG = "en"


def _prompts_base() -> Path:
    """返回内置 prompts 目录 (仓库根的 prompts/)。

    优先级: 运行时查找 src/mycode 上两级的 prompts/;
    若装成 wheel 后该路径不存在,fallback 到 importlib resources。
    """
    here = Path(__file__).resolve()
    # src/mycode/prompts/loader.py → 仓库根的 prompts/
    repo_prompts = here.parent.parent.parent.parent / "prompts"
    if repo_prompts.is_dir():
        return repo_prompts
    # package 内的 fallback(wheel 安装后)
    pkg_prompts = here.parent.parent / "prompts"
    return pkg_prompts


@dataclass
class PromptLoader:
    """加载 prompts 目录里的 .md 模板。

    查找顺序:
    1. 项目级覆盖: `<workspace>/.mycode/prompts/<lang>/<name>.md`
    2. 内置:       `<repo>/prompts/<lang>/<name>.md`
    3. 回退英文:    `<repo>/prompts/en/<name>.md`
    """

    lang: str = DEFAULT_LANG
    workspace_root: Path | None = None

    def __post_init__(self) -> None:
        if self.lang not in VALID_LANGS:
            self.lang = DEFAULT_LANG

    def _candidates(self, name: str) -> list[Path]:
        base = _prompts_base()
        paths: list[Path] = []
        if self.workspace_root is not None:
            paths.append(self.workspace_root / ".mycode" / "prompts" / self.lang / f"{name}.md")
        paths.append(base / self.lang / f"{name}.md")
        if self.lang != DEFAULT_LANG:
            paths.append(base / DEFAULT_LANG / f"{name}.md")
        return paths

    def load_raw(self, prompt_name: str, /) -> str:
        """读原始模板(不 format 变量)。positional-only 避免与模板变量冲突。"""
        for p in self._candidates(prompt_name):
            if p.is_file():
                return p.read_text(encoding="utf-8").rstrip("\n")
        raise FileNotFoundError(
            f"prompt '{prompt_name}' not found (lang={self.lang}); "
            f"tried: {', '.join(str(p) for p in self._candidates(prompt_name))}"
        )

    def render(self, prompt_name: str, /, **vars: Any) -> str:
        """读取并用变量展开。未用到的变量被忽略;缺少变量抛 KeyError。"""
        raw = self.load_raw(prompt_name)
        if not vars:
            return raw
        try:
            return raw.format(**vars)
        except KeyError as e:
            raise KeyError(
                f"prompt '{prompt_name}' references undefined variable {e}; "
                f"passed vars: {sorted(vars.keys())}"
            ) from None

    def available(self) -> list[str]:
        """列出当前语言下所有可用 prompt 名(不含路径和后缀)。"""
        base = _prompts_base() / self.lang
        if not base.is_dir():
            return []
        return sorted(p.stem for p in base.glob("*.md"))


@lru_cache(maxsize=8)
def _singleton(lang: str, workspace: str | None) -> PromptLoader:
    return PromptLoader(lang=lang, workspace_root=Path(workspace) if workspace else None)


def load_prompt(prompt_name: str, /, *, lang: str = DEFAULT_LANG, workspace: Path | None = None, **vars: Any) -> str:
    """便捷入口。所有模块走这个函数统一加载。

    首个参数用 positional-only (`/`) 防止与模板变量冲突
    (比如 teammate_system 模板里的 `{name}` 就会撞)。
    """
    key_ws = str(workspace) if workspace else None
    loader = _singleton(lang, key_ws)
    return loader.render(prompt_name, **vars)
