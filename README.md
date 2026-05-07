# CADAir

A Python tool for **DWG → JSON conversion** and **DWG/DXF text translation** using [ezdxf](https://ezdxf.mozman.at/) and ODA File Converter.

## Features

- ✅ **DWG ↔ DXF Conversion** — Uses ODA File Converter
- ✅ **Multi-position Text Extraction** — Layouts, Block definitions (including anonymous blocks `*U`), Block attributes (ATTRIB)
- ✅ **MTEXT Format Handling** — Extract plain text for translation
- ✅ **DXF Encoding Handling** — Detects R2007+ UTF-8 and legacy `$DWGCODEPAGE` encodings for raw DXF patching
- ✅ **Chinese Font Support** — Auto configure `gbcbig.shx`
- ✅ **Plugin Architecture** — Easy to add new translation engines
- ✅ **Human Translation Workflow** — Extract → Edit JSON → Write back
- ✅ **In-Memory Translation Cache** — Avoid duplicate API calls, auto deduplicate identical texts
- ✅ **Pre-API Translation Filtering** — Skips numbers, dimensions, CAD markers, target-language text, and stable technical abbreviations
- ✅ **Async Translation with Concurrency Control** — QPS limiting, max concurrent requests
- ✅ **Environment Variables Support** — Configure via `.env` file
- ✅ **MULTILEADER Preservation** — Avoids `ezdxf.saveas()` roundtrip for DWG/DXF output and patches DXF text directly

## Documentation

- [Work Summary: DWG Translation Roundtrip Fix](docs/WORK_SUMMARY_2026-05-06.md)
- [Work Summary: DXF Non-Roundtrip Patch Output](docs/WORK_SUMMARY_DXF_NON_ROUNDTRIP_2026-05-06.md)
- [Work Summary: Translation Filtering](docs/WORK_SUMMARY_TRANSLATION_FILTERING_2026-05-06.md)
- [TODO](docs/TODO.md)

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management (or pip)
- ODA File Converter (for DWG support, see below)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/CADAir.git
cd CADAir
```

### 2. Install Python dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install ezdxf requests
```

### 3. Install ODA File Converter (for DWG support)

`ezdxf` cannot read DWG files directly. It uses the **ODA File Converter** to convert DWG ↔ DXF:

1. Go to https://www.opendesign.com/guestfiles/oda_file_converter
2. Download the latest **ODA File Converter** for your platform
3. Install (default Windows path: `C:\Program Files\ODA\ODAFileConverter 27.1.0\`)

### 4. Configure via .env file

Create a `.env` file in the project root:

```env
# Baidu Translation API credentials
APP_ID=your_app_id_here
SEC_KEY=your_secret_key_here

# ODA File Converter path (required for DWG support)
# Windows:
# ODA_PATH=C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe
# Linux:
ODA_PATH=/path/to/ODAFileConverter.AppImage

# Optional translation settings
TRANSLATE_DOMAIN=machinery
TRANSLATE_QPS=1.0
TRANSLATE_TARGET=en
TRANSLATE_SOURCE=zh
TRANSLATE_USE_GENERAL=y
```

### 5. Configure ODA path in code

`oda_path` is **required** (no default value):

```python
from dwgtranslator import TranslationManager

# Windows
manager = TranslationManager(oda_path=r"C:\Your\Path\ODAFileConverter.exe")

# Linux
manager = TranslationManager(oda_path="/path/to/ODAFileConverter.AppImage")
```

## Project Structure

```
CADAir/
├── docs/                   # Work summaries and TODOs
├── dwgtranslator/          # Modular DWG translation package
│   ├── __init__.py
│   ├── core.py            # DWG/DXF I/O, ODA conversion, encoding, fonts
│   ├── extract.py         # Text extraction, including raw DXF MULTILEADER supplement
│   ├── writeback.py       # Translated text writer and direct DXF patcher
│   ├── translator.py      # Translation engine ABC + Factory
│   ├── translation_filter.py # Pre-API CAD text filtering
│   ├── manager.py         # Workflow manager (Facade)
│   └── plugins/
│       ├── __init__.py
│       └── baidu.py       # Baidu Translation API plugins
├── dwg-utils/              # Standalone DWG/DXF utilities
│   ├── dwg_to_dxf.py      # Direct ODA DWG to DXF converter
│   ├── dwg2json.py
│   └── text_reader.py
├── data/                   # DWG/DXF/JSON data files
│   ├── 20260123.dwg       # Sample DWG
│   ├── your_design.dwg    # Sample DWG
│   ├── output.dxf         # Translated DXF
│   ├── output.json        # Geometry export JSON
│   └── translation_work.json  # Translation workflow
├── pyproject.toml
└── README.md
```

## DWG → JSON (Geometry Extraction)

Extract geometric entities from DWG:

```bash
python main.py
```

Supported entities:
- `LINE` — start/end points
- `CIRCLE` — center/radius
- `TEXT` — content/insert point/height
- `LWPOLYLINE` — vertices

Output: `data/output.json`

## DWG Text Translation

### Modular Plugin Architecture

```
dwgtranslator/
├── __init__.py          # Unified exports
├── core.py              # DWG/DXF I/O, encoding upgrade, fonts
├── extract.py           # 3-position text extraction (TEXT/MTEXT/ATTRIB, including anonymous blocks)
├── writeback.py         # Write translated texts back to entities
├── translator.py        # Translation engine ABC + Factory pattern
├── translation_cache.py # In-memory cache to avoid duplicate API calls
├── translation_filter.py # Pre-API filtering for CAD markers and target-language text
├── manager.py           # Facade for workflow management
└── plugins/
    └── baidu.py         # Baidu: field-specific + general translation APIs (sync + async)
```

### Core Features

| Module | Key Responsibilities |
|--------|----------------------|
| `core.py` | Read DWG/DXF, run ODA conversion, track ODA-generated DXF for non-roundtrip output |
| `extract.py` | Extract from layouts, block definitions, INSERT attributes, MTEXT, and raw DXF MULTILEADER group code `304` |
| `writeback.py` | Write translations and directly patch DXF text without full `ezdxf.saveas()` for DWG/DXF input |
| `translator.py` | ABC, Mock implementation, factory for engine registration |
| `translation_filter.py` | Skip non-translatable CAD labels before cache lookup and API calls |
| `manager.py` | Orchestrate: extract → translate → write-back |

### Pre-API Translation Filtering

Before checking the translation cache or calling a translation API, the manager filters text that should remain unchanged in CAD drawings.

Skipped categories include:

- Pure numbers, page/range markers, dimensions, sizes, ratios, and electrical values.
- Equipment, cabinet, terminal, and slot labels such as `CAB-01`, `XT1`, `U01`, and `2U`.
- Stable uppercase technical abbreviations such as `ODF`, `PDU`, `CCU`, `ETH`, `RUN`, `ALM`, and `PWR`.
- Text already matching the target language, such as English labels when `TRANSLATE_TARGET=en`.

Skipped handles are not added to `translated_bundles`, so they are not written back and the original DXF text is preserved. Mixed source-language labels such as `主柜 PDU` still go through translation because they contain source text that needs output in the target language.

### DWG/DXF Output Compatibility

For DWG and DXF input, the final DXF output intentionally avoids a full `ezdxf` save roundtrip.

The workflow is:

1. DWG input is converted by ODA File Converter; DXF input uses the original DXF as the base file.
2. `ezdxf` is used for safe extraction.
3. Missing complex `MULTILEADER` text is supplemented from raw DXF group code `304`.
4. The translated text is patched directly into the base DXF by entity handle.

This preserves complex `MULTILEADER` arrows, labels, proxy graphics, and context data that some CAD viewers rely on. See [the work summary](docs/WORK_SUMMARY_2026-05-06.md) for the root-cause analysis and verification details.

Raw DXF reads and writes use lightweight header-based encoding detection. R2007+ DXF files (`AC1021` and newer) are treated as UTF-8, while older DXF files use `$DWGCODEPAGE` mappings such as `ANSI_936` → `gbk`.

### Available Translation Engines

```python
from dwgtranslator import TranslationEngineFactory
print(TranslationEngineFactory.list_engines())
# ['mock', 'baidu_field', 'baidu_general']
```

### Usage

**Run examples**:
```bash
# Run all examples
python examples/run_all.py

# Run individual example
python examples/quick_start.py
python examples/extract_only.py
python examples/writeback_only.py
python examples/baidu_translate.py
```

**Extract for human translation**:
```python
from dwgtranslator import TranslationManager

manager = TranslationManager(oda_path="/path/to/ODAFileConverter")
manager.extract_only("data/input.dwg", "data/translation_work.json")
# Edit JSON, add 'translated' field, then:
manager.writeback_only("data/input.dwg", "data/translation_work.json", "data/output.dxf")
```

**Baidu Field Translation API (Synchronous)**:
```python
from dwgtranslator import TranslationManager, BaiduFieldTranslator

baidu = BaiduFieldTranslator(
    app_id="YOUR_APP_ID",
    app_key="YOUR_APP_KEY",
    domain="machinery"  # it, electronics, machinery, finance
)

manager = TranslationManager(oda_path="/path/to/ODAFileConverter")
manager.set_translator(baidu)
manager.translate_file("data/input.dwg", "data/output.dxf")
```

**Async Baidu Translation API (with concurrency & rate control)**:
```python
import asyncio
from dwgtranslator import TranslationManager, AsyncBaiduGeneralTranslator, AsyncBaiduFieldTranslator

# 通用翻译（推荐用于中译英）
baidu = AsyncBaiduGeneralTranslator(
    app_id="YOUR_APP_ID",
    app_key="YOUR_APP_KEY",
    max_concurrent=3,            # 最大并发请求数
    requests_per_second=1.0      # QPS限制 (每秒最多请求数)
)

# 或领域翻译（推荐用于英译中，特定专业领域）
# baidu = AsyncBaiduFieldTranslator(
#     app_id="YOUR_APP_ID",
#     app_key="YOUR_APP_KEY",
#     domain="machinery",
#     max_concurrent=3,
#     requests_per_second=1.0
# )

manager = TranslationManager(oda_path="/path/to/ODAFileConverter")
manager.set_translator(baidu)

# 异步翻译流程
asyncio.run(manager.translate_file_async(
    "data/input.dwg",
    "data/output_async.dxf"
))
```

**Run async example**:
```bash
uv run python examples/baidu_async_translate.py data/20260123.dwg
```

*Performance benchmark: 20 texts with 100ms simulated delay - sync: 2.0s, async: 0.45s (4.4x speedup)*

*Translation cache: In-memory cache automatically deduplicates identical texts, reducing API calls significantly for repeated content.*

*Translation filtering: Non-translatable CAD labels are skipped before cache lookup and API calls, reducing API usage and preserving stable identifiers.*

**Custom glossary / allowlist**:
```python
from dwgtranslator import TranslationManager

manager = TranslationManager(
    oda_path="/path/to/ODAFileConverter",
    glossary=["ODF", "PDU", "CCU", "ETH", "RUN", "ALM", "PWR"],
)
```

Glossary entries can also include fixed translations. Exact matches in `translations` are written directly without calling the translation API; exact matches in `terms` are skipped and preserved as-is.

Glossary config can be passed as JSON text or loaded from a JSON file:

```python
manager = TranslationManager(
    oda_path="/path/to/ODAFileConverter",
    glossary_json='["ODF", "PDU", "主柜"]',
    glossary_file="config/cad_glossary_zh-en.json",
)
```

Supported file formats:

```json
["ODF", "PDU", "主柜"]
```

```json
{
  "terms": ["ODF", "PDU"],
  "translations": {
    "主柜": "Main Cabinet",
    "备用柜": "Standby Cabinet"
  }
}
```

For the async Baidu example, glossary can be supplied from `.env` or CLI:

```bash
uv run python examples/baidu_async_translate.py data/input.dwg --glossary-json ODF,PDU,主柜
uv run python examples/baidu_async_translate.py data/input.dwg --glossary-file config/cad_glossary_zh-en.json
```

Verified zh-to-en run with the bundled glossary config:

```bash
.venv/bin/python examples/baidu_async_translate.py data/20260123.dwg --glossary-file config/cad_glossary_zh-en.json
```

This produced `data/20260123_translated_translated.dxf`, patched `327/327` translated handles, and showed fixed glossary output such as `电源分配单元 -> Power Distribution Unit`.

### Adding New Translation Plugins

```python
from dwgtranslator.translator import TranslationEngine, TranslationEngineFactory

class MyTranslator(TranslationEngine):
    name = "my_translator"
    
    def translate(self, text, from_lang='auto', to_lang='zh'):
        # Implement your API
        return translated_text

TranslationEngineFactory.register(MyTranslator)

# Use:
engine = TranslationEngineFactory.create('my_translator', api_key='xxx')
```

### Get Baidu API Credentials

1. Go to: https://fanyi-api.baidu.com/
2. Register as developer
3. Create an application with **Field Translation** or **General Translation** service
4. Get your `APP ID` and `Secret Key`

### Translation Cache

The translator includes an in-memory cache to avoid duplicate API calls:
- Each text is checked against the cache before translation
- Identical texts are translated only once per session
- Cache is automatically used for both sync and async translation
- Cache statistics are logged: total texts, cache hits, actual translations

```python
# Clear cache manually
manager.clear_cache()

# Get cache stats
stats = manager.get_cache_stats()
```

## Project Structure

```
CADAir/
├── docs/                   # Work summaries and TODOs
├── dwgtranslator/          # Translation package
│   ├── __init__.py
│   ├── core.py            # DWG/DXF I/O and ODA conversion
│   ├── extract.py         # Text extraction, including raw MULTILEADER supplement
│   ├── writeback.py       # Text write-back and direct DXF patching
│   ├── translator.py      # Translation engine ABC + Factory
│   ├── translation_cache.py # In-memory translation cache
│   ├── translation_filter.py # Pre-API CAD text filtering
│   ├── manager.py         # Workflow facade
│   └── plugins/
│       ├── __init__.py
│       └── baidu.py       # Baidu Translation API plugins
├── dwg-utils/              # Standalone utilities
│   ├── dwg_to_dxf.py      # ODA direct converter
│   ├── dwg2json.py
│   └── text_reader.py
├── data/                   # All DWG/DXF/JSON data files
│   ├── 20260123.dwg
│   ├── your_design.dwg
│   ├── output.dxf
│   ├── output_mock.dxf
│   ├── output.json
│   └── translation_work.json
├── examples/               # Example scripts (one per file)
│   ├── __init__.py
│   ├── quick_start.py     # Quick translation
│   ├── mock_translate.py  # Mock translator with custom dict
│   ├── extract_only.py    # Extract text for human translation
│   ├── writeback_only.py  # Write-back translated JSON
│   ├── baidu_translate.py # Baidu API translation (sync)
│   ├── baidu_async_translate.py # Baidu API translation (async with QPS control)
│   ├── custom_translator.py # Custom translation function
│   ├── list_engines.py    # List available translation engines
│   └── run_all.py         # Run all examples
├── pyproject.toml
├── uv.lock
├── TODO.md                 # Pointer to docs/TODO.md
└── README.md
```
