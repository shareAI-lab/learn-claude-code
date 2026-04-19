# PyPI 发布指南

> M3-7 在代码层面已准备好(classifiers / LICENSE / urls / 构建通过)。
> 真正推送到 PyPI 前还需完成下方 checklist。

## 发布前 checklist

- [x] **包名占用检查**:M5-5 查过 PyPI,`mycode` 等候选名**均可用**。当前版本使用 `mycode`
- [x] **版本号**:从 `0.1.0.dev0` 提升到 `0.1.0`(M5-5 完成)
- [x] **CHANGELOG.md**:已列出 M0 到 M5 的主要功能
- [ ] **README 补英文版**:PyPI 页面国际用户看不懂中文,建议提供 README-en.md,或在顶部加英文摘要
- [x] **跑完整测试套件**:`uv run pytest -q` 全过(目前 241+)
- [x] **本地构建**:`uv build` 产出 `dist/*.whl` 和 `dist/*.tar.gz`
- [ ] **本地安装自测**:新建一个干净 venv,`pip install dist/*.whl`,跑 `mycode --version`
- [ ] **PyPI Token 准备**:到 https://pypi.org/manage/account/token/ 创建项目 token,导出到 `UV_PUBLISH_TOKEN`

## 发布流程

```bash
cd mycode

# 1. 清理旧产物
rm -rf dist/ build/ *.egg-info

# 2. 构建
uv build

# 3. 检查产物
ls -la dist/
# 预期: mycode-<ver>.tar.gz 和 mycode-<ver>-py3-none-any.whl

# 4. (可选) 上传到 TestPyPI 做一次预演
uv publish --publish-url https://test.pypi.org/legacy/ \
  --token <TEST_PYPI_TOKEN>

# 5. 从 TestPyPI 装一下验证
pip install -i https://test.pypi.org/simple/ mycode

# 6. 正式发布
uv publish --token <PYPI_TOKEN>
```

## 安装体验(发布后)

```bash
# pipx 隔离安装,最推荐
pipx install mycode

# 或普通 pip
pip install mycode

mycode --help
```

## 注意事项

1. **Token 存储**:用 `UV_PUBLISH_TOKEN` 环境变量,不要写进 pyproject 或 commit
2. **版本不可回收**:一旦 `0.1.0` 上架就不能重复使用同版本号上传。需改 bug 要跳到 `0.1.1`
3. **pre-release**:如果不确定质量,用 `0.1.0rc1` 或 `0.1.0a1`,这些默认不被 `pip install` 抓取
4. **License 字段**:`LICENSE` 文件会自动被 hatchling 打进 wheel
