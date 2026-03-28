#!/bin/bash
set -e

echo "🔍 Running Quality Gates (2026 Standards with Turbo acceleration)..."

npx turbo check-quality

echo "🎉 Quality check passed!"
