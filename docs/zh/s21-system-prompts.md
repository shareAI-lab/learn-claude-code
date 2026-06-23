# s21: System Prompts 分析

[中文](../../s21_system_prompts_analysis/README.md) · [English](../../s21_system_prompts_analysis/README.en.md)

s21 直接分析 Piebald-AI/claude-code-system-prompts 仓库，用 code.py 动态抓取、分类、统计 515+ 条真实提示词。

## 核心要点

- 数据来源：Piebald-AI 仓库（Claude Code v2.1.181，515+ 提示词）
- 分析方法：code.py 动态抓取 README.md，正则解析，分类聚合
- 设计模式：多阶段分解、条件组装、安全约束、记忆管理、Schema 驱动

## 运行

```sh
python s21_system_prompts_analysis/code.py
```

详见 [s21_system_prompts_analysis/README.md](../../s21_system_prompts_analysis/README.md)
