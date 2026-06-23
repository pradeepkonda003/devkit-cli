"""Tests for devkit validator, generator, and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from devkit.cli import cli
from devkit.generator import generate_sdk_stub
from devkit.validator import validate_schema

VALID_OPENAPI = {
    "openapi": "3.0.3",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/users": {
            "get": {"operationId": "listUsers", "summary": "List all users", "tags": ["users"], "responses": {"200": {"description": "OK"}}},
            "post": {"operationId": "createUser", "summary": "Create a user", "tags": ["users"], "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}, "responses": {"201": {"description": "Created"}}},
        },
        "/users/{id}": {
            "get": {"operationId": "getUser", "summary": "Get a user by ID", "tags": ["users"], "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "OK"}, "404": {"description": "Not Found"}}},
        },
    },
}


@pytest.fixture()
def valid_schema_json(tmp_path):
    p = tmp_path / "openapi.json"
    p.write_text(json.dumps(VALID_OPENAPI), encoding="utf-8")
    return p


@pytest.fixture()
def valid_schema_yaml(tmp_path):
    p = tmp_path / "openapi.yaml"
    p.write_text(yaml.dump(VALID_OPENAPI), encoding="utf-8")
    return p


@pytest.fixture()
def minimal_invalid_schema(tmp_path):
    doc = {"openapi": "3.0.3", "info": {"title": "Incomplete"}}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


@pytest.fixture()
def no_operation_ids_schema(tmp_path):
    doc = {"openapi": "3.0.3", "info": {"title": "Warn API", "version": "0.1.0"}, "paths": {"/items": {"get": {"responses": {"200": {"description": "OK"}}}}}}
    p = tmp_path / "warn.yaml"
    p.write_text(yaml.dump(doc), encoding="utf-8")
    return p


class TestValidateSchema:
    def test_valid_json_schema_passes(self, valid_schema_json):
        result = validate_schema(str(valid_schema_json))
        assert not result.has_errors()
        assert not result.has_warnings()

    def test_valid_yaml_schema_passes(self, valid_schema_yaml):
        result = validate_schema(str(valid_schema_yaml))
        assert not result.has_errors()

    def test_missing_required_fields_raises_errors(self, minimal_invalid_schema):
        result = validate_schema(str(minimal_invalid_schema))
        assert result.has_errors()
        msgs = [i.message for i in result.errors()]
        assert any("paths" in m for m in msgs)
        assert any("version" in m for m in msgs)

    def test_missing_operation_id_is_warning(self, no_operation_ids_schema):
        result = validate_schema(str(no_operation_ids_schema))
        assert not result.has_errors()
        assert result.has_warnings()
        assert any("operationId" in i.message for i in result.warnings())

    def test_unparseable_json_returns_error(self, tmp_path):
        p = tmp_path / "broken.json"
        p.write_text("{not valid json", encoding="utf-8")
        result = validate_schema(str(p))
        assert result.has_errors()

    def test_unsupported_extension_returns_error(self, tmp_path):
        p = tmp_path / "schema.toml"
        p.write_text("[info]\ntitle = 'x'\n", encoding="utf-8")
        result = validate_schema(str(p))
        assert result.has_errors()

    def test_non_object_root_returns_error(self, tmp_path):
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        result = validate_schema(str(p))
        assert result.has_errors()

    def test_operation_without_response_returns_error(self, tmp_path):
        doc = {"openapi": "3.0.3", "info": {"title": "T", "version": "1"}, "paths": {"/x": {"get": {"operationId": "getX", "summary": "Get X"}}}}
        p = tmp_path / "no_response.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        result = validate_schema(str(p))
        assert result.has_errors()


class TestGenerateSdkStub:
    def test_python_stub_dry_run_returns_paths(self, valid_schema_json, tmp_path):
        out = tmp_path / "sdk"
        files = generate_sdk_stub(str(valid_schema_json), lang="python", output_dir=str(out), dry_run=True)
        assert len(files) > 0
        assert all(f.endswith(".py") for f in files)
        assert not out.exists()

    def test_typescript_stub_dry_run_returns_paths(self, valid_schema_json, tmp_path):
        out = tmp_path / "sdk"
        files = generate_sdk_stub(str(valid_schema_json), lang="typescript", output_dir=str(out), dry_run=True)
        assert len(files) > 0
        assert all(f.endswith(".ts") for f in files)

    def test_python_stub_writes_files(self, valid_schema_json, tmp_path):
        out = tmp_path / "sdk"
        files = generate_sdk_stub(str(valid_schema_json), lang="python", output_dir=str(out))
        assert all(Path(f).exists() for f in files)
        content = Path(files[0]).read_text()
        assert "class" in content and "async def" in content

    def test_typescript_stub_writes_files(self, valid_schema_json, tmp_path):
        out = tmp_path / "sdk"
        files = generate_sdk_stub(str(valid_schema_json), lang="typescript", output_dir=str(out))
        assert all(Path(f).exists() for f in files)
        content = Path(files[0]).read_text()
        assert "export class" in content and "Promise<unknown>" in content

    def test_invalid_lang_raises(self, valid_schema_json, tmp_path):
        with pytest.raises(ValueError, match="Unsupported language"):
            generate_sdk_stub(str(valid_schema_json), lang="ruby", output_dir=str(tmp_path))  # type: ignore

    def test_operations_grouped_by_tag(self, valid_schema_json, tmp_path):
        out = tmp_path / "sdk"
        files = generate_sdk_stub(str(valid_schema_json), lang="python", output_dir=str(out))
        assert "users.py" in [Path(f).name for f in files]


class TestCLI:
    def setup_method(self):
        self.runner = CliRunner()

    def test_validate_valid_schema_exits_0(self, valid_schema_json):
        assert self.runner.invoke(cli, ["validate", str(valid_schema_json)]).exit_code == 0

    def test_validate_invalid_schema_exits_1(self, minimal_invalid_schema):
        assert self.runner.invoke(cli, ["validate", str(minimal_invalid_schema)]).exit_code == 1

    def test_validate_strict_exits_2_on_warnings(self, no_operation_ids_schema):
        assert self.runner.invoke(cli, ["validate", str(no_operation_ids_schema), "--strict"]).exit_code == 2

    def test_validate_json_output(self, valid_schema_json):
        result = self.runner.invoke(cli, ["validate", str(valid_schema_json), "--format", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["valid"] is True

    def test_generate_dry_run_lists_files(self, valid_schema_json, tmp_path):
        result = self.runner.invoke(cli, ["generate", str(valid_schema_json), "--lang", "python", "--out", str(tmp_path / "sdk"), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_generate_writes_files(self, valid_schema_json, tmp_path):
        out = tmp_path / "sdk"
        result = self.runner.invoke(cli, ["generate", str(valid_schema_json), "--lang", "typescript", "--out", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_version_flag(self):
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
