"""Render validation results to stdout in text or JSON format."""

from __future__ import annotations

import json
import sys
from typing import Literal

from devkit.validator import ValidationResult


def render_report(result: ValidationResult, fmt: Literal["text", "json"] = "text") -> None:
    """Print validation results to stdout (errors) / stderr (on failure).

    Args:
        result: The ValidationResult to render.
        fmt: ``"text"`` for human-readable output, ``"json"`` for machine-readable.
    """
    if fmt == "json":
        _render_json(result)
    else:
        _render_text(result)


def _render_text(result: ValidationResult) -> None:
    errors = result.errors()
    warnings = result.warnings()
    if not errors and not warnings:
        print(f"✓ {result.schema_path} — no issues found")
        return
    print(f"Validating: {result.schema_path}\n")
    for issue in errors:
        print(f"  ✗ {issue}", file=sys.stderr)
    for issue in warnings:
        print(f"  ⚠ {issue}")
    print(f"\n  {len(errors)} error(s), {len(warnings)} warning(s)")


def _render_json(result: ValidationResult) -> None:
    output = {
        "schema_path": result.schema_path,
        "valid": not result.has_errors(),
        "errors": [{"path": i.path, "message": i.message} for i in result.errors()],
        "warnings": [{"path": i.path, "message": i.message} for i in result.warnings()],
    }
    print(json.dumps(output, indent=2))
