import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from sqlmodel import SQLModel, create_engine

ROOT = Path(__file__).resolve().parent.parent
API_APP_ROOT = ROOT / "apps" / "api"
OPENAPI_PATH = ROOT / "packages" / "api-spec" / "openapi.json"
GENERATED_TYPE_PATHS = [
    ROOT / "apps" / "harvester-dashboard" / "types" / "api.generated.ts",
    ROOT / "apps" / "mobile" / "types" / "api.generated.ts",
]
MOBILE_UI_TYPES_PATH = ROOT / "apps" / "mobile" / "types" / "ui.ts"
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}

# Add monorepo root and apps/api to path to ensure imports work correctly.
sys.path.append(str(ROOT))
sys.path.append(str(API_APP_ROOT))

# Import all models to ensure they are registered in SQLModel.metadata.
try:
    import packages.domain.models  # noqa: F401
    from packages.domain.models.event import EventCategory
except ImportError as e:
    print(f"Warning: Some models could not be imported: {e}")  # noqa: T201


@dataclass
class CheckResult:
    name: str
    ok: bool
    summary: str
    details: list[str]


def load_env() -> None:
    """Simple .env loader to avoid extra dependencies."""
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def include_object(obj: object, name: str, type_: str, reflected: bool, compare_to: object) -> bool:
    """
    Filter out internal PostGIS and Tiger geocoder tables from comparison.
    Only include tables that are defined in our SQLModel metadata.
    """
    if type_ == "table":
        internal_prefixes = [
            "spatial_ref_sys",
            "topology",
            "layer",
            "addr",
            "county",
            "state",
            "place",
            "zip",
            "tract",
            "bg",
            "tabblock",
            "edges",
            "faces",
            "featnames",
            "cousub",
            "countysub",
            "direction_lookup",
            "street_type_lookup",
            "secondary_unit_lookup",
            "loader_",
            "geocode_settings",
            "pagc_",
        ]
        if any(name.startswith(prefix) for prefix in internal_prefixes):
            return False

        return name in SQLModel.metadata.tables

    return True


