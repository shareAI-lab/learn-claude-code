# s14: Security Classifier (安全分类器)

`s02 > s13 > [ s14 ] | s15 | s16 > s17`

> *"正则表达式认模式不认意图；LLM 能理解上下文"*
>
> **Harness 层**: 安全分类 -- 判断命令意图，而非仅匹配形状。

## 问题

s13 的正则表达式只匹配命令的"形状"，不理解"意图"。`rm -rf build/` 和 `rm -rf /` 看起来一模一样，但前者是正常的构建清理，后者是灾难性操作。

## 解决方案

```
    Command
       |
       v
    +--------------------+
    | Layer 1: 快速扫描   |   正则模式 (零成本)
    +--------+-----------+
             |
        命中? --是--> deny/ask
             |
            否
             v
    +--------------------+
    | Layer 2: LLM 分类  |   ~10 tokens/次
    +--------+-----------+
             |
      safe / moderate / dangerous
             |
        allow / ask / deny
```

两层分类管线:

- **Layer 1**（正则）: 15 种已知危险模式，零成本，即时匹配。
- **Layer 2**（LLM）: 通过理解意图分类未知命令。

## 工作原理

1. `SecurityClassifier.quick_scan()` 以 O(1) 检查 15 条正则模式。

2. `SecurityClassifier.llm_classify()` 将命令发送给 LLM 进行意图分析。

3. `classify()` 运行完整管线: 快速扫描 -> 白名单 -> LLM。

## 相对 s13 的变更

| 组件 | 之前 (s13) | 之后 (s14) |
|------|-----------|-----------|
| 分类方式 | 仅正则模式匹配 | 正则快筛 + LLM 分类 |
| 未知命令 | 默认 allow | LLM 判断 safe/moderate/dangerous |
| 误判率 | 高（`rm -rf build/` 被拦） | 低（LLM 理解意图） |
| 成本 | 零 | 白名单零成本 + LLM ~10 tokens/次 |

## 试一试

```sh
cd learn-claude-code
python agents/s14_security_classifier.py
```

1. `delete the build/ directory` (LLM 应判断为 moderate -> ask)
2. `list all python files` (白名单 -> allow)
3. `run git push --force origin main` (正则模式 -> deny)
4. `run pip install numpy` (LLM 应判断为 moderate -> ask)
5. `create a new file called test.py` (LLM 应判断为 safe -> allow)
