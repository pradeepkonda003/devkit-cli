"""SDK stub generator — emits typed client stubs from OpenAPI schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml

Language = Literal["python", "typescript"]
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def _load(path: str) -> dict:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    if p.suffix in {".yaml", ".yml"}:
        return yaml.safe_load(raw)
    return json.loads(raw)


def _collect_operations(doc: dict) -> list[dict]:
    """Flatten all path operations into a list of operation dicts."""
    ops = []
    for path, path_item in doc.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            ops.append({
                "path": path,
                "method": method.upper(),
                "operation_id": operation.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}"),
                "summary": operation.get("summary", ""),
                "tags": operation.get("tags", ["default"]),
                "parameters": operation.get("parameters", []),
                "request_body": operation.get("requestBody"),
                "responses": operation.get("responses", {}),
            })
    return ops


def _python_method(op: dict) -> str:
    """Render a single Python async method stub."""
    name = op["operation_id"]
    method = op["method"]
    path = op["path"]
    summary = op["summary"]
    params = ["self"]
    if op["request_body"]:
        params.append("body: dict")
    for p in op["parameters"]:
        pname = p.get("name", "param")
        required = p.get("required", False)
        params.append(f"{pname}: str" if required else f"{pname}: str | None = None")
    param_str = ", ".join(params)
    docstring = summary or f"{method} {path}"
    return f'    async def {name}({param_str}) -> dict:\n        """{docstring}"""\n        return await self._request("{method}", f"{path}")\n'


def _python_class(tag: str, ops: list[dict]) -> str:
    class_name = tag.replace("-", "_").replace(" ", "_").title() + "Client"
    methods = "\n".join(_python_method(op) for op in ops)
    return (
        f"class {class_name}:\n"
        f'    """Auto-generated SDK client for {tag} operations."""\n\n'
        f"    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:\n"
        f"        self._base_url = base_url\n"
        f"        self._session = session\n\n"
        f"    async def _request(self, method: str, path: str, **kwargs) -> dict:\n"
        f"        url = self._base_url.rstrip('/') + path\n"
        f"        async with self._session.request(method, url, **kwargs) as resp:\n"
        f"            resp.raise_for_status()\n"
        f"            return await resp.json()\n\n"
        f"{methods}"
    )


def _write_python(ops: list[dict], output_dir: Path, dry_run: bool) -> list[str]:
    by_tag: dict[str, list[dict]] = {}
    for op in ops:
        for tag in op["tags"]:
            by_tag.setdefault(tag, []).append(op)
    written = []
    for tag, tag_ops in by_tag.items():
        filename = tag.lower().replace(" ", "_").replace("-", "_") + ".py"
        content = (
            '"""Auto-generated SDK stub — do not edit by hand."""\n\n'
            "from __future__ import annotations\n\n"
            "import aiohttp\n\n\n"
            + _python_class(tag, tag_ops)
            + "\n"
        )
        dest = output_dir / filename
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        written.append(str(dest))
    return written


def _ts_method(op: dict) -> str:
    name = op["operation_id"]
    method = op["method"]
    path = op["path"]
    summary = op["summary"]
    params = []
    if op["request_body"]:
        params.append("body: Record<string, unknown>")
    for p in op["parameters"]:
        pname = p.get("name", "param")
        required = p.get("required", False)
        params.append(f"{pname}{'?' if not required else ''}: string")
    param_str = ", ".join(params)
    docstring = summary or f"{method} {path}"
    return f"  /** {docstring} */\n  async {name}({param_str}): Promise<unknown> {{\n    return this.request(\"{method}\", `{path}`);\n  }}\n"


def _ts_class(tag: str, ops: list[dict]) -> str:
    class_name = tag.replace("-", " ").replace("_", " ").title().replace(" ", "") + "Client"
    methods = "\n".join(_ts_method(op) for op in ops)
    return (
        f"/** Auto-generated SDK client for {tag} operations. */\n"
        f"export class {class_name} {{\n"
        f"  constructor(private readonly baseUrl: string) {{}}\n\n"
        f"  private async request(method: string, path: string, body?: unknown): Promise<unknown> {{\n"
        f"    const res = await fetch(`${{this.baseUrl.replace(/\\/+$/, '')}}${{path}}`, {{\n"
        f"      method,\n"
        f"      headers: {{ 'Content-Type': 'application/json' }},\n"
        f"      body: body ? JSON.stringify(body) : undefined,\n"
        f"    }});\n"
        f"    if (!res.ok) throw new Error(`HTTP ${{res.status}} ${{res.statusText}}`);\n"
        f"    return res.json();\n"
        f"  }}\n\n"
        f"{methods}}}\n"
    )


def _write_typescript(ops: list[dict], output_dir: Path, dry_run: bool) -> list[str]:
    by_tag: dict[str, list[dict]] = {}
    for op in ops:
        for tag in op["tags"]:
            by_tag.setdefault(tag, []).append(op)
    written = []
    for tag, tag_ops in by_tag.items():
        filename = tag.lower().replace(" ", "-").replace("_", "-") + ".ts"
        content = "// Auto-generated SDK stub — do not edit by hand.\n\n" + _ts_class(tag, tag_ops)
        dest = output_dir / filename
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        written.append(str(dest))
    return written


def generate_sdk_stub(schema_path: str, *, lang: Language, output_dir: str, dry_run: bool = False) -> list[str]:
    """Generate typed SDK stubs from an OpenAPI schema."""
    doc = _load(schema_path)
    ops = _collect_operations(doc)
    out = Path(output_dir)
    if lang == "python":
        return _write_python(ops, out, dry_run)
    elif lang == "typescript":
        return _write_typescript(ops, out, dry_run)
    else:
        raise ValueError(f"Unsupported language: {lang!r}")
