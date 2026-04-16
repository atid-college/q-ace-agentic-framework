"""
suite_adapter.py – Adapter pattern for loading test suite files into a uniform list of dicts.

Supported formats are controlled by Q_ACE_SUITE_FORMATS in .env (default: json,csv,yaml,yml,md,markdown).
Each adapter returns List[{"name": str, "prompt": str}].
"""

import os
import io
import json
import re
from typing import List, Dict, Any

# Load allowed formats from environment
_raw_formats = os.environ.get("Q_ACE_SUITE_FORMATS", "json,csv,yaml,yml,md,markdown")
ALLOWED_FORMATS = {fmt.strip().lower() for fmt in _raw_formats.split(",") if fmt.strip()}


class UnsupportedFormatError(ValueError):
    pass


class SuiteParseError(ValueError):
    pass


def detect_format(filename: str) -> str:
    """Return the lowercased extension (without dot) and validate it's allowed."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_FORMATS:
        allowed = ", ".join(sorted(ALLOWED_FORMATS))
        raise UnsupportedFormatError(
            f"Unsupported file format '.{ext}'. Allowed: {allowed}"
        )
    return ext


def load_suite(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Main entry point. Detects format from filename and delegates to the right adapter.
    Returns a list of dicts: [{"name": str, "prompt": str}, ...]
    """
    fmt = detect_format(filename)

    try:
        if fmt == "json":
            return _load_json(file_bytes)
        elif fmt == "csv":
            return _load_csv(file_bytes)
        elif fmt in ("yaml", "yml"):
            return _load_yaml(file_bytes)
        elif fmt in ("md", "markdown"):
            return _load_markdown(file_bytes)
    except (UnsupportedFormatError, SuiteParseError):
        raise
    except Exception as e:
        raise SuiteParseError(f"Failed to parse '{filename}': {e}") from e

    raise UnsupportedFormatError(f"No adapter for format '{fmt}'")


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

def _normalize(raw: Any, index: int) -> Dict[str, Any]:
    """Turn a raw item (str or dict) into {"name": ..., "prompt": ...}."""
    if isinstance(raw, str):
        return {"name": f"Prompt {index + 1}", "prompt": raw.strip()}
    elif isinstance(raw, dict):
        prompt = raw.get("prompt") or raw.get("task") or raw.get("description") or ""
        name = raw.get("name") or raw.get("title") or raw.get("id") or f"Prompt {index + 1}"
        if not prompt:
            raise SuiteParseError(
                f"Item {index + 1} has no recognizable prompt field (expected 'prompt', 'task', or 'description'). Got: {list(raw.keys())}"
            )
        return {"name": str(name), "prompt": str(prompt).strip()}
    else:
        raise SuiteParseError(f"Item {index + 1} is not a string or object: {type(raw)}")


def _load_json(file_bytes: bytes) -> List[Dict[str, Any]]:
    text = file_bytes.decode("utf-8")
    data = json.loads(text)
    if not isinstance(data, list):
        raise SuiteParseError("JSON file must contain a top-level array.")
    return [_normalize(item, i) for i, item in enumerate(data)]


def _load_csv(file_bytes: bytes) -> List[Dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError:
        raise SuiteParseError("pandas is required to parse CSV files. Install it with: pip install pandas")

    df = pd.read_csv(io.BytesIO(file_bytes))
    # Find the prompt column case-insensitively
    col_map = {c.lower(): c for c in df.columns}
    prompt_col = col_map.get("prompt") or col_map.get("task") or col_map.get("description")
    if not prompt_col:
        # Fall back to using the first column as prompt
        prompt_col = df.columns[0]
    
    name_col = col_map.get("name") or col_map.get("title") or col_map.get("id")

    results = []
    for i, row in df.iterrows():
        prompt = str(row[prompt_col]).strip()
        name = str(row[name_col]).strip() if name_col else f"Prompt {i + 1}"
        results.append({"name": name, "prompt": prompt})
    return results


def _load_yaml(file_bytes: bytes) -> List[Dict[str, Any]]:
    try:
        import yaml
    except ImportError:
        raise SuiteParseError("pyyaml is required to parse YAML files. Install it with: pip install pyyaml")

    text = file_bytes.decode("utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, list):
        raise SuiteParseError("YAML file must contain a top-level list.")
    return [_normalize(item, i) for i, item in enumerate(data)]


def _load_markdown(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parse Markdown suites. Each prompt is delimited by:
    - A `## Heading` (H2) – heading becomes the name, body below is the prompt
    - OR `---` separators if no headings found
    """
    text = file_bytes.decode("utf-8")
    results = []

    # Strategy 1: use ## headings
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    if len(sections) > 1:
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            lines = section.strip().splitlines()
            name = lines[0].strip() if lines else f"Prompt {i}"
            body = "\n".join(lines[1:]).strip()
            if body:
                results.append({"name": name, "prompt": body})
        return results

    # Strategy 2: split on --- separators
    blocks = re.split(r"^\s*---\s*$", text, flags=re.MULTILINE)
    for i, block in enumerate(blocks):
        block = block.strip()
        if block:
            results.append({"name": f"Prompt {i + 1}", "prompt": block})
    return results
