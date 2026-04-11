---
name: pdf
description: 处理 PDF 文件：提取文本、创建 PDF、合并文档。适用于读取/生成/编辑 PDF 的请求。
---

# PDF 处理技能

你现在具备 PDF 处理能力。按以下工作流执行。

## 读取 PDF

**方案 1：快速提取文本（优先）**
```bash
pdftotext input.pdf -
pdftotext input.pdf output.txt

# 若 pdftotext 不可用：
python3 -c "
import fitz
for page in fitz.open('input.pdf'):
    print(page.get_text())
"
```

**方案 2：逐页 + 元数据**
```python
import fitz

doc = fitz.open("input.pdf")
print(f"Pages: {len(doc)}")
print(f"Metadata: {doc.metadata}")

for i, page in enumerate(doc):
    print(f"--- Page {i+1} ---")
    print(page.get_text())
```

## 创建 PDF

**方案 1：由 Markdown 生成（推荐）**
```bash
pandoc input.md -o output.pdf
pandoc input.md -o output.pdf --pdf-engine=xelatex -V geometry:margin=1in
```

**方案 2：编程生成**
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("output.pdf", pagesize=letter)
c.drawString(100, 750, "Hello, PDF!")
c.save()
```

**方案 3：由 HTML 生成**
```bash
wkhtmltopdf input.html output.pdf

python3 -c "
import pdfkit
pdfkit.from_file('input.html', 'output.pdf')
"
```

## 合并 PDF

```python
import fitz

result = fitz.open()
for pdf_path in ["file1.pdf", "file2.pdf", "file3.pdf"]:
    result.insert_pdf(fitz.open(pdf_path))
result.save("merged.pdf")
```

## 拆分 PDF

```python
import fitz

doc = fitz.open("input.pdf")
for i in range(len(doc)):
    single = fitz.open()
    single.insert_pdf(doc, from_page=i, to_page=i)
    single.save(f"page_{i+1}.pdf")
```

## 常用库

| 任务 | 库 | 安装 |
|---|---|---|
| 读/写/合并 | PyMuPDF | `pip install pymupdf` |
| 从零创建 | ReportLab | `pip install reportlab` |
| HTML 转 PDF | pdfkit | `pip install pdfkit` + wkhtmltopdf |
| 文本提取 | pdftotext | `brew install poppler` / `apt install poppler-utils` |

## 最佳实践

1. 使用前先检查工具/依赖是否安装
2. 注意编码问题（PDF 可能混合多种编码）
3. 大文件按页处理，避免内存爆涨
4. 扫描件需 OCR：文本提取为空时可用 `pytesseract`
