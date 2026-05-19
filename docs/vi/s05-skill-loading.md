# s05: Kỹ năng (Skills)

`s01 > s02 > s03 > s04 > [ s05 ] s06 | s07 > s08 > s09 > s10 > s11 > s12`

> *"Tải kiến thức khi bạn cần, không phải tải ngay từ đầu"* -- chèn thông qua tool_result, không phải qua system prompt.
>
> **Lớp khung (Harness layer)**: Kiến thức theo yêu cầu -- chuyên môn trong lĩnh vực, được tải khi mô hình yêu cầu.

## Vấn đề

Bạn muốn agent tuân theo các quy trình làm việc đặc thù của lĩnh vực: quy ước git, các mẫu kiểm thử (testing patterns), danh sách kiểm tra khi xem xét mã nguồn (code review checklists). Việc đưa mọi thứ vào system prompt sẽ lãng phí token cho các kỹ năng không được sử dụng. 10 kỹ năng, mỗi kỹ năng 2000 token = 20,000 token, mà hầu hết trong số đó không liên quan đến một tác vụ cụ thể.

## Giải pháp

```
System prompt (Lớp 1 -- luôn hiện diện):
+--------------------------------------+
| Bạn là một coding agent.             |
| Các kỹ năng hiện có:                 |
|   - git: Hỗ trợ quy trình Git        |  ~100 token/kỹ năng
|   - test: Các thực hành kiểm thử tốt |
+--------------------------------------+

Khi mô hình gọi load_skill("git"):
+--------------------------------------+
| tool_result (Lớp 2 -- theo yêu cầu): |
| <skill name="git">                   |
|   Hướng dẫn đầy đủ quy trình git...  |  ~2000 token
|   Bước 1: ...                        |
| </skill>                             |
+--------------------------------------+
```

Lớp 1: *tên* các kỹ năng trong system prompt (ít tốn kém). Lớp 2: toàn bộ *nội dung* thông qua tool_result (theo yêu cầu).

## Cách hoạt động

1. Mỗi kỹ năng là một thư mục chứa tệp `SKILL.md` với YAML frontmatter (phần mô tả đầu tệp).

```
skills/
  pdf/
    SKILL.md       # ---\n name: pdf\n description: Xử lý các tệp PDF\n ---\n ...
  code-review/
    SKILL.md       # ---\n name: code-review\n description: Xem xét mã nguồn\n ---\n ...
```

2. SkillLoader quét các tệp `SKILL.md`, sử dụng tên thư mục làm mã định danh kỹ năng.

```python
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills = {}
        for f in sorted(skills_dir.rglob("SKILL.md")):
            text = f.read_text()
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body}

    def get_descriptions(self) -> str:
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "")
            lines.append(f"  - {name}: {desc}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            return f"Lỗi: Kỹ năng không xác định '{name}'."
        return f"<skill name=\"{name}\">\n{skill['body']}\n</skill>"
```

3. Lớp 1 được đưa vào system prompt. Lớp 2 chỉ là một trình xử lý công cụ khác.

```python
SYSTEM = f"""Bạn là một coding agent tại {WORKDIR}.
Các kỹ năng hiện có:
{SKILL_LOADER.get_descriptions()}"""

TOOL_HANDLERS = {
    # ...các công cụ cơ bản...
    "load_skill": lambda **kw: SKILL_LOADER.get_content(kw["name"]),
}
```

Mô hình biết được những kỹ năng nào đang tồn tại (ít tốn kém) và tải chúng khi thấy liên quan (tốn kém hơn nhưng chính xác).

## Những gì đã thay đổi so với s04

| Thành phần         | Trước (s04)          | Sau (s05)                         |
|--------------------|----------------------|-----------------------------------|
| Công cụ            | 5 (cơ bản + task)    | 5 (cơ bản + load_skill)           |
| System prompt      | Chuỗi tĩnh           | + mô tả các kỹ năng               |
| Kiến thức          | Không có             | Các tệp skills/\*/SKILL.md        |
| Chèn kiến thức     | Không có             | Hai lớp (system + tool_result)    |

## Thử nghiệm

```sh
cd learn-claude-code
python agents/s05_skill_loading.py
```

1. `Có những kỹ năng nào?`
2. `Tải kỹ năng agent-builder và làm theo hướng dẫn của nó`
3. `Tôi cần xem xét mã nguồn -- hãy tải kỹ năng liên quan trước`
4. `Xây dựng một MCP server bằng kỹ năng mcp-builder`
