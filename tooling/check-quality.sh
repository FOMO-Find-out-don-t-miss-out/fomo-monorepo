#!/bin/bash
set -e

echo "🔍 Running Quality Gates (2026 Standards)..."

echo "🧪 Running Ruff (Linting & Formatting)..."
uv run ruff check .
uv run ruff format --check .

echo "✅ Running Tests (95% Coverage Mandatory)..."
uv run pytest --cov-fail-under=95

echo "🎉 Quality check passed!"
