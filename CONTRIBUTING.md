# 贡献指南

感谢你对 learn-claude-code 项目的关注！本文档指导你如何参与贡献。

## 贡献流程

### 1. Fork 与 Clone
```sh
gh repo fork shareAI-lab/learn-claude-code --clone
cd learn-claude-code
```

### 2. 创建分支
```sh
git checkout -b fix/issue-<编号>-<简述>
# 或
git checkout -b docs/<简述>
git checkout -b test/<简述>
```

### 3. 开发与测试
```sh
# Python 代码验证
python -m py_compile agents/<file>.py
python -m pytest tests -q

# Web 前端验证
cd web && npm ci && npm run build
```

### 4. 提交规范
提交信息格式：`<type>(<scope>): <description>`

| type | 说明 |
|------|------|
| fix | Bug 修复 |
| feat | 新功能 |
| docs | 文档变更 |
| test | 测试相关 |
| ci | CI/CD 变更 |
| refactor | 重构 |

示例：
- `fix(s06): preserve write_file results in micro_compact (#274)`
- `docs: add CONTRIBUTING.md`
- `test: add s06 context compact unit tests`

### 5. 创建 PR
```sh
git push fork <branch>
gh pr create --repo shareAI-lab/learn-claude-code \
  --head <your-username>:<branch> --base main \
  --title "<title>" --body "<description>"
```

## 代码规范

### Python
- 遵循 PEP 8
- 函数包含 docstring（参数说明、返回值说明）
- 使用 type hints（Python 3.10+ 语法）
- 文件头部保留模块 docstring

### 文档
- 三语同步：`README.md`（中文）、`README.en.md`（英文）、`README.ja.md`（日文）
- Markdown 使用 ATX 风格标题（`#`）
- 代码块标注语言

### 测试
- 新增功能需附带测试
- 测试文件放在 `tests/` 目录
- 使用 pytest 框架
- 测试函数以 `test_` 开头

## 目录结构

```
agents/          # 精简版 agent 代码（s01-s12 + s_full）
s01_agent_loop/  # 教学章节（含 README、code.py、images）
...
s20_comprehensive/
docs/            # 多语文档（zh/en/ja）
tests/           # 测试文件
web/             # Next.js 可视化站点
skills/          # Claude Code skill 模板
```

## Issue 报告

提交 Issue 时请包含：
1. 问题描述（预期行为 vs 实际行为）
2. 复现步骤
3. 环境信息（OS、Python 版本、模型）
4. 错误日志（如有）

## 行为准则

参与本项目即表示你同意遵守 [Code of Conduct](CODE_OF_CONDUCT.md)。

## 许可证

提交的贡献将遵循 MIT 许可证。