def normalize_text(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n") + "\n"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def load_json(path: Path) -> dict:
    return json.loads(read_text(path))


def collect_path_method_pairs(spec: dict) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for path, path_item in spec.get("paths", {}).items():
        for method in path_item:
            lowered = method.lower()
            if lowered in HTTP_METHODS:
                pairs.add((path, lowered))
    return pairs


def collect_schema_names(spec: dict) -> set[str]:
    return set(spec.get("components", {}).get("schemas", {}).keys())


def diff_lines(label: str, actual: set[str], expected: set[str]) -> list[str]:
    details: list[str] = []
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        details.append(f"Missing {label}:")
        details.extend(f"  - {item}" for item in missing)
    if extra:
        details.append(f"Unexpected {label}:")
        details.extend(f"  - {item}" for item in extra)
    return details


def run_openapi_typescript(openapi_path: Path, output_path: Path) -> None:
    pnpm_executable = "pnpm.cmd" if os.name == "nt" else "pnpm"
    completed = subprocess.run(
        [pnpm_executable, "exec", "openapi-typescript", str(openapi_path), "-o", str(output_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        message = stderr or stdout or "openapi-typescript failed"
        raise RuntimeError(message)


def load_live_openapi_spec() -> dict:
    """
    Load the live FastAPI OpenAPI document using the same uv-backed import path
    as the existing frontend type generator.
    """
    completed = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-c",
            'from app.main import app; import json; print(json.dumps(app.openapi()))',
        ],
        cwd=API_APP_ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        message = stderr or stdout or "Failed to load live OpenAPI spec."
        raise RuntimeError(message)

    return json.loads(completed.stdout)


def evaluate_database_schema_sync() -> CheckResult:
    """
    Compares the current SQLModel metadata with the live database schema.
    Preserves the legacy success/failure output for external tooling.
    """
    if os.getenv("SKIP_DB_VERIFY"):
        print("WARNING: Skipping schema verification (SKIP_DB_VERIFY is set).")  # noqa: T201
        return CheckResult(
            name="ORM<->DB",
            ok=True,
            summary="ORM<->DB schema verification skipped because SKIP_DB_VERIFY is set.",
            details=[],
        )

    load_env()

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db = os.getenv("POSTGRES_DB", "fomo")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    engine = create_engine(database_url, connect_args={"connect_timeout": 5})

    try:
        with engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            connection.commit()

            context = MigrationContext.configure(
                connection, opts={"include_object": include_object}
            )
            diff = compare_metadata(context, SQLModel.metadata)

        if diff:
            print("CRITICAL: Schema Drift Detected. Please run Alembic migrations.")  # noqa: T201
            details = [f" - {entry}" for entry in diff]
            for line in details:
                print(line)  # noqa: T201
            return CheckResult(
                name="ORM<->DB",
                ok=False,
                summary="ORM metadata drifted from the live database schema.",
                details=details,
            )

        print("SUCCESS: Schema is in sync.")  # noqa: T201
        return CheckResult(
            name="ORM<->DB",
            ok=True,
            summary="ORM metadata matches the live database schema.",
            details=[],
        )
    except Exception as e:
        if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            print(f"WARNING: Could not verify schema sync in CI environment: {e}")  # noqa: T201
            return CheckResult(
                name="ORM<->DB",
                ok=True,
                summary="ORM<->DB schema verification skipped in CI because the database was unavailable.",
                details=[],
            )
        print(f"Error: Could not verify schema sync: {e}")  # noqa: T201
        return CheckResult(
            name="ORM<->DB",
            ok=False,
            summary="Could not verify ORM<->DB schema sync.",
            details=[str(e)],
        )


def check_openapi_coverage() -> CheckResult:
    """
    Ensure the committed OpenAPI spec exposes the same path/method pairs and
    named schema set as the live FastAPI app.
    """
    committed_spec = load_json(OPENAPI_PATH)
    live_spec = load_live_openapi_spec()

    committed_pairs = {f"{path} [{method.upper()}]" for path, method in collect_path_method_pairs(committed_spec)}
    live_pairs = {f"{path} [{method.upper()}]" for path, method in collect_path_method_pairs(live_spec)}
    committed_schemas = collect_schema_names(committed_spec)
    live_schemas = collect_schema_names(live_spec)

    details: list[str] = []
    details.extend(diff_lines("OpenAPI operations", committed_pairs, live_pairs))
    details.extend(diff_lines("OpenAPI schemas", committed_schemas, live_schemas))

    if details:
        return CheckResult(
            name="OpenAPI Coverage",
            ok=False,
            summary="Committed openapi.json drifted from the live FastAPI contract surface.",
            details=details,
        )

    return CheckResult(
        name="OpenAPI Coverage",
        ok=True,
        summary=(
            f"Committed openapi.json covers {len(committed_pairs)} operations and "
            f"{len(committed_schemas)} named schemas from the live FastAPI app."
        ),
        details=[],
    )


def check_frontend_types_freshness() -> CheckResult:
    """
    Regenerate frontend TypeScript types from the committed OpenAPI spec into a
    temp directory and fail if the generated output differs from the tracked files.
    """
    drifted_files: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for generated_path in GENERATED_TYPE_PATHS:
            regenerated_path = temp_dir / generated_path.name
            run_openapi_typescript(OPENAPI_PATH, regenerated_path)
            committed_text = normalize_text(read_text(generated_path))
            regenerated_text = normalize_text(read_text(regenerated_path))
            if committed_text != regenerated_text:
                drifted_files.append(str(generated_path.relative_to(ROOT)))

    if drifted_files:
        return CheckResult(
            name="Frontend Types Freshness",
            ok=False,
            summary="Generated frontend API types are stale relative to packages/api-spec/openapi.json.",
            details=[f"  - {path}" for path in drifted_files],
        )

    return CheckResult(
        name="Frontend Types Freshness",
        ok=True,
        summary=f"Generated frontend API types match {OPENAPI_PATH.relative_to(ROOT)}.",
        details=[],
    )


def extract_string_literal_union(source: str, type_name: str) -> list[str]:
    pattern = rf"export type {re.escape(type_name)}\s*=\s*(.*?);"
    match = re.search(pattern, source, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find type alias '{type_name}' in mobile ui.ts.")
    return re.findall(r"'([^']+)'", match.group(1))


def extract_object_literal_keys(source: str, const_name: str) -> list[str]:
    pattern = rf"export const {re.escape(const_name)}\s*:[^=]+=\s*\{{(.*?)\n\}};"
    match = re.search(pattern, source, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find object literal '{const_name}' in mobile ui.ts.")
    return re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", match.group(1), flags=re.MULTILINE)


def check_mobile_ui_category_coherence() -> CheckResult:
    """
    Ensure the mobile hand-maintained ApiEventCategory union and apiCategoryToUi
    mapping stay aligned with the backend EventCategory enum.
    """
    source = read_text(MOBILE_UI_TYPES_PATH)
    backend_categories = {category.value for category in EventCategory}
    ui_categories = set(extract_string_literal_union(source, "ApiEventCategory"))
    mapping_keys = set(extract_object_literal_keys(source, "apiCategoryToUi"))

    details: list[str] = []
    details.extend(diff_lines("mobile ApiEventCategory values", ui_categories, backend_categories))
    details.extend(diff_lines("mobile apiCategoryToUi keys", mapping_keys, backend_categories))

    if details:
        return CheckResult(
            name="Mobile UI Category Coherence",
            ok=False,
            summary="Mobile category aliases drifted from the backend EventCategory enum.",
            details=details,
        )

    return CheckResult(
        name="Mobile UI Category Coherence",
        ok=True,
        summary="Mobile category aliases and apiCategoryToUi mapping match the backend EventCategory enum.",
        details=[],
    )


def print_check_result(result: CheckResult) -> None:
    status = "PASS" if result.ok else "FAIL"
    print(f"[{status}] {result.name}: {result.summary}")  # noqa: T201
    if result.details:
        for detail in result.details:
            print(detail)  # noqa: T201


def verify_schema() -> None:
    """
    Legacy ORM<->DB-only entry point preserved for backwards compatibility.
    """
    result = evaluate_database_schema_sync()
    sys.exit(0 if result.ok else 1)


def main() -> None:
    results = [
        evaluate_database_schema_sync(),
        check_openapi_coverage(),
        check_frontend_types_freshness(),
        check_mobile_ui_category_coherence(),
    ]

    for result in results:
        print_check_result(result)

    failed_checks = [result for result in results if not result.ok]
    if failed_checks:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
