# s17: Structured Output (结构化输出)

`s01 > s02 > s03 > s04 > s05 > s06 > s07 > s08 > s09 > s10 > s11 > s12 > s13 > s14 > s15 > s16 > [ s17 ] s18 > s19`

> *"JSON Schema 约束把散文变成数据"* -- harness 读取结构化输出,而非自由文本。
>
> **Harness 层**: Schema 验证 -- 强制模型返回可解析的数据。

## 问题

s16 之后,harness 能智能路由任务。但模型仍返回自由文本。要程序化使用结果,harness 必须解析散文 -- 不可靠且昂贵。

如果模型返回验证过的 JSON,harness 直接读取。

## 解决方案

```
不使用结构化输出:
模型: "我发现了 3 个问题:第一,折扣函数不处理负值..."
 -> harness 必须解析散文 (不可靠)

使用结构化输出:
模型: {"findings": [{"severity": "critical", "line": 5, "message": "..."}]}
 -> harness 直接读取 JSON (可靠)

验证循环:
1. 发送 prompt + schema
2. 解析 JSON 响应
3. 验证 schema
4. 如果无效:把错误发回模型,重试
5. 最多 3 次重试
```

## 工作原理

1. **定义 schema。** JSON Schema 子集 (object, array, string, integer, enum)。

```python
CODE_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["critical", "warning", "info"]},
                    "line": {"type": "integer"},
                    "message": {"type": "string"},
                },
                "required": ["severity", "message"],
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["findings", "summary"],
}
```

2. **验证 schema。** 简单的类型 + 必填检查。

```python
def validate_schema(data, schema, errors=None):
    if schema.get("type") == "object":
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"缺少必填字段 '{req}'")
    return errors
```

3. **带反馈的重试。** 验证失败时把错误发回模型。

```python
for attempt in range(1, max_retries + 1):
    if attempt > 1:
        prompt = f"验证失败: {errors}\n修复并重试。\n{原始prompt}"
    data = json.loads(response_text)
    errors = validate_schema(data, schema)
    if not errors:
        return data
```

## 试一试

```sh
cd learn-claude-code
python agents/s17_structured_output.py
```

试试这些:

1. `/review` -- 结构化代码审查,JSON 输出
2. `/status "已完成数据库设置,下一步需要认证"` -- 提取状态为 JSON
3. `/demo` -- 展示 schema 验证的好数据和坏数据
4. `/validate {"findings": [], "summary": "ok"}` -- 测试你自己的 JSON
