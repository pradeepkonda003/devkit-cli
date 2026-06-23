"""OpenAPI and JSON Schema validation logic."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class ValidationIssue:
    level: Literal["error", "warning"]
    message: str
    path: str = ""

    def __str__(self) -> str:
        loc = f" [{self.path}]" if self.path else ""
        return f"[{self.level.upper()}]{loc} {self.message}"


@dataclass
class ValidationResult:
    schema_path: str
    issues: list[ValidationIssue] = field(default_factory=list)

    def has_errors(self) -> bool:
        return any(i.level == "error" for i in self.issues)

    def has_warnings(self) -> bool:
        return any(i.level == "warning" for i in self.issues)

    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]


def _load_schema(path: str) -> dict:
    """Load a JSON or YAML schema file."""
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    if p.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(raw)
    elif p.suffix == ".json":
        return json.loads(raw)
    else:
        raise ValueError(f"Unsupported file extension: {p.suffix!r}. Use .json or .yaml/.yml")


def _check_openapi_required_fields(doc: dict, result: ValidationResult) -> None:
    """Validate presence of required top-level OpenAPI fields."""
    required = ["openapi", "info", "paths"]
    for field_name in required:
        if field_name not in doc:
            result.issues.append(
                ValidationIssue(
                    level="error",
                    message=f"Missing required top-level field: '{field_name}'",
                    path=field_name,
                )
            )
    info = doc.get("info", {})
    for sub in ["title", "version"]:
        if sub not in info:
            result.issues.append(
                ValidationIssue(
                    level="error",
                    message=f"Missing required field in 'info': '{sub}'",
                    path=f"info.{sub}",
                )
            )


def _check_operations(doc: dict, result: ValidationResult) -> None:
    """Warn on operations missing summaries or operationIds."""
    http_methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
    paths = doc.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in http_methods or not isinstance(operation, dict):
                continue
            op_path = f"paths.{path}.{method}"
            if "operationId" not in operation:
                result.issues.append(
                    ValidationIssue(
                        level="warning",
                        message="Operation is missing 'operationId'. SDK generators rely on this.",
                        path=op_path,
                    )
                )
            if "summary" not in operation and "description" not in operation:
                result.issues.append(
                    ValidationIssue(
                        level="warning",
                        message="Operation has no 'summary' or 'description'.",
                        path=op_path,
                    )
                )


def _check_response_schemas(doc: dict, result: ValidationResult) -> None:
    """Error on operations that declare no response schemas at all."""
    http_methods = {"get", "post", "put", "patch", "delete"}
    paths = doc.get("paths", {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in http_methods or not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            if not responses:
                result.issues.append(
                    ValidationIssue(
                        level="error",
                        message="Operation defines no responses.",
                        path=f"paths.{path}.{method}.responses",
                    )
                )


def validate_schema(schema_path: str, *, strict: bool = False) -> ValidationResult:
    """Validate an OpenAPI or JSON Schema document."""
    result = ValidationResult(schema_path=schema_path)
    try:
        doc = _load_schema(schema_path)
    except (ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        result.issues.append(ValidationIssue(level="error", message=f"Failed to parse schema: {exc}"))
        return result
    if not isinstance(doc, dict):
        result.issues.append(ValidationIssue(level="error", message="Schema root must be a JSON object / YAML mapping."))
        return result
    _check_openapi_required_fields(doc, result)
    _check_operations(doc, result)
    _check_response_schemas(doc, result)
    return result
