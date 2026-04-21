# CADAir

A Python tool for converting DWG files to JSON using [ezdxf](https://ezdxf.mozman.at/) and the ODA File Converter.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for dependency management
- ODA File Converter (see below)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/CADAir.git
cd CADAir
```

### 2. Install Python dependencies

```bash
uv sync
```

### 3. Install ODA File Converter

`ezdxf` cannot read DWG files directly. It relies on the **ODA File Converter** to convert DWG to DXF first.

1. Go to https://www.opendesign.com/guestfiles/oda_file_converter
2. Download the latest **ODA File Converter** for your platform
3. Install it (default path on Windows: `C:\Program Files\ODA\ODAFileConverter\`)

> **Note:** The installer version number may vary (e.g., `ODAFileConverter 27.1.0`). Make sure the path in `main.py` matches your actual installation.

### 4. Configure the ODA path

Open `main.py` and update the `oda_path` variable to match your installation:

```python
oda_path = r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
```

> **Important:** Newer versions of `ezdxf` read the path from `ezdxf.options`, not `odafc.win_exec_path`. The code in this project already handles this correctly:
> ```python
> ezdxf.options.set("odafc-addon", "win_exec_path", oda_path)
> ```

If the path is wrong, you will see:

```
Could not find ODAFileConverter in the path.
Install application from https://www.opendesign.com/guestfiles/oda_file_converter
```

## Usage

```bash
uv run main.py
```

This will read `your_design.dwg` and export the geometry data to `output.json`.

## Supported Entities

Currently extracts the following entity types:

- `LINE` — start and end points
- `CIRCLE` — center and radius
- `TEXT` — content, insert point, height
- `LWPOLYLINE` — vertices

## Project Structure

```
.
├── main.py          # Main script: DWG -> JSON converter
├── pyproject.toml   # uv project configuration
├── uv.lock          # Dependency lock file
└── README.md        # This file
```
