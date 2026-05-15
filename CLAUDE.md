# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A tkinter/ttkbootstrap desktop application for generating primary school (grades 1-6) practice worksheets. Supports math, Chinese, English, science, composition, reading, and calligraphy subjects. Generates questions with answers and exports to A4 PDF.

## Commands

```bash
python main.py                    # Launch the application
pip install -r requirements.txt   # Install dependencies
```

Windows users: double-click `启动出题软件.bat` (auto-installs deps if missing).

## Architecture

```
main.py → gui/app.py (MainApplication) → gui/tabs/* → core/* generators
```

**GUI layer** (`gui/`):
- `app.py` — MainApplication: 1200x800 themed window, PanedWindow layout (tabs left, preview right)
- `tabs/` — One Frame per subject. Each tab has `generate_questions()` returning `[{"question": str, "answer": str, "type": str}]`, and `export_pdf()`
- `widgets/settings.py` — SettingsPanel base class providing grade radio buttons + count spinbox
- `widgets/preview.py` — PreviewPanel for displaying generated questions

**Core layer** (`core/`):
- `question_generator.py` — BaseQuestionGenerator (ABC) + Math/Chinese/English/Science/Composition/Reading generators. Each has `KNOWLEDGE_POINTS: dict[int, list[str]]` hardcoded per grade
- `math_generator_enhanced.py` — EnhancedMathGenerator: 53 question types in 10 groups (used by MathTab instead of basic MathQuestionGenerator). Category codes like `"10in"`, `"mul_table"`, `"chicken_rabbit"` with `gen_<code>()` methods
- `pdf_export.py` — PDFExporter using ReportLab `canvas.Canvas`. Calligraphy export uses separate grid-drawing methods (`_draw_tianzige`, `_draw_mizige`, etc.)
- `web_scraper.py` — Baidu search scraper (only used by CompositionTab for essay search)

## Key Patterns

**Generator interface**: `generate(grade, count, question_type, knowledge_points)` returns list of dicts. All generators guard against empty knowledge_points with fallback defaults.

**EnhancedMathGenerator** differs from other generators: `_safe_gen()` wrapper with retry logic, category-code dispatch instead of question_type string, and `gen_*` methods return `(question_str, answer_value)` tuples.

**PDF export**: Subject-specific `export_*` methods delegate to `create_pdf()`, which renders line-by-line with manual y-position tracking and page breaks. Page numbers via `_add_page_number()`.

**data/ directory**: Structure exists (fonts, knowledge_points, questions, templates) but all subdirectories are empty. Knowledge data is hardcoded in generator source files.

## Adding a New Math Question Type

1. Add category code to `CATEGORY_NAMES` in `math_generator_enhanced.py`
2. Add to appropriate group in `get_categories_by_group()`
3. Implement `gen_<code>()` returning `(question_str, answer_value)` tuple
4. Math tab checkboxes pick it up automatically

## Adding a New Subject Tab

1. Create `gui/tabs/<subject>_tab.py` with a Frame subclass
2. Implement `generate_questions()` and `export_pdf()` methods
3. Import in `gui/app.py` and add to `create_tabs()`
