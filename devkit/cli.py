"""CLI entry point for devkit."""

import sys
import click
from devkit.validator import validate_schema
from devkit.generator import generate_sdk_stub
from devkit.reporter import render_report


@click.group()
@click.version_option(version="0.1.0", prog_name="devkit")
def cli():
    """devkit — Developer tooling for API schema validation and SDK stub generation.

    Validate OpenAPI/JSON Schema files and generate typed SDK stubs from
    your API contracts. Designed for CI pipelines and local developer workflows.

    Examples:

    \b
        devkit validate ./openapi.json
        devkit validate ./schema.yaml --strict
        devkit generate ./openapi.json --lang python --out ./sdk
        devkit generate ./openapi.json --lang typescript --out ./sdk
    """


@cli.command()
@click.argument("schema_path", type=click.Path(exists=True))
@click.option("--strict", is_flag=True, default=False, help="Fail on warnings in addition to errors.")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", show_default=True, help="Output format for validation results.")
def validate(schema_path: str, strict: bool, output_format: str):
    """Validate an OpenAPI or JSON Schema file."""
    result = validate_schema(schema_path, strict=strict)
    render_report(result, fmt=output_format)
    if result.has_errors():
        sys.exit(1)
    if strict and result.has_warnings():
        sys.exit(2)


@cli.command()
@click.argument("schema_path", type=click.Path(exists=True))
@click.option("--lang", type=click.Choice(["python", "typescript"]), required=True, help="Target language for generated SDK stubs.")
@click.option("--out", "output_dir", type=click.Path(), default="./sdk", show_default=True, help="Directory to write generated files into.")
@click.option("--dry-run", is_flag=True, default=False, help="Print files that would be generated without writing them.")
def generate(schema_path: str, lang: str, output_dir: str, dry_run: bool):
    """Generate typed SDK stubs from an OpenAPI schema."""
    files = generate_sdk_stub(schema_path, lang=lang, output_dir=output_dir, dry_run=dry_run)
    if dry_run:
        click.echo("Dry run — files that would be generated:")
        for f in files:
            click.echo(f"  {f}")
    else:
        click.echo(f"Generated {len(files)} file(s) into {output_dir}/")
        for f in files:
            click.echo(f"  {f}")
