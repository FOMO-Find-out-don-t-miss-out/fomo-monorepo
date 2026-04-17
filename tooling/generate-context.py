import ast
import os
import re
from pathlib import Path


def get_directory_tree(root_dir, max_depth=3):
    """Generates a directory tree up to a specified depth."""
    tree = []
    root_path = Path(root_dir).resolve()

    def walk(directory, depth):
        if depth > max_depth:
            return

        # Sort directories first, then files
        try:
            items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return

        for i, path in enumerate(items):
            # Skip common noise
            if path.name in [
                ".git",
                "node_modules",
                ".venv",
                "__pycache__",
                ".turbo",
                ".pytest_cache",
                ".ruff_cache",
                "dist",
                "build",
            ]:
                continue

            connector = "├───" if i < len(items) - 1 else "└───"
            indent = "│   " * (depth - 1)

            if path.is_dir():
                tree.append(f"{indent}{connector}{path.name}/")
                walk(path, depth + 1)
            else:
                tree.append(f"{indent}{connector}{path.name}")

    tree.append(f"{root_path.name}/")
    walk(root_path, 1)
    return "\n".join(tree)


def get_api_route_signatures(api_dir):
    """Extracts route signatures from FastAPI files."""
    signatures = []
    api_path = Path(api_dir)
    if not api_path.exists():
        return "API directory not found."

    for py_file in api_path.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        signatures.append(f"### {py_file.name}")
        with open(py_file, encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                        for decorator in node.decorator_list:
                            # Handle router.get("/path"), router.post("/path"), etc.
                            if isinstance(decorator, ast.Call) and isinstance(
                                decorator.func, ast.Attribute
                            ):
                                if decorator.func.attr in ["get", "post", "put", "delete", "patch"]:
                                    route = ""
                                    if decorator.args and isinstance(
                                        decorator.args[0], ast.Constant
                                    ):
                                        route = decorator.args[0].value
                                    signatures.append(
                                        f"- {decorator.func.attr.upper()} `{route}` -> `{node.name}`"
                                    )
            except Exception as e:
                signatures.append(f"- Error parsing {py_file.name}: {e}")
    return "\n".join(signatures)


def get_openapi_schemas(openapi_file):
    """Lists named schemas from the generated OpenAPI spec."""
    import json
    spec_path = Path(openapi_file)
    if not spec_path.exists():
        return "openapi.json not found — run `pnpm --filter @fomo/api-spec build`."
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    schemas = spec.get("components", {}).get("schemas", {})
    lines = [f"- `{name}`" for name in sorted(schemas)]
    paths = spec.get("paths", {})
    lines.append(f"\nTotal endpoints: {sum(len(v) for v in paths.values())}")
    return "\n".join(lines)


def get_quality_status():
    """Summarizes quality/coverage status."""
    status = []
    if os.path.exists(".coverage"):
        status.append("- `.coverage` file present (95% target enforced).")
    else:
        status.append("- No `.coverage` found (run tests to generate).")

    status.append("- Linting: Ruff (Python), ESLint (TS/JS).")
    status.append("- Validation: FastAPI → openapi.json → openapi-typescript pipeline.")
    return "\n".join(status)


def generate_snapshot():
    snapshot_path = "AI_SNAPSHOT.md"
    content = f"""# AI Context Snapshot (2026 standards)

## 📁 Directory Tree (Max Depth: 3)
```text
{get_directory_tree(".")}
```

## 🛣 API Routes (v1)
{get_api_route_signatures("apps/api/app/api/v1")}

## 🏗 OpenAPI Schemas (packages/api-spec/openapi.json)
{get_openapi_schemas("packages/api-spec/openapi.json")}

## 🧪 Quality & Coverage Status
{get_quality_status()}
"""
    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Snapshot generated: {snapshot_path}")


if __name__ == "__main__":
    generate_snapshot()
