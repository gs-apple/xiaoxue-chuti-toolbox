# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A tkinter desktop application for generating primary school (grades 1-6) practice worksheets. Supports math, Chinese calligraphy, composition, and exam paper download. Generates questions with answers and exports to A4 PDF.

## Commands

```bash
python main.py                    # Launch the application
pip install -r requirements.txt   # Install dependencies (if available)
```

Windows users: double-click `启动.bat` (auto-launches the app).

## Architecture

```
main.py → MathGeneratorApp (tkinter) → Tab Widgets → Core Modules → PDF Export
```

**Main Entry** (`main.py`):
- `MathGeneratorApp`: 700x700 themed window with ttk.Notebook tabs
- Imports and initializes 4 tab widgets: ShuxueTabWidget, ZiTieTabWidget, ZuowenTabWidget, ZhentiTabWidget

**Tab Widgets** (UI layer):
- `shuxue_ui.py` — Math tab: 40+ checkbox types for question selection, spinboxes for count, generate/export buttons
- `zi_tie_ui.py` — Calligraphy tab: mode selection (字帖生成/空白模板), font selection (楷体/行书/行楷/自定义), content type (生字/词语/古诗/文言文/数字/拼音/改定), style selection (田字格/方格/米字格/数学格/生字格/拼音格/作文本/教案格/大楷本)
- `zuowen_ui.py` — Composition tab: 3 modes (课本作文/看图写话/自定义作文), grade filter, search, PDF export, example essays
- `zhenti_ui.py` — Exam download tab: multi-platform support (第一试卷网/中小学试卷网/新一试卷), subject/grade/year filtering

**Core Modules** (generation layer):
- `shuxue_core.py` — Math question generator: 40+ types across 10 groups (加减法/乘法/除法/混合运算/巧算/应用题/几何/数论/逻辑/组合), dedup cache, FRAC fraction notation
- `shuxue_drawings.py` — Geometry figure renderer: extracts dimensions from question text, draws rectangles/triangles/circles/cubes/prisms using ReportLab
- `shuxue_export.py` — Math PDF exporter: handles FRAC notation rendering, answer formatting, figure embedding
- `zitie_core.py` — Calligraphy generator: 9 grid styles (田字格/方格/米字格/数学格/生字格/拼音格/作文本/教案格/大楷本), stroke order rendering, font management
- `zitie_data.py` — Grade 1-6 character data: 生字表/古诗词/文言文/词语表 for each semester (人教版/国学)
- `stroke_renderer.py` — Stroke order renderer: uses makemeahanzi SVG data, Pillow-based rendering with lazy loading
- `zuowen_core.py` — Composition engine: textbook query (1-6年级), picture writing topics (19个), example essays (45篇), custom CRUD (SQLite)
- `zuowen_data.py` — Composition data: TEXTBOOK_COMPS (48 units), PICTURE_WRITING (19 topics), EXAMPLE_ESSAYS (45 essays)
- `zuowen_export.py` — Composition PDF exporter: example essay, worksheet (grid paper), custom composition

**Shared Components** (`widgets.py`):
- `GradientButton`: Custom tkinter Canvas button with gradient background, hover/press effects

**Spider Module** (`spider/`):
- `scraper.py` — Web scraper for exam papers
- `zhenti_scraper.py` — Exam paper specific scraper
- `database.py` — SQLite database for storing scraped data
- `integration.py` — Integration layer for spider functionality

**Data Files**:
- `stroke_data.json` — 24MB stroke order data (Unicode codepoint → SVG paths)
- `question_bank.db` — 1.5MB SQLite question bank
- `zuowen.db` — SQLite database for custom compositions
- `fonts/` — Custom font files for calligraphy
- `makemeahanzi-master/` — Stroke order SVG source files (gitignored)

## Key Patterns

**Math Question Generation**:
- `generate_questions()` returns list of `(category_code, question_text, answer)` tuples
- FRAC notation: `FRAC[1,3]` represents 1/3, rendered as proper fractions in PDF
- Dedup cache: `_DedupCache` class persists to `.question_cache.json`, max 500 entries
- Thread-safe generation with queue-based UI updates

**Calligraphy Generation**:
- `ZitieGenerator` with `ZitieConfig` for grid/font/content settings
- Content types: 生字(shengzi), 词语(ciyu), 古诗(gushi), 文言文(wenyan), 数字(shuzi), 拼音(pinyin_text), 改定(gaiding)
- Style indices: 0=田字格, 1=方格, 2=米字格, 3=数学格, 4=生字格, 5=拼音格, 6=作文本, 7=教案格, 8=大楷本
- Font management: builtin fonts (楷体/行书/行楷) + custom font support

**PDF Export**:
- ReportLab `canvas.Canvas` for all PDF generation
- Subject-specific export methods: `export_math()`, `export_zitie()`
- Manual y-position tracking with page breaks
- Page numbers via `_add_page_number()`

**Stroke Rendering**:
- Lazy-loaded `stroke_data.json` (24MB)
- SVG path parsing with Bezier curve support
- Pillow-based image rendering with caching

## Adding a New Math Question Type

1. Add category code to `CATEGORY_NAMES` in `shuxue_core.py`
2. Add checkbox to `ShuxueTabWidget._ATTR_MAP` in `shuxue_ui.py`
3. Implement `gen_<code>()` function in `shuxue_core.py`
4. Add to appropriate group in the UI layout

## Adding a New Calligraphy Style

1. Add style index to `_CONTENT_DISABLE_RULES` in `zi_tie_ui.py`
2. Implement grid drawing method in `zitie_core.py`
3. Update style radio buttons in `ZiTieTabWidget._init_ui()`

## Adding a New Composition Topic

1. Add to `unit_zuowen_titles` dictionary in `zuowen_ui.py`
2. Include grade-specific content in the appropriate grade section

## Dependencies

- **tkinter**: Built-in Python GUI framework
- **Pillow**: Image processing for stroke rendering
- **ReportLab**: PDF generation
- **requests**: HTTP client for web scraping
- **beautifulsoup4**: HTML parsing for exam paper scraping
- **sqlite3**: Built-in Python database (for question bank)

## Notes

- The project uses `Microsoft YaHei` font throughout the UI
- All UI elements use a consistent color scheme: `#f0f0f0` background, `#2563eb` accent
- The `FRAC` notation is internal; it's converted to proper fractions in display/export
- Stroke data is large (24MB) and loaded lazily to minimize startup time
- The spider module is optional and only used for exam paper download functionality
