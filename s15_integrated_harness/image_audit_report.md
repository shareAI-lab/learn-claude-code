# Image Audit Report — s15_integrated_harness

- **Scope:** read-only audit of `images/` assets vs. image references in all `.md` files
- **Method:** full read of every `.md` file in the repo; full read of every file in `images/`
- **Result:** **no broken references, no duplicates, no unused images**

---

## 1. Contents of `images/`

Exactly 3 files (all SVG, no other asset types):

| # | File | Description (from full file read) |
|---|------|-----------------------------------|
| 1 | `images/system-architecture.en.svg` | Architecture diagram, English labels. Title: "s15 Integrated Harness — Many Mechanisms, One Loop" (labels: Before LLM, Before Tools, next turn, …) |
| 2 | `images/system-architecture.ja.svg` | Architecture diagram, Japanese labels. Title: "s15 Integrated Harness — 多くの仕組みを 1 つのループへ" (labels: LLM 前, Tool 前, 次のターン, …) |
| 3 | `images/system-architecture.svg` | Architecture diagram, Chinese labels. Title: "s15 Agent Harness 集成 — 多种机制，一个循环" (labels: LLM 前处理, 工具前闸门, 下一轮, …) |

## 2. Markdown files scanned

All `.md` files in the repository (verified via recursive glob; none hidden or in subdirectories):

1. `README.md` (English)
2. `README.zh.md` (Chinese)
3. `README.ja.md` (Japanese)
4. `ARCHITECTURE.md`
5. `trace_view_changes.md`

## 3. Every image reference found

Only three image references exist in the whole repository, all using standard Markdown
`![alt](path)` syntax in the "Solution/解決策/解决方案" section of each trilingual README:

| Reference (Markdown) | Located in | Resolved path (from repo dir) | Target exists? |
|---|---|---|---|
| `![System Architecture](images/system-architecture.en.svg)` | `README.md` | `images/system-architecture.en.svg` | ✅ yes |
| `![System Architecture](images/system-architecture.svg)` | `README.zh.md` | `images/system-architecture.svg` | ✅ yes |
| `![System Architecture](images/system-architecture.ja.svg)` | `README.ja.md` | `images/system-architecture.ja.svg` | ✅ yes |

Other `.md` files contain **no** image references:

- `ARCHITECTURE.md` — contains an inline `mermaid` code-block diagram (§12) and a
  turn-level `text` flow diagram; neither embeds an image file. Its §13.1 file map
  mentions `images/system-architecture*.svg` as a plain-text wildcard description,
  not a Markdown image embedding.
- `trace_view_changes.md` — no image references.

No HTML `<img>` tags or other reference syntaxes (`<picture>`, CSS `url(...)`, etc.)
appear in any `.md` file.

## 4. Broken references

**None.** All 3 referenced files exist on disk. Each relative path resolves correctly
from the directory containing the README (`s15_integrated_harness/`).

## 5. Duplicate references / duplicate assets

**None.**

- Each image file is referenced exactly once (by exactly one README). No two READMEs
  point at the same file, and no file is referenced more than once anywhere.
- The three SVGs are **not** byte-for-byte or content duplicates of each other: they
  are distinct localized variants of the same diagram (English / Japanese / Chinese).
  Full-file comparison shows different `font-family` stacks, different titles, and
  different labels throughout. The Chinese `.svg` also has minor text differences
  from the English variant even on shared lines (e.g., "s07 skills catalog +
  load_skill" vs. "s07 skills + load_skill"; "durable work:
  create/update/list/get/claim/complete_task · schedule/list/cancel_cron" vs.
  "durable work: task tools · cron tools").

## 6. Unused images

**None.** All 3 files in `images/` are referenced:

| File in `images/` | Referenced by |
|---|---|
| `system-architecture.en.svg` | `README.md` |
| `system-architecture.ja.svg` | `README.ja.md` |
| `system-architecture.svg` | `README.zh.md` |

## 7. Findings summary

| Check | Result |
|---|---|
| Broken image references | 0 |
| Duplicate references (same file referenced by multiple docs) | 0 |
| Duplicate asset files | 0 |
| Unused files in `images/` | 0 |
| Image references found in total | 3 (all valid) |

### Observations (informational, not defects)

1. **Naming asymmetry:** the English and Japanese variants use language-suffixed
   filenames (`.en.svg`, `.ja.svg`) while the Chinese variant uses the unsuffixed
   `system-architecture.svg`. This is consistent with the README convention (the
   primary/English README uses the suffixed English asset, the Chinese README the
   plain name) and all references resolve correctly, but the unsuffixed name could be
   mistaken for a generic default. Renaming to e.g. `system-architecture.zh.svg`
   would make the set uniform — optional, not required for correctness.
2. `README.md` links the diagram to the **English** asset and `README.zh.md` to the
   Chinese asset — i.e., each language's README displays its own localized diagram.
   This is intentional trilingual behavior, verified consistent across all three.
3. Scope note: this audit covered `.md` files as requested. Non-Markdown sources
   (e.g., `code.py`, Python docstrings) were not scanned for image-path strings.

**No files were modified by this audit.** This report is the only new file created.
