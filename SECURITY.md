# 安全策略

## 报告安全漏洞

如果你发现安全漏洞，请**不要**通过公开 Issue 报告。

请通过以下方式之一私下报告：

### 方式一：GitHub Security Advisory（推荐）
1. 前往 https://github.com/shareAI-lab/learn-claude-code/security/advisories/new
2. 填写漏洞详情、影响范围与复现步骤
3. 提交后维护者将在 48 小时内响应

### 方式二：邮件
发送邮件至维护者，主题以 `[SECURITY]` 开头。

## 响应时间

| 阶段 | 时间 |
|------|------|
| 确认收到 | 48 小时内 |
| 初步评估 | 7 天内 |
| 修复发布 | 30 天内（严重漏洞优先） |

## 支持版本

| 版本 | 支持状态 |
|------|----------|
| main 分支 | ✅ 支持 |
| 最新 release | ✅ 支持 |
| 旧版本 | ❌ 不支持 |

## 披露政策

- 漏洞修复后将在 GitHub Security Advisory 公开披露
- 报告者将获得致谢（如愿意）
- 我们遵循协调披露（Coordinated Disclosure）原则

## 安全最佳实践（针对使用者）

1. **API Key 保护**: 不要将 `.env` 文件提交到 git，确保 `.gitignore` 包含 `.env`
2. **工作区隔离**: s03 的 `safe_path()` 防止路径逃逸，不要禁用此检查
3. **命令过滤**: s03 的 `_DANGEROUS_PATTERNS` 拦截危险命令，不要绕过
4. **依赖更新**: 启用 dependabot 保持依赖最新
