---
name: code-review
description: 对代码进行全面审查，覆盖安全、性能、可维护性。适用于用户要求 review 代码、查 bug、审计代码库。
---

# 代码审查技能

你现在具备完整代码审查能力。请按以下结构执行。

## 审查清单

### 1. 安全（最高优先级）

检查：
- [ ] **注入漏洞**：SQL、命令、XSS、模板注入
- [ ] **认证问题**：硬编码凭据、弱认证
- [ ] **授权缺陷**：缺失访问控制、IDOR
- [ ] **数据泄露**：日志/报错泄漏敏感信息
- [ ] **密码学**：弱算法、密钥管理不当
- [ ] **依赖风险**：已知漏洞（`npm audit`、`pip-audit`）

```bash
# 快速安全扫描
npm audit                    # Node.js
pip-audit                    # Python
cargo audit                  # Rust
grep -r "password\|secret\|api_key" --include="*.py" --include="*.js"
```

### 2. 正确性

检查：
- [ ] **逻辑错误**：边界值、空值、off-by-one
- [ ] **并发问题**：竞态条件、同步缺失
- [ ] **资源泄露**：文件/连接/内存未释放
- [ ] **错误处理**：异常吞掉、遗漏错误路径
- [ ] **类型安全**：隐式转换、过多 any

### 3. 性能

检查：
- [ ] **N+1 查询**：循环中访问数据库
- [ ] **内存问题**：大对象分配、引用滞留
- [ ] **阻塞操作**：异步流程中同步 I/O
- [ ] **低效算法**：可 O(n) 却写成 O(n^2)
- [ ] **缺少缓存**：昂贵计算重复执行

### 4. 可维护性

检查：
- [ ] **命名**：语义清晰、一致
- [ ] **复杂度**：函数过长、嵌套过深
- [ ] **重复代码**：复制粘贴逻辑
- [ ] **死代码**：未使用 import、不可达分支
- [ ] **注释质量**：过时/冗余/缺失

### 5. 测试

检查：
- [ ] **覆盖率**：关键路径是否覆盖
- [ ] **边界场景**：空值、边界值、异常输入
- [ ] **隔离性**：外部依赖是否正确 mock
- [ ] **断言质量**：断言是否具体、有效

## 输出格式

```markdown
## Code Review: [file/component name]

### Summary
[1-2 sentence overview]

### Critical Issues
1. **[Issue]** (line X): [Description]
   - Impact: [What could go wrong]
   - Fix: [Suggested solution]

### Improvements
1. **[Suggestion]** (line X): [Description]

### Positive Notes
- [What was done well]

### Verdict
[ ] Ready to merge
[ ] Needs minor changes
[ ] Needs major revision
```

## 常见模式（重点标记）

### Python
```python
# Bad: SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# Good:
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# Bad: Command injection
os.system(f"ls {user_input}")
# Good:
subprocess.run(["ls", user_input], check=True)

# Bad: Mutable default argument
def append(item, lst=[]):  # Bug: shared mutable default
# Good:
def append(item, lst=None):
    lst = lst or []
```

### JavaScript/TypeScript
```javascript
// Bad: Prototype pollution
Object.assign(target, userInput)
// Good:
Object.assign(target, sanitize(userInput))

// Bad: eval usage
eval(userCode)
// Good: Never use eval with user input

// Bad: Callback hell
getData(x => process(x, y => save(y, z => done(z))))
// Good:
const data = await getData();
const processed = await process(data);
await save(processed);
```

## 常用命令

```bash
# 最近变更
git diff HEAD~5 --stat
git log --oneline -10

# 潜在风险点
grep -rn "TODO\|FIXME\|HACK\|XXX" .
grep -rn "password\|secret\|token" . --include="*.py"

# 复杂度检查（Python）
pip install radon && radon cc . -a

# 依赖检查
npm outdated
pip list --outdated
```

## 审查流程

1. 理解上下文：先读 PR 描述与关联 issue
2. 运行项目：构建、测试、本地验证（可行时）
3. 自上而下阅读：先入口，再核心模块
4. 检查测试：新增变更是否被测试覆盖
5. 安全扫描：自动化工具 + 人工复核
6. 输出反馈：明确问题、给可执行建议、语气专业
