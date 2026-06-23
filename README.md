# devkit-cli

[![CI](https://github.com/pradeepkonda003/devkit-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/pradeepkonda003/devkit-cli/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Developer tooling for **API schema validation** and **typed SDK stub generation** from OpenAPI documents.

`devkit` is designed to slot into local developer workflows and CI pipelines, giving teams fast feedback on contract correctness before code ever ships.

---

## Features

- **Validate** OpenAPI 3.x documents (JSON or YAML) — catches missing required fields, undocumented responses, and missing `operationId`s that break downstream SDK generators
- **Generate** typed client stubs in **Python** (async/aiohttp) or **TypeScript** (fetch-based), grouped by tag
- **Strict mode** (`--strict`) to fail CI on warnings, not just errors
- **JSON output** (`--format json`) for machine-readable results in pipelines
- **Dry run** (`--dry-run`) to preview generated files without writing them

---

## Installation

```bash
pip install devkit-cli
```

Or install from source for development:

```bash
git clone https://github.com/pradeepkonda003/devkit-cli.git
cd devkit-cli
pip install -e ".[dev]"
```

---

## Usage

### Validate a schema

```bash
# Basic validation
devkit validate ./openapi.json

# Fail on warnings too (good for CI)
devkit validate ./openapi.yaml --strict

# Machine-readable JSON output
devkit validate ./openapi.json --format json
```

### Generate SDK stubs

```bash
# Python async client
devkit generate ./openapi.json --lang python --out ./sdk

# TypeScript fetch client
devkit generate ./openapi.json --lang typescript --out ./sdk

# Preview without writing
devkit generate ./openapi.json --lang python --dry-run
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy devkit/
```

---

## Project Structure
