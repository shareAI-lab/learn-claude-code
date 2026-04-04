---
name: pdf
description: Process PDF files - extract text, create PDFs, merge documents. Use when user asks to read PDF, create PDF, or work with PDF files.
---

# PDF Processing Skill

You now have expertise in PDF manipulation. Follow these workflows:

## Reading PDFs

**Option 1: Quick text extraction (preferred)**
```bash
# Using pdftotext (poppler-utils)
pdftotext input.pdf -  # Output to stdout
pdftotext input.pdf output.txt  # Output to file

# If pdftotext not available, try:
python3 -c "
import fitz  # PyMuPDF
doc = fitz.open('input.pdf')
for page in doc:
    print(page.get_text())
"
```

**Option 2: Page-by-page with metadata**
```python
import fitz  # pip install pymupdf

doc = fitz.open("input.pdf")
print(f"Pages: {len(doc)}")
print(f"Metadata: {doc.metadata}")

for i, page in enumerate(doc):
    text = page.get_text()
    print(f"--- Page {i+1} ---")
    print(text)
```

## Creating PDFs

**Option 1: From Markdown (recommended)**
```bash
# Using pandoc
pandoc input.md -o output.pdf

# With custom styling
pandoc input.md -o output.pdf --pdf-engine=xelatex -V geometry:margin=1in
```

**Option 2: Programmatically**
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("output.pdf", pagesize=letter)
c.drawString(100, 750, "Hello, PDF!")
c.save()
```

**Option 3: From HTML**
```bash
# Using wkhtmltopdf
wkhtmltopdf input.html output.pdf

# Or with Python
python3 -c "
import pdfkit
pdfkit.from_file('input.html', 'output.pdf')
"
```

## Merging PDFs

```python
import fitz

result = fitz.open()
for pdf_path in ["file1.pdf", "file2.pdf", "file3.pdf"]:
    doc = fitz.open(pdf_path)
    result.insert_pdf(doc)
result.save("merged.pdf")
```

## Splitting PDFs

```python
import fitz

doc = fitz.open("input.pdf")
for i in range(len(doc)):
    single = fitz.open()
    single.insert_pdf(doc, from_page=i, to_page=i)
    single.save(f"page_{i+1}.pdf")
```

## Key Libraries

| Task | Library | Install |
|------|---------|---------|
| Read/Write/Merge | PyMuPDF | `pip install pymupdf` |
| Create from scratch | ReportLab | `pip install reportlab` |
| HTML to PDF | pdfkit | `pip install pdfkit` + wkhtmltopdf |
| Text extraction | pdftotext | `brew install poppler` / `apt install poppler-utils` |

## Best Practices

1. **Always check if tools are installed** before using them
2. **Handle encoding issues** - PDFs may contain various character encodings
3. **Large PDFs**: Process page by page to avoid memory issues
4. **OCR for scanned PDFs**: Use `pytesseract` if text extraction returns empty
